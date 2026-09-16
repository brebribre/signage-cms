package com.fortu.player.playback

import android.annotation.SuppressLint
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.zIndex
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import coil.compose.AsyncImage
import com.fortu.player.R
import com.fortu.player.api.KIND_WEB
import com.fortu.player.api.ManifestElement
import com.fortu.player.api.ManifestSlot
import kotlinx.coroutines.delay
import java.io.File

/**
 * Maps the CMS's `fit` values onto the platform's own scaling modes.
 *
 * These are exact equivalents, which is what makes the CMS's device preview trustworthy
 * rather than approximate — the same three words mean the same three things in the editor's
 * CSS `object-fit`, in Compose's `ContentScale`, and in Media3's resize mode.
 */
private fun contentScaleFor(fit: String): ContentScale = when (fit) {
    "cover" -> ContentScale.Crop
    "stretch" -> ContentScale.FillBounds
    else -> ContentScale.Fit
}

/** Cap for a video whose slot has no explicit duration. Playback is always from an
 *  already-downloaded local file — there is no network buffering to allow for — so the only
 *  reason this should ever fire is a decoder that failed to report end-of-stream, a real
 *  device-specific bug seen on some hardware. Kept short enough that a wedged screen recovers
 *  within a minute and a half, not an entire shift. */
private const val DEFAULT_VIDEO_CAP_SECONDS = 90

/**
 * The CSS width every website element is laid out at, before being scaled into its box.
 *
 * Sites choose a layout from the viewport width, so this is what decides whether a screen shows
 * the desktop design or the phone one. 1280 is the smallest width that reliably lands on desktop
 * breakpoints (Bootstrap's `xl`, Tailwind's `xl`, and the common 1200px container all fit), while
 * staying small enough that text is still legible once it is scaled into a half- or quarter-width
 * element rather than the whole screen.
 */
private const val DESKTOP_CSS_WIDTH_PX = 1280f

/**
 * Forces the page to lay out at a desktop width, and reports what it ended up with.
 *
 * Setting the WebView's zoom is not enough on its own: a site's own `<meta name="viewport">`
 * wins over it, which is why a screen kept getting the phone layout even with a desktop user
 * agent — the page was still being told the window was as wide as the panel's dp, not its
 * pixels. Rewriting that meta tag is the one instruction a browser cannot overrule. `width` alone
 * (no `initial-scale`) leaves the browser to scale the result to fit, which is exactly wanted:
 * it renders at the panel's real resolution rather than upscaling a small layout.
 *
 * Re-applied on every page load, so following a link inside a site keeps the desktop layout.
 */
private val DESKTOP_VIEWPORT_SCRIPT = """
    (function () {
      var m = document.querySelector('meta[name=viewport]');
      if (!m) { m = document.createElement('meta'); m.name = 'viewport'; document.head.appendChild(m); }
      m.setAttribute('content', 'width=${DESKTOP_CSS_WIDTH_PX.toInt()}');
      return JSON.stringify({
        css: window.innerWidth,
        dpr: window.devicePixelRatio,
        chMobile: (navigator.userAgentData ? navigator.userAgentData.mobile : 'n/a'),
        ua: navigator.userAgent,
      });
    })();
""".trimIndent()

/** Slack over the slot duration before the watchdog fires, so ordinary buffering on bad venue
 *  wifi is not mistaken for a stall. */
private const val STALL_GRACE_MILLIS = 5_000L

/**
 * Whether this element covers its whole frame on its own — the case a SurfaceView can take,
 * because nothing else shares the screen with it. Compared with a tolerance: these arrive as
 * JSON floats, and a box authored by dragging is never exactly 1.0. A rotated element is
 * excluded: rotation draws through a graphics layer, which a SurfaceView does not follow.
 */
private fun ManifestElement.isFullBleed(): Boolean {
    val slack = 0.001f
    return kotlin.math.abs(x) < slack &&
        kotlin.math.abs(y) < slack &&
        kotlin.math.abs(width - 1f) < slack &&
        kotlin.math.abs(height - 1f) < slack &&
        rotationDegrees == 0
}

