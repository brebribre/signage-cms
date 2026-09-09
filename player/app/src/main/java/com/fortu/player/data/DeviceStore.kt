package com.fortu.player.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first

private val Context.dataStore by preferencesDataStore(name = "fortu_player")

/**
 * The device token and the last manifest ETag.
 *
 * Plain DataStore, not encrypted. The token is a bearer credential sitting on hardware you
 * physically control: `androidx.security-crypto` is deprecated, anyone with root and the
 * device in hand wins regardless, and the controls that actually matter are Device Owner
 * mode plus `POST /devices/{id}/unpair` on the server, which revokes it centrally. Encrypting
 * it locally would be theatre.
 */
class DeviceStore(private val context: Context) : com.fortu.player.TokenStore {
    private val tokenKey = stringPreferencesKey("device_token")
    private val etagKey = stringPreferencesKey("manifest_etag")
    private val nameKey = stringPreferencesKey("device_name")
    private val manifestKey = stringPreferencesKey("manifest_json")
    private val deviceIdKey = stringPreferencesKey("device_id")

    override suspend fun token(): String? = context.dataStore.data.first()[tokenKey]
    override suspend fun etag(): String? = context.dataStore.data.first()[etagKey]
    override suspend fun name(): String? = context.dataStore.data.first()[nameKey]

    override suspend fun saveToken(token: String, name: String?) {
        context.dataStore.edit {
            it[tokenKey] = token
            if (name != null) it[nameKey] = name
        }
    }

    override suspend fun saveEtag(etag: String) {
        context.dataStore.edit { it[etagKey] = etag }
    }

    override suspend fun manifestJson(): String? = context.dataStore.data.first()[manifestKey]

    override suspend fun saveManifestJson(json: String) {
        context.dataStore.edit { it[manifestKey] = json }
    }

    override suspend fun deviceId(): String? = context.dataStore.data.first()[deviceIdKey]

    override suspend fun saveDeviceId(id: String) {
        context.dataStore.edit { it[deviceIdKey] = id }
    }

    /** Called when the server rejects our token — drops everything so the app re-pairs. */
    override suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }
}
