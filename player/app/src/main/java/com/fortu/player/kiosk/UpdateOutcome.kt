package com.fortu.player.kiosk

import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.flow.MutableStateFlow
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

    /** Whether the install the engine last handed over came back rejected. Separate from the
     *  message because the engine acts on it (by backing the version off) rather than reading
     *  it, and a boolean it can consume exactly once is the whole contract. */
    private val failed = AtomicBoolean(false)

    fun report(message: String) {
        _last.value = message
    }

    /** Both at once: say so on screen, and leave a flag for the engine to pick up. */
    fun reportFailure(message: String) {
        failed.set(true)
        report(message)
    }

    /** True at most once per failure — a second caller (or a second heartbeat) must not see a
     *  rejection that has already started a backoff, or the cooldown would keep resetting. */
    fun consumeFailure(): Boolean = failed.getAndSet(false)
}