private fun resizeModeFor(fit: String): Int = when (fit) {
    "cover" -> AspectRatioFrameLayout.RESIZE_MODE_ZOOM
    "stretch" -> AspectRatioFrameLayout.RESIZE_MODE_FILL
    else -> AspectRatioFrameLayout.RESIZE_MODE_FIT
}

/**
 * The loop, over slots instead of flat items — a slot is one or more elements, layered and
 * positioned by their own x/y/width/height fractions (the same normalized coordinate space
 * `ScreenPreview.vue`/`SceneEditor.vue` already use), shown together.
 *
 * **Advance policy**: a slot that is exactly one video keeps the original behavior exactly —
 * the natural end of the video (or the watchdog cap) advances the loop, whichever comes first.
 * The exception is a playlist of exactly one slot, which has nothing to advance *to*: its video
 * repeats instead of stopping on its last frame, and its duration only decides how often the
 * play is reported.
 * Anything else — a picture, or a slot with more than one element regardless of kind — advances
 * on a plain timer set to the slot's own `durationSeconds`, the same way a picture always has.
 * A video inside a multi-element slot loops on its own rather than trying to end the slot; with
 * more than one video in play there is no single unambiguous "this slot is done" signal to
 * reconcile, so the CMS-authored duration is the one that decides, same as it always has for a
 * picture.
 *
 * **Video surfaces are pooled, and every pool member is composed on every single slot,
 * active or not.** The original single-player design existed to dodge a real bug — recreating
 * an ExoPlayer/PlayerView (and so its SurfaceView) on every transition left some embedded GPUs
 * never delivering a first frame to the new surface, silently. Composing a pool member only
 * when the *current* slot happens to need it would reintroduce exactly that: the member leaves
 * composition on a slot that does not need it and gets rebuilt from scratch the next time one
 * does. Every pool member's `AndroidView` is therefore called unconditionally, every slot, for
 * as long as this composable exists — inactive members just sit invisible, exactly like the
 * original single instance did between a picture and the next video.
 */
