import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "com.fortu.player"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.fortu.player"
        // API 24 (Android 7). Signage sticks and panels run several versions behind, and
        // Media3 supports back to 21 — 24 is a comfortable floor that still gets modern
        // WebView/codec behaviour on anything actually shipping.
        minSdk = 24
        targetSdk = 35
        // Overridable for a test install over a screen (or emulator) that already carries a higher
        // test build: ./gradlew assembleRelease -PversionCode=200 -PversionName=1.2.0-emu. A real
        // release never passes these; it edits the two numbers here.
        versionCode = (project.findProperty("versionCode") as String?)?.toInt() ?: 37
        versionName = (project.findProperty("versionName") as String?) ?: "1.3.6"

        // The API base URL is compiled in, not configured on the device — a screen with no
        // keyboard cannot be asked to type one. Override per build:
        //   ./gradlew assembleRelease -PapiBaseUrl=https://your-api.example.com
        val apiBaseUrl = (project.findProperty("apiBaseUrl") as String?)
            ?: "https://signage-cms-production.up.railway.app"
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
        // Plain HTTP is only ever allowed for a build that was explicitly pointed at a plain-HTTP
        // backend (a developer's own machine). The production address is HTTPS, so a production
        // build keeps Android's default of refusing cleartext — the same property decides both.
        manifestPlaceholders["usesCleartextTraffic"] = apiBaseUrl.startsWith("http://").toString()

        // Push prototype (see PushClient / MqttPushClient). Defaults to the real deployed
        // broker, same reasoning as apiBaseUrl above — per-device credentials (each
        // device's own username/password, minted at pairing, scoped by the broker's
        // device-role ACL to its own topic) shipped and were verified live, so there is no
        // longer a shared-secret reason to keep this opt-in. No username/password build
        // config at all: every device gets its own MQTT credential from the pairing
        // response, never a build-time one (see PairPollResponse.mqttPassword,
        // TokenStore.mqttPassword).
        //
        // Port and TLS default *together with* host, not independently — passing only
        // -PmqttHost must not silently pull in the production port/TLS pairing. (This bit
        // a local test: -PmqttHost=10.0.2.2 alone landed on the leftover default port
        // 46790 — the real broker's — instead of the local broker's 1883, and the app sat
        // there failing to connect with nothing but silence to show for it.) Point this at
        // docker-compose's local broker for dev, which is anonymous and needs no TLS:
        //   ./gradlew installDebug -PmqttHost=192.168.1.23
        // (a LAN IP, not "localhost" — that resolves to the screen itself, not your
        // machine; port/TLS follow automatically). Or disable push outright: -PmqttHost=
        val mqttHostOverridden = project.hasProperty("mqttHost")
        val mqttHost = (project.findProperty("mqttHost") as String?) ?: "altaria.proxy.rlwy.net"
        val mqttPort = (project.findProperty("mqttPort") as String?)
            ?: if (mqttHostOverridden) "1883" else "46790"
        val mqttTls = (project.findProperty("mqttTls") as String?)
            ?: if (mqttHostOverridden) "false" else "true"
        buildConfigField("String", "MQTT_HOST", "\"$mqttHost\"")
        buildConfigField("int", "MQTT_PORT", mqttPort)
        buildConfigField("boolean", "MQTT_TLS", mqttTls)
    }

    // The real release key lives outside the repo, in ~/.paskall/keystore.properties (storeFile,
    // storePassword, keyAlias, keyPassword) — created 2026-09-21. Android only lets an app
    // update over an installed copy signed with the SAME key, so this key must never change,
    // and must be backed up: losing it means every screen out there needs a manual reinstall,
    // and a Play Store listing could never be updated again.
    //
    // Falls back to the debug key when the file is missing (a machine without the key can still
    // build for a test), or when asked with -PuseDebugKey (the emulator carries a debug-signed
    // Device Owner install that a release-signed build cannot update). A build meant for
    // screens must come from a machine that has the key — the warning below says which it was.
    val keystoreProperties = Properties().apply {
        val file = File(System.getProperty("user.home"), ".paskall/keystore.properties")
        if (file.exists()) file.inputStream().use { load(it) }
    }
    val useDebugKey = project.hasProperty("useDebugKey") || keystoreProperties.isEmpty
    if (!useDebugKey) {
        signingConfigs.create("release") {
            storeFile = file(keystoreProperties["storeFile"] as String)
            storePassword = keystoreProperties["storePassword"] as String
            keyAlias = keystoreProperties["keyAlias"] as String
            keyPassword = keystoreProperties["keyPassword"] as String
        }
    } else {
        logger.warn("Signing release with the DEBUG key (no ~/.paskall/keystore.properties or -PuseDebugKey) — not for real screens.")
    }

    buildTypes {
        debug {
            // So a debug build can be installed alongside a release one on the same screen
            // while testing a new version.
            applicationIdSuffix = ".debug"
        }
        release {
            // Not minified, on purpose. R8 shrank the APK from 12 MB to 3.6 MB (1.3.0), but it
            // also stripped what two libraries reach by reflection and the app crashed at
            // start-up until the right keep rules were found — and every future library
            // upgrade could do the same, with only a device test to catch it. A bigger
            // download is the safer trade for a fleet that updates itself unattended.
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // The real key when this machine has it (see above); the debug key otherwise.
            signingConfig = if (useDebugKey) signingConfigs.getByName("debug") else signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources {
            // Netty (hivemq-mqtt-client's transport) ships the same META-INF housekeeping
            // file in several of its jars — harmless at runtime, but the merge step that
            // builds the APK's resources treats a genuine duplicate as fatal. None of these
            // are ever read by the app itself.
            excludes += "META-INF/INDEX.LIST"
            excludes += "META-INF/io.netty.versions.properties"
        }
    }

    testOptions {
        unitTests {
            // PlayerEngine has no Android dependencies, but it does call android.util.Log.
            // Returning defaults keeps those calls harmless instead of throwing
            // "not mocked" and failing every test for an irrelevant reason.
            isReturnDefaultValues = true
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.service)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.media3.exoplayer)
    implementation(libs.media3.ui)
    implementation(libs.media3.datasource.okhttp)
    implementation(libs.okhttp)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.coil.compose)
    implementation(libs.hivemq.mqtt.client)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
}
