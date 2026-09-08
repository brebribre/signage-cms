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
        versionCode = 1
        versionName = "1.0.0"

        // The API base URL is compiled in, not configured on the device — a screen with no
        // keyboard cannot be asked to type one. Override per build:
        //   ./gradlew assembleRelease -PapiBaseUrl=https://your-api.example.com
        val apiBaseUrl = (project.findProperty("apiBaseUrl") as String?)
            ?: "https://signage-cms-production.up.railway.app"
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
    }

    buildTypes {
        debug {
            // So a debug build can be installed alongside a release one on the same screen
            // while testing a new version.
            applicationIdSuffix = ".debug"
        }
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Signed with the debug key so `assembleRelease` produces an installable APK with
            // no keystore setup. Fine for sideloading onto screens you own; a real Play
            // Store release would need its own signing config.
            signingConfig = signingConfigs.getByName("debug")
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

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
}