@Composable
fun PlaybackSurface(
    slots: List<ManifestSlot>,
    fileFor: (ManifestElement) -> File,
    modifier: Modifier = Modifier,
    /** Called as each slot finishes, for proof-of-play — once per element it contained, all
     *  sharing the same timing. Reported in batches on the next heartbeat rather than
     *  immediately — a slot can be shorter than the heartbeat interval, and a request per slot
     *  would be absurd traffic for a 10-second picture. */
    onPlayed: (ManifestSlot, Long, Int) -> Unit = { _, _, _ -> },
    /** Reported to the CMS so an unplayable file shows up on the health page rather than
     *  only as a gap someone happens to notice. */
    onPlaybackError: (String) -> Unit = {},
) {
    var index by remember(slots) { mutableIntStateOf(0) }
    val slot = slots[index.coerceIn(slots.indices)]
    var startedAt by remember(slots) { mutableLongStateOf(System.currentTimeMillis()) }

    fun advance() {
        val now = System.currentTimeMillis()
        onPlayed(slot, startedAt, ((now - startedAt) / 1000).toInt())
        startedAt = now
        index = if (slots.isEmpty()) 0 else (index + 1) % slots.size
    }

    // The one case that keeps the original single-video timing exactly: nothing to reconcile
    // when there is only ever one thing that could signal "done."
    val singleVideo = slot.elements.singleOrNull()?.takeIf { it.kind == "video" }

    /** A one-slot playlist: the loop has nowhere to advance, so "the slot ended" is meaningless
     *  — what is on screen stays on screen. It still has to be *reported* as playing, and a
     *  video still has to keep playing rather than stop dead on its last frame. */
    val onlySlot = slots.size == 1

    /** Records the play without changing what is on screen — the one-slot counterpart of
     *  [advance], which cannot be used there: advancing to the same slot re-keys nothing, so the
     *  timer below would never run again and the play would be counted exactly once, forever. */
    fun report() {
        val now = System.currentTimeMillis()
        onPlayed(slot, startedAt, ((now - startedAt) / 1000).toInt())
        startedAt = now
    }

    // A plain duration timer for everything else — pictures (as always), an empty slot (should
    // not happen, but must not hang forever if it does), and any multi-element slot (new):
    // with more than one thing on screen, the CMS-authored duration is the only unambiguous
    // "this slot is over" signal.
    if (onlySlot) {
        LaunchedEffect(slot.id) {
            while (true) {
                delay(slot.durationSeconds * 1000L)
                report()
            }
        }
    } else if (singleVideo == null) {
        LaunchedEffect(slot.id, index) {
            delay(slot.durationSeconds * 1000L)
            advance()
        }
    }

    // Persists for as long as this composable lives — never rebuilt just because `slots`
    // changed. It only ever grows, to the most concurrent videos any slot *this composable
    // has ever seen* needs. Keying this on `slots` instead (as an earlier version did) meant
    // any playlist swap while already playing — a rule firing, a schedule change — tore down
    // and rebuilt every pool member from scratch: releasing and recreating an ExoPlayer and
    // its decoder/surface is expensive enough, synchronously on the main thread during
    // composition, to visibly freeze the screen. A slot needing fewer than the pool's current
    // size just leaves the remaining members inactive, exactly as before.
    val context = LocalContext.current
    // A SnapshotStateList, not a plain list: replacePoolMember (below) swaps one element in
    // place on a decoder-stall recovery, and that swap needs to be observed by whatever reads
    // this pool the same way growing it already is.
    val exoPool = remember { mutableStateListOf<ExoPlayer>() }
    var poolSize by remember { mutableIntStateOf(0) }
    val requiredPoolSize = slots.maxOfOrNull { s -> s.elements.count { it.kind == "video" } } ?: 0
    LaunchedEffect(requiredPoolSize) {
        while (exoPool.size < requiredPoolSize) {
            exoPool.add(
                ExoPlayer.Builder(context).build().apply {
                    playWhenReady = true
                    volume = 0f
                },
            )
        }
        poolSize = exoPool.size
    }
    DisposableEffect(Unit) { onDispose { exoPool.forEach { it.release() } } }

    /**
     * Recovery for a decoder that never reported end-of-stream (the watchdog's one real
     * purpose — see [DEFAULT_VIDEO_CAP_SECONDS]). Advancing the slot alone was not enough:
     * doing that reuses this same pool member for the *next* video too, via the ordinary
     * stop()-then-prepare() its own effect already does on every transition — but if the
     * decoder itself, not just the stream's EOS signal, is what is wedged, that stop()/prepare()
     * cycle on the same instance may not actually recover it, and the next video gets stuck
     * the same way. A brand new ExoPlayer sidesteps that entirely.
     *
     * Deliberately does not release() the outgoing instance here. It is always called
     * alongside finishOnce() advancing the slot, which changes this pool member's `file` too —
     * that composable's own DisposableEffect is about to tear down and will call stop() on the
     * outgoing instance via its own closure, exactly as it does on every ordinary transition.
     * Calling release() here as well would race that teardown, and a released ExoPlayer throws
     * if anything still calls into it. The abandoned instance's decoder is already freed by its
     * own stop(); only its idle internal thread leaks until the process restarts — an
     * acceptable trade against ever risking a call into an already-released player.
     */
    fun replacePoolMember(poolIndex: Int) {
        exoPool[poolIndex] = ExoPlayer.Builder(context).build().apply {
            playWhenReady = true
            volume = 0f
        }
    }

    // A lone video repeats: with no next slot, ending playback would freeze the screen on its
    // last frame until the playlist changed. Looping also means nothing calls onEnded for it,
    // which is exactly right — the report timer above owns proof-of-play in that case.
    val loop = singleVideo == null || onlySlot

    /**
     * Which kind of video surface this playlist gets.
     *
     * A SurfaceView keeps a 4K video at 4K — the display composites it directly — while a
     * TextureView draws every frame through the app's window, capping it at the window's
     * resolution. The TextureView is only needed where a video shares its frame with other
     * elements (see pooled_player_view.xml's own note), so it is reserved for playlists that
     * actually contain such a scene.
     *
     * Decided across the whole playlist rather than per slot, deliberately: the surface cannot
     * change without rebuilding the player view, and rebuilding one mid-loop is exactly the
     * "decoder runs, first frame never paints" bug the pool exists to avoid. A playlist that
     * mixes full-bleed videos with multi-element scenes keeps the TextureView throughout.
     */
    val useSurfaceView = slots.all { s ->
        val videos = s.elements.filter { it.kind == "video" }
        videos.isEmpty() || (s.elements.size == 1 && videos.single().isFullBleed())
    }

    val videoElementsInSlot = slot.elements.filter { it.kind == "video" }
    // Paint order matches the backend's own z-index ordering, which `slot.elements` already
    // arrives sorted by — later in the list paints on top. Explicit zIndex (not source order)
    // controls that here, since the always-composed pool and the freely-composed non-video
    // elements are declared in two separate groups below.
    fun zIndexOf(element: ManifestElement) = slot.elements.indexOf(element).toFloat()

    Box(modifier.fillMaxSize().background(Color.Black)) {
        BoxWithConstraints(Modifier.fillMaxSize()) {
            val parentWidth = maxWidth
            val parentHeight = maxHeight

            for (poolIndex in 0 until poolSize) {
                val element = videoElementsInSlot.getOrNull(poolIndex)
                val boxModifier = if (element != null) {
                    Modifier
                        .zIndex(zIndexOf(element))
                        .offset(x = parentWidth * element.x, y = parentHeight * element.y)
                        .size(parentWidth * element.width, parentHeight * element.height)
                        // The pooled surface is a TextureView, composited on its own hardware
                        // layer — Compose's offset/size alone position and measure it but do
                        // not clip its *drawing*, so without this its video content can bleed
                        // past this box into whatever else is on screen.
                        .clipToBounds()
                } else {
                    Modifier.zIndex(-1f).size(0.dp)
                }
                Box(boxModifier) {
                    RotatedContent(element?.rotationDegrees ?: 0) {
                        PooledVideoSurface(
                            exo = exoPool[poolIndex],
                            element = element,
                            file = element?.let(fileFor),
                            loop = loop,
                            onEnded = if (!loop) ::advance else ({}),
                            onError = onPlaybackError,
                            onStalled = { replacePoolMember(poolIndex) },
                            useSurfaceView = useSurfaceView,
                        )
                    }
                }
            }

            for (element in slot.elements) {
                if (element.kind == "video") continue // handled by the pool above
                Box(
                    Modifier
                        .zIndex(zIndexOf(element))
                        .offset(x = parentWidth * element.x, y = parentHeight * element.y)
                        .size(parentWidth * element.width, parentHeight * element.height)
                        .clipToBounds(),
                ) {
                    RotatedContent(element.rotationDegrees) {
                        when (element.kind) {
                            "image" -> {
                                // A plain File model resets Coil's painter to empty the instant
                                // it changes, even on a cache hit — the request still resolves
                                // through a coroutine dispatch, so there is a real frame or two
                                // with nothing drawn in this Box, showing the black background
                                // behind it. Coil's own ImageRequest.crossfade() was tried first
                                // and measured to have no visible effect here — Compose's own
                                // Crossfade, keyed on the file, is used instead: it keeps the
                                // *previous* composable (still showing its last decoded frame)
                                // on screen, fading it into the new one, independent of
                                // whatever Coil's internal transition plumbing does or doesn't
                                // do for a Compose target.
                                Crossfade(
                                    targetState = fileFor(element),
                                    animationSpec = tween(300),
                                    label = "image-crossfade",
                                ) { file ->
                                    AsyncImage(
                                        model = file,
                                        contentDescription = null,
                                        contentScale = contentScaleFor(element.fit),
                                        modifier = Modifier.fillMaxSize(),
                                        onError = { Log.e("FortuPlayer", "image failed to load: ${element.id}", it.result.throwable) },
                                    )
                                }
                            }
                            KIND_WEB -> WebsiteElement(element.url)
                            // A kind this build predates — nothing to render, but not a crash,
                            // and every other element in the slot still shows correctly.
                            else -> {}
                        }
                    }
                }
            }
        }
    }
}

