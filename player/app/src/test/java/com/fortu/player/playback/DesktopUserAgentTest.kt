package com.fortu.player.playback

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * A signage panel is a desktop-sized screen, and a site decides which layout to serve largely on
 * the user agent. Android's WebView announces a phone; these are the real strings it produces,
 * and what has to survive the rewrite: the Chrome version (so a site's feature detection still
 * sees the browser it actually is) and nothing that says "phone".
 */
class DesktopUserAgentTest {

    private val webViewOnPhone =
        "Mozilla/5.0 (Linux; Android 15; Pixel Tablet Build/AP3A.240905.015; wv) " +
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.219 Mobile Safari/537.36"

    private val webViewOnTablet =
        "Mozilla/5.0 (Linux; Android 14; SM-X200) AppleWebKit/537.36 (KHTML, like Gecko) " +
            "Chrome/120.0.6099.43 Safari/537.36"

    @Test
    fun `the phone markers are gone`() {
        val ua = desktopUserAgent(webViewOnPhone)
        assertFalse("no Android platform token: $ua", ua.contains("Android"))
        assertFalse("no WebView marker: $ua", ua.contains("wv"))
        assertFalse("no Mobile marker: $ua", ua.contains("Mobile"))
    }

    @Test
    fun `it claims a desktop platform`() {
        assertTrue(desktopUserAgent(webViewOnPhone).contains("X11; Linux x86_64"))
        assertTrue(desktopUserAgent(webViewOnTablet).contains("X11; Linux x86_64"))
    }

    @Test
    fun `the browser it really is survives`() {
        // Whatever system WebView the device ships, the site should see that Chrome — the
        // rewrite is about the platform, not about pretending to be a different browser.
        assertTrue(desktopUserAgent(webViewOnPhone).contains("Chrome/124.0.6367.219"))
        assertTrue(desktopUserAgent(webViewOnPhone).contains("Safari/537.36"))
        assertTrue(desktopUserAgent(webViewOnTablet).contains("Chrome/120.0.6099.43"))
    }

    @Test
    fun `a tablet string without Mobile still becomes desktop`() {
        assertEquals(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) " +
                "Chrome/120.0.6099.43 Safari/537.36",
            desktopUserAgent(webViewOnTablet),
        )
    }
}
