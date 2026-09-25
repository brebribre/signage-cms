package com.fortu.player.kiosk

import android.content.Context
import android.content.res.Resources
import android.graphics.Point
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.display.DisplayManager
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.view.Display
import android.view.Surface
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * Reads what [detectOrientation] needs from the device — a gravity reading, the display's
 * rotation, whether the panel is landscape by nature, and the maker's rotation setting — and
 * returns the CMS orientation, or null when the screen can't tell. Called while the pairing
 * code is on screen, so the CMS can skip "How is the screen mounted?".
 *
 * Blocking, for up to [SAMPLE_TIMEOUT_MS]: it listens for one sensor reading and stops. Never
 * throws; anything that goes wrong is "can't tell".
 */
object MountDetector {
    private const val TAG = "FortuMount"
    private const val SAMPLE_TIMEOUT_MS = 500L

    private val thread by lazy { HandlerThread("mount-detector").apply { start() } }

    fun detect(context: Context): String? = runCatching {
        val app = context.applicationContext
        val display = app.getSystemService(DisplayManager::class.java)?.getDisplay(Display.DEFAULT_DISPLAY)
            ?: return null
        val rotation = when (display.rotation) {
            Surface.ROTATION_90 -> 90
            Surface.ROTATION_180 -> 180
            Surface.ROTATION_270 -> 270
            else -> 0
        }
        val size = Point().also {
            @Suppress("DEPRECATION")
            display.getRealSize(it)
        }
        val landscapeNow = size.x >= size.y
        val naturalLandscape = if (rotation == 0 || rotation == 180) landscapeNow else !landscapeNow
        val result = detectOrientation(sampleTilt(app), rotation, naturalLandscape, reverseDefaultRotation())
        result
    }.onFailure { Log.w(TAG, "mount detection failed", it) }.getOrNull()

    /** One tilt reading from the gravity sensor (or the raw accelerometer), or null without
     *  either, lying flat, or with no reading in time. */
    private fun sampleTilt(context: Context): Int? {
        val sensors = context.getSystemService(SensorManager::class.java) ?: return null
        val sensor = sensors.getDefaultSensor(Sensor.TYPE_GRAVITY)
            ?: sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            ?: return null
        val latch = CountDownLatch(1)
        var reading: FloatArray? = null
        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                if (reading == null) {
                    reading = event.values.copyOf()
                    latch.countDown()
                }
            }
            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
        }
        sensors.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_UI, Handler(thread.looper))
        try {
            latch.await(SAMPLE_TIMEOUT_MS, TimeUnit.MILLISECONDS)
        } finally {
            sensors.unregisterListener(listener)
        }
        val v = reading ?: return null
        return tiltDegrees(v[0], v[1], v[2])
    }

    /** The maker's `config_reverseDefaultRotation`: whether "portrait" is the other quarter
     *  turn on this device. False where the framework doesn't have it. */
    private fun reverseDefaultRotation(): Boolean = runCatching {
        val res = Resources.getSystem()
        val id = res.getIdentifier("config_reverseDefaultRotation", "bool", "android")
        id != 0 && res.getBoolean(id)
    }.getOrDefault(false)
}