/**
 * A website, shown live. It leaves composition with its slot, so it loads fresh each time the
 * slot comes up and its WebView is destroyed when the slot ends.
 *
 * Touchable: scrolling, tapping and links all work, so a wayfinding board or an order page is
 * usable by whoever is standing there. The CMS's touchscreen lock is what turns that off, for
 * the whole app at once (`MainActivity.dispatchTouchEvent`) — and kiosk mode means even a link
 * that opens a new page cannot leave the player.
 */
/**
 * A signage panel is a big screen, so a site must lay out as it would in a desktop browser
 * window that size. Two things force the phone layout otherwise, and both have to go:
 *
 * The **user agent**: Android's WebView announces itself as a mobile browser ("Android …
 * Mobile", plus the "wv" WebView marker), and responsive sites serve their phone layout on the
 * strength of that alone, whatever the width. Rewritten to the same Chrome, on a desktop OS —
 * derived from the device's own string rather than hard-coded, so the Chrome version stays
 * honest as the system WebView updates.
 *
 * The **viewport**: `width=device-width` resolves to the WebView's width in *density-independent*
 * units, so a full-screen element on a 1080p panel reports ~960 CSS pixels and lands on tablet
 * breakpoints. The view is therefore laid out at the element's real width in pixels — 1920 CSS
 * pixels for a full-screen element on that panel — and scaled back down by the display density,
 * which renders it at native resolution rather than upscaling a small layout. It is the same
 * composition `ScreenPreview.vue` makes in the CMS, so the preview and the panel agree.
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
private fun WebsiteElement(url: String) {
    BoxWithConstraints(Modifier.fillMaxSize().clipToBounds()) {
        // How wide the page believes the window is, in CSS pixels, is the whole ballgame: it is
        // what a responsive site picks its layout from. Sizing the view and scaling it by hand
        // got this wrong, because a CSS pixel is neither a dp nor a device pixel — the browser
        // derives it from the display density, so the same code produced a different viewport on
        // every panel, and a narrow enough one served the phone layout.
        //
        // Telling the WebView its zoom directly removes the density from the question entirely:
        // at a scale of (element pixels / DESKTOP_CSS_WIDTH), the layout viewport is
        // DESKTOP_CSS_WIDTH CSS pixels wide by definition, on any screen, and the browser does
        // the scaling itself — no extra layer, and it renders at the panel's real resolution.
        val elementWidthPx = with(LocalDensity.current) { maxWidth.toPx() }
        val zoomPercent = ((elementWidthPx / DESKTOP_CSS_WIDTH_PX) * 100f)
            .roundToInt()
            .coerceIn(1, 1000)
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                WebView(ctx).apply {
                    setBackgroundColor(android.graphics.Color.BLACK)
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    settings.mediaPlaybackRequiresUserGesture = false
                    settings.useWideViewPort = true
                    // NOT loadWithOverviewMode: it would zoom the page out again to fit, undoing
                    // the zoom set here.
                    setInitialScale(zoomPercent)
                    settings.userAgentString = desktopUserAgent(settings.userAgentString)
                    // Redirects, links and in-page navigation stay in this view instead of
                    // handing off to a browser — there isn't one to hand off to on a kiosk screen.
                    // The log line on load is the only way to see, from a screen you cannot
                    // attach a debugger to, which layout a site actually chose and why.
                    webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView, finishedUrl: String) {
                            view.evaluateJavascript(DESKTOP_VIEWPORT_SCRIPT) { measured ->
                                Log.i(
                                    "FortuWeb",
                                    "$finishedUrl laid out $measured in a ${view.width}x${view.height}px view",
                                )
                            }
                        }
                    }
                    tag = url
                    loadUrl(url)
                }
            },
            // Only a changed address reloads; comparing against view.url would reload after every
            // redirect.
            update = { view ->
                view.setInitialScale(zoomPercent)
                if (view.tag != url) {
                    view.tag = url
                    view.loadUrl(url)
                }
            },
            onRelease = { it.destroy() },
        )
    }
}

/**
 * The WebView's own user agent, with everything that says "phone" taken out: the Android
 * platform token becomes a desktop one, and the "Mobile" and WebView ("wv") markers go. Keeping
 * the rest means the Chrome version stays whatever the device actually ships.
 */
