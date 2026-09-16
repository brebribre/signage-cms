/**
 * The device token, the last manifest and its ETag — the Android player's `data/DeviceStore.kt`,
 * on `localStorage`.
 *
 * Not encrypted, for the reason DeviceStore.kt gives: it is a bearer credential on hardware you
 * physically control, and the control that matters is revoking it centrally from the CMS.
 */

export interface TokenStore {
  token(): string | null
  etag(): string | null
  name(): string | null
  saveToken(token: string, name: string | null | undefined): void
  saveEtag(etag: string): void
  /** Persisted so a screen that restarts can play immediately from its cache, with no network. */
  manifestJson(): string | null
  saveManifestJson(json: string): void
  deviceId(): string | null
  saveDeviceId(id: string): void
  clear(): void
}

const PREFIX = 'fortu_player.'
const KEYS = ['device_token', 'manifest_etag', 'device_name', 'manifest_json', 'device_id']

export class LocalDeviceStore implements TokenStore {
  constructor(private readonly storage: Storage = window.localStorage) {}

  private get(key: string): string | null {
    try {
      return this.storage.getItem(PREFIX + key)
    } catch {
      return null
    }
  }

  private set(key: string, value: string): void {
    try {
      this.storage.setItem(PREFIX + key, value)
    } catch (e) {
      // Quota or a locked-down browser. The manifest is the only large value, and losing it
      // costs an offline restart — not the pairing — so it is not worth failing over.
      console.warn('[FortuPlayer] could not persist', key, e)
    }
  }

  token() { return this.get('device_token') }
  etag() { return this.get('manifest_etag') }
  name() { return this.get('device_name') }

  saveToken(token: string, name: string | null | undefined) {
    this.set('device_token', token)
    if (name != null) this.set('device_name', name)
  }

  saveEtag(etag: string) { this.set('manifest_etag', etag) }
  manifestJson() { return this.get('manifest_json') }
  saveManifestJson(json: string) { this.set('manifest_json', json) }
  deviceId() { return this.get('device_id') }
  saveDeviceId(id: string) { this.set('device_id', id) }

  /** Called when the server rejects our token — drops everything so the screen re-pairs. */
  clear() {
    for (const key of KEYS) {
      try {
        this.storage.removeItem(PREFIX + key)
      } catch {
        /* nothing further to do */
      }
    }
  }
}
