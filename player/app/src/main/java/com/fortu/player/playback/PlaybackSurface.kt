package com.fortu.player.playback

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
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
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

    Box(modifier.fillMaxSize().background(Color.Black)) {
        if (item.kind == "video") {
            VideoItem(
                file = fileFor(item),
                fit = item.fit,
                // Finish the current item before moving on — cutting mid-item to apply an
                // update is the difference between a CMS and a glitch.
                onEnded = { advance() },
            )
        } else {
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
private fun VideoItem(file: File, fit: String, onEnded: () -> Unit) {
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

    DisposableEffect(file.absolutePath) {
        exo.setMediaItem(MediaItem.fromUri(file.toURI().toString()))
        exo.prepare()
        val listener = object : Player.Listener {
            override fun onPlaybackStateChanged(state: Int) {
                if (state == Player.STATE_ENDED) onEnded()
            }
        }
        exo.addListener(listener)
        onDispose {
            exo.removeListener(listener)
        }
    }

    DisposableEffect(Unit) { onDispose { exo.release() } }

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
        update = { it.resizeMode = resizeModeFor(fit) },
        modifier = Modifier.fillMaxSize(),
    )
}