internal fun desktopUserAgent(current: String): String =
    current
        .replace(Regex("""Linux; Android [^;)]*(; [^)]*)?"""), "X11; Linux x86_64")
        .replace("; wv", "")
        .replace(" Mobile Safari", " Safari")
        .replace(Regex(""" Mobile(?= )"""), "")

/** Measures [content] at its pre-rotation aspect (swapped for 90°/270°) and rotates it to fill
 *  this box exactly — the Compose equivalent of `cropMath.ts`'s `rotationStyle`, since Compose
 *  has no direct analogue of CSS container-query units to lean on instead. */
@Composable
private fun RotatedContent(rotationDegrees: Int, content: @Composable () -> Unit) {
    val swapped = rotationDegrees == 90 || rotationDegrees == 270
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val contentWidth = if (swapped) maxHeight else maxWidth
        val contentHeight = if (swapped) maxWidth else maxHeight
        Box(
            Modifier
                .align(Alignment.Center)
                .size(contentWidth, contentHeight)
                .rotate(rotationDegrees.toFloat()),
        ) {
            content()
        }
    }
}

/**
 * One slot in the video pool. Called unconditionally on every slot regardless of whether
 * [element] is non-null for it — see [PlaybackSurface]'s pooling note for why leaving
 * composition even briefly is exactly the bug this avoids. `element`/`file` null means this
 * pool member is not needed by the current slot; it just sits invisible until one needs it.
 */
