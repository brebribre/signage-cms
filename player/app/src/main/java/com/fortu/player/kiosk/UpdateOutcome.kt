package com.fortu.player.kiosk

import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * What the system finally said about the last silent install.
 *
 * `PackageInstaller` answers asynchronously, by broadcast, long after the call that started the
 * install returned — so the engine cannot report the outcome itself. Without this the screen sat
 * on "installing update 1.1.3…" forever whether the install landed, was rejected for lack of
 * space, or was quietly waiting for a confirmation nobody was there to give.
 *
 * A plain object rather than anything injected: a BroadcastReceiver is constructed by the system
 * with no access to the app's own graph, and this has to be reachable from both sides.
 */
object UpdateOutcome {
    private val _last = MutableStateFlow<String?>(null)

    /** Human-readable, and shown verbatim in the debug overlay's `update` row. */
    val last: StateFlow<String?> = _last

    /** The reason the install the engine last handed over came back rejected, until the engine
     *  collects it. Held as the message rather than a flag: the reason is exactly what the CMS
     *  needs to show, and the engine is the only thing with a device token to send it with. */
    private val failure = AtomicReference<String?>(null)

    private val _failures = MutableSharedFlow<Unit>(extraBufferCapacity = 1)

    /** Fires when a rejection lands, so the engine can act on it now rather than on its next
     *  heartbeat — up to 30 seconds later, during which the CMS still says "installing". */
    val failures: SharedFlow<Unit> = _failures

    fun report(message: String) {
        _last.value = message
    }

    /** Both at once: say so on screen, and leave the reason for the engine to pick up. */
    fun reportFailure(message: String) {
        failure.set(message)
        report(message)
        _failures.tryEmit(Unit)
    }

    /** The reason, at most once per failure — a second caller (or a second heartbeat) must not
     *  see a rejection that has already started a backoff, or the cooldown would keep resetting. */
    fun consumeFailure(): String? = failure.getAndSet(null)
}
