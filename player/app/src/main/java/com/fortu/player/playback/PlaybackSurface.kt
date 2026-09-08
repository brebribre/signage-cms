package com.fortu.player.playback

import android.util.Log
import android.view.View
import android.view.ViewGroup
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import coil.compose.AsyncImage
import com.fortu.player.api.ManifestItem
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
 * The loop.
 *
 * Images are advanced by a timer; videos hand control to ExoPlayer and advance when it
 * reports the item ended. A single index drives both, so a playlist mixing the two needs no
 * special casing beyond which composable renders.
 *
 * Note this deliberately does *not* use one ExoPlayer playlist for everything: Media3 gained
 * image support relatively recently, and mixing kinds in one playlist would tie playback to a
 * Media3 version floor for no real gain. A timer and an index are boring and work everywhere.
 */
@Composable
fun PlaybackSurface(
    items: List<ManifestItem>,
    fileFor: (ManifestItem) -> File,
    modifier: Modifier = Modifier,
    /** Called as each item finishes, for proof-of-play. Reported in batches on the next
     *  heartbeat rather than immediately — an item can be shorter than the heartbeat
     *  interval, and a request per item would be absurd traffic for a 10-second image. */
    onPlayed: (ManifestItem, Long, Int) -> Unit = { _, _, _ -> },
    /** Reported to the CMS so an unplayable file shows up on the health page rather than
     *  only as a gap someone happens to notice. */
    onPlaybackError: (String) -> Unit = {},
) {
    var index by remember(items) { mutableIntStateOf(0) }
    val item = items[index.coerceIn(items.indices)]
    var startedAt by remember(items) { mutableLongStateOf(System.currentTimeMillis()) }

    fun advance() {
        val now = System.currentTimeMillis()
        onPlayed(item, startedAt, ((now - startedAt) / 1000).toInt())
        startedAt = now
        index = if (items.isEmpty()) 0 else (index + 1) % items.size
    }

    // One ExoPlayer, and one PlayerView backing it, for the whole playlist — not one per
    // video item. The bug this fixes: a playlist alternating picture/video played the first
    // video fine, but the *second* time a video came around the screen stayed black with no
    // error logged anywhere. Each video item used to build its own ExoPlayer and its own
    // PlayerView (hence its own native SurfaceView) from scratch, and tear both down the
    // moment the loop moved off it. Recreating a SurfaceView that quickly is a known source of
    // "first frame never arrives" on embedded/signage GPUs — decoding proceeds normally (no
    // error, no stall the watchdog would catch), it simply never reaches the new surface.
    // Keeping one player and one surface alive for as long as this screen is playing sidesteps
    // the recreation entirely.
    val context = LocalContext.current
    val exo = remember {
        ExoPlayer.Builder(context).build().apply {
            playWhenReady = true
            // No repeat: the surrounding loop owns advancing, so the playlist order stays in
            // one place rather than being split between here and the index above.
            repeatMode = Player.REPEAT_MODE_OFF
            volume = 0f
        }
    }
    DisposableEffect(Unit) { onDispose { exo.release() } }

    Box(modifier.fillMaxSize().background(Color.Black)) {
        // Always composed, even on a picture slot, so the underlying SurfaceView is created
        // once and just hidden — never destroyed and rebuilt on the next video.
        VideoSurface(
            exo = exo,
            active = item.kind == "video",
            file = if (item.kind == "video") fileFor(item) else null,
            fit = item.fit,
            maxSeconds = item.durationSeconds,
            // Finish the current item before moving on — cutting mid-item to apply an
            // update is the difference between a CMS and a glitch.
            onEnded = { advance() },
            onError = onPlaybackError,
        )
        if (item.kind != "video") {
            AsyncImage(
                model = fileFor(item),
                contentDescription = null,
                contentScale = contentScaleFor(item.fit),
                modifier = Modifier.fillMaxSize(),
            )
            LaunchedEffect(item.id, index) {
                delay(item.durationSeconds * 1000L)
                advance()
            }
        }
    }
}

@Composable
private fun VideoSurface(
    exo: ExoPlayer,
    /** False on a picture slot — the surface stays mounted but idle rather than leaving
     *  composition, so its SurfaceView is never torn down and recreated. */
    active: Boolean,
    file: File?,
    fit: String,
    /** The slot's duration from the CMS. A video is cut at this if it runs longer — the
     *  playlist editor offers it, the backend stores it, and until now the player ignored
     *  it and always played to the natural end. */
    maxSeconds: Int,
    onEnded: () -> Unit,
    onError: (String) -> Unit,
) {
    // Guarantees exactly one advance per item however playback ends — naturally, by error,
    // or by the watchdog below. Without it a video that errors *and* times out would skip
    // two items.
    var finished by remember(file?.absolutePath) { mutableStateOf(false) }
    fun finishOnce(reason: String?) {
        if (finished) return
        finished = true
        reason?.let(onError)
        onEnded()
    }

    DisposableEffect(file?.absolutePath, active) {
        if (active && file != null) {
            exo.setMediaItem(MediaItem.fromUri(file.toURI().toString()))
            exo.prepare()
        }

        val listener = object : Player.Listener {
            override fun onPlaybackStateChanged(state: Int) {
                if (active && state == Player.STATE_ENDED) finishOnce(null)
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
                finishOnce("${file?.name}: ${error.errorCodeName}")
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
     * Watchdog. Covers the cases an error listener cannot: a stream that stalls buffering
     * forever, a decoder that hangs without reporting, or a file whose container says one
     * duration and whose data says another.
     *
     * Also implements the CMS's per-slot duration — whichever comes first, the natural end or
     * this, the loop moves on.
     */
    LaunchedEffect(file?.absolutePath, active) {
        if (!active || file == null) return@LaunchedEffect
        val cap = if (maxSeconds > 0) maxSeconds else DEFAULT_VIDEO_CAP_SECONDS
        delay(cap * 1000L + STALL_GRACE_MILLIS)
        if (!finished) {
            Log.w("FortuPlayer", "video did not finish within ${cap}s — advancing")
            finishOnce("${file.name}: did not finish in ${cap}s")
        }
    }

    AndroidView(
        factory = { ctx ->
            PlayerView(ctx).apply {
                useController = false
                resizeMode = resizeModeFor(fit)
                setBackgroundColor(android.graphics.Color.BLACK)
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT,
                )
                player = exo
            }
        },
        update = {
            it.resizeMode = resizeModeFor(fit)
            it.visibility = if (active) View.VISIBLE else View.INVISIBLE
        },
        modifier = Modifier.fillMaxSize(),
    )
}