@Composable
private fun PooledVideoSurface(
    exo: ExoPlayer,
    element: ManifestElement?,
    file: File?,
    /** True for anything but the slot's sole video — see [PlaybackSurface]'s advance policy. */
    loop: Boolean,
    onEnded: () -> Unit,
    onError: (String) -> Unit,
    /** Called once, right before [onEnded], only when the watchdog below fires — a decoder
     *  that never reported end-of-stream, not an ordinary transition. Lets the caller retire
     *  this pool member's ExoPlayer instance instead of reusing a possibly-wedged one for the
     *  next video. */
    onStalled: () -> Unit = {},
    /** See [PlaybackSurface]'s own `useSurfaceView`: direct-to-display for a full-bleed video,
     *  composited through the window when a scene layers other elements over it. */
    useSurfaceView: Boolean = false,
) {
    val active = element != null && file != null

    // Guarantees exactly one advance per slot however playback ends — naturally, by error, or
    // by the watchdog below. Without it a video that errors *and* times out would skip two
    // slots. Meaningless (and harmless) whenever `loop` is true: nothing here calls it then.
    //
    // `exo` is in this key for the same reason it is on the effects below: a stall-recovery
    // replacement can land on the same file (a single-video playlist is the extreme case, but
    // any short cycle can do it), and without `exo` here this flag would stay stuck `true`
    // from the watchdog that just fired — silently swallowing the *next* video's legitimate
    // end-of-stream signal, including from the fresh, correctly-working replacement player.
    // Confirmed live: the replacement decoder played its video through to a clean natural stop
    // and nothing advanced, because this flag never reset.
    var finished by remember(exo, file?.absolutePath) { mutableStateOf(false) }
    fun finishOnce(reason: String?) {
        if (finished) return
        finished = true
        reason?.let(onError)
        onEnded()
    }

    // `exo` is in this key for exactly one reason: a stall-recovery replacement (see
    // replacePoolMember). Ordinarily this pool member's ExoPlayer instance never changes for
    // the life of the app, so adding it here changes nothing about normal playback — but
    // without it, a single-video playlist (or any advance that happens to land back on the
    // same file) would never re-run this block after a replacement, since `file` alone would
    // be unchanged: the fresh instance would sit there with no media ever prepared on it.
    DisposableEffect(exo, file?.absolutePath, active, loop) {
        if (active) {
            exo.repeatMode = if (loop) Player.REPEAT_MODE_ONE else Player.REPEAT_MODE_OFF
            exo.setMediaItem(MediaItem.fromUri(file!!.toURI().toString()))
            exo.prepare()
        }

        val listener = object : Player.Listener {
            override fun onPlaybackStateChanged(state: Int) {
                if (active && !loop && state == Player.STATE_ENDED) finishOnce(null)
            }

            /**
             * The bug this fixes: without an error listener, a video the device cannot decode
             * produced no ENDED and no advance, so the loop stopped dead on a black screen
             * *forever* — it never even reached the next photo. A screen showing nothing is
             * the single worst outcome for signage, and one unplayable file could cause it.
             */
            override fun onPlayerError(error: PlaybackException) {
                if (!active) return
                Log.e("FortuPlayer", "playback failed for ${file?.name}", error)
                val message = "${file?.name}: ${error.errorCodeName}"
                if (loop) onError(message) else finishOnce(message)
            }
        }
        exo.addListener(listener)
        onDispose {
            exo.removeListener(listener)
            // Stop rather than leave the old item buffered behind the next one — the player
            // instance survives, but nothing it was doing for this slot should carry over.
            if (active) exo.stop()
        }
    }

    /**
     * Watchdog — only meaningful on the legacy single-video path. Covers what an error
     * listener cannot: a stream that stalls buffering forever, a decoder that hangs without
     * reporting, or a file whose container says one duration and whose data says another. A
     * looping video (any multi-element slot) has no "should have finished by now" instant —
     * the slot's own duration timer is the only clock that matters there.
     */
    LaunchedEffect(exo, file?.absolutePath, active, loop) {
        if (!active || loop) return@LaunchedEffect
        delay(DEFAULT_VIDEO_CAP_SECONDS * 1000L + STALL_GRACE_MILLIS)
        if (!finished) {
            Log.w("FortuPlayer", "video did not finish within ${DEFAULT_VIDEO_CAP_SECONDS}s — advancing and retiring its decoder")
            onStalled()
            finishOnce("${file?.name}: did not finish in time")
        }
    }

    // Keyed on the surface type: changing it means a different View entirely, so the old one
    // has to go. Only a new manifest can flip it, never an ordinary slot transition.
    key(useSurfaceView) {
        AndroidView(
            factory = { ctx ->
                // Inflated, not `PlayerView(ctx)` directly — the surface type is an XML attribute.
                val layout =
                    if (useSurfaceView) R.layout.pooled_player_view_surface else R.layout.pooled_player_view
                (LayoutInflater.from(ctx).inflate(layout, null) as PlayerView).apply {
                    setBackgroundColor(android.graphics.Color.BLACK)
                    player = exo
                }
            },
            update = {
                // Cheap to repeat every recomposition — PlayerView no-ops if it's already the
                // current player. The one time it isn't a no-op is exactly the case `factory`
                // alone can't handle: a stall-recovery replacement swaps this pool member's
                // ExoPlayer instance without this View ever being recreated, and factory only
                // runs once at creation.
                it.player = exo
                it.resizeMode = resizeModeFor(element?.fit ?: "contain")
                it.visibility = if (active) View.VISIBLE else View.INVISIBLE
                // Only meaningful while this pool member is active; an inactive one's exo.volume
                // would otherwise leak into whatever plays on it next.
                if (active) exo.volume = if (element?.hasAudio == true) 1f else 0f
            },
            modifier = Modifier.fillMaxSize(),
        )
    }
}
