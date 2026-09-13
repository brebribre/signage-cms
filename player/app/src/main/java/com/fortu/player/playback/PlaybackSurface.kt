package com.fortu.player.playback

import android.util.Log
import android.view.LayoutInflater
import android.view.View
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
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
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
import androidx.compose.ui.unit.dp
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

/** Cap for a video whose slot has no explicit duration. Long enough for any realistic signage
 *  clip, short enough that a hung decoder cannot hold a screen black for an entire shift. */
private const val DEFAULT_VIDEO_CAP_SECONDS = 600

/** Slack over the slot duration before the watchdog fires, so ordinary buffering on bad venue
 *  wifi is not mistaken for a stall. */
private const val STALL_GRACE_MILLIS = 5_000L

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

    // A plain duration timer for everything else — pictures (as always), an empty slot (should
    // not happen, but must not hang forever if it does), and any multi-element slot (new):
    // with more than one thing on screen, the CMS-authored duration is the only unambiguous
    // "this slot is over" signal.
    if (singleVideo == null) {
        LaunchedEffect(slot.id, index) {
            delay(slot.durationSeconds * 1000L)
            advance()
        }
    }

    // Sized once per manifest (`slots` is a structurally new list only when content actually
    // changed — an unchanged poll answers 304 and never reaches here at all) to the most
    // concurrent videos any single slot needs. A slot needing fewer just leaves the remaining
    // pool members inactive.
    val context = LocalContext.current
    val poolSize = remember(slots) {
        slots.maxOfOrNull { s -> s.elements.count { it.kind == "video" } } ?: 0
    }
    val exoPool = remember(slots) {
        List(poolSize) {
            ExoPlayer.Builder(context).build().apply {
                playWhenReady = true
                volume = 0f
            }
        }
    }
    DisposableEffect(exoPool) { onDispose { exoPool.forEach { it.release() } } }

    val loop = singleVideo == null
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
                                AsyncImage(
                                    model = fileFor(element),
                                    contentDescription = null,
                                    contentScale = contentScaleFor(element.fit),
                                    modifier = Modifier.fillMaxSize(),
                                    onError = { Log.e("FortuPlayer", "image failed to load: ${element.id}", it.result.throwable) },
                                )
                            }
                            // A kind this build predates (an iframe/website element authored
                            // by a newer CMS) — nothing to render, but not a crash, and every
                            // other element in the slot still shows correctly.
                            else -> {}
                        }
                    }
                }
            }
        }
    }
}

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
) {
    val active = element != null && file != null

    // Guarantees exactly one advance per slot however playback ends — naturally, by error, or
    // by the watchdog below. Without it a video that errors *and* times out would skip two
    // slots. Meaningless (and harmless) whenever `loop` is true: nothing here calls it then.
    var finished by remember(file?.absolutePath) { mutableStateOf(false) }
    fun finishOnce(reason: String?) {
        if (finished) return
        finished = true
        reason?.let(onError)
        onEnded()
    }

    DisposableEffect(file?.absolutePath, active, loop) {
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
    LaunchedEffect(file?.absolutePath, active, loop) {
        if (!active || loop) return@LaunchedEffect
        delay(DEFAULT_VIDEO_CAP_SECONDS * 1000L + STALL_GRACE_MILLIS)
        if (!finished) {
            Log.w("FortuPlayer", "video did not finish within ${DEFAULT_VIDEO_CAP_SECONDS}s — advancing")
            finishOnce("${file?.name}: did not finish in time")
        }
    }

    AndroidView(
        factory = { ctx ->
            // Inflated, not `PlayerView(ctx)` directly — see pooled_player_view.xml for why
            // this needs to force TextureView over the default SurfaceView.
            (LayoutInflater.from(ctx).inflate(R.layout.pooled_player_view, null) as PlayerView).apply {
                setBackgroundColor(android.graphics.Color.BLACK)
                player = exo
            }
        },
        update = {
            it.resizeMode = resizeModeFor(element?.fit ?: "contain")
            it.visibility = if (active) View.VISIBLE else View.INVISIBLE
            // Only meaningful while this pool member is active; an inactive one's exo.volume
            // would otherwise leak into whatever plays on it next.
            if (active) exo.volume = if (element?.hasAudio == true) 1f else 0f
        },
        modifier = Modifier.fillMaxSize(),
    )
}
