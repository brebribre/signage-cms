/**
 * What the media library accepts — the same list the backend enforces
 * (backend/app/services/media.py::ALLOWED_MIME). Change both together.
 */

/** For a file picker's `accept`. */
export const ACCEPTED_MEDIA = 'image/jpeg,image/png,image/webp,image/gif,video/mp4'

/** Shown under every upload area, so a refused file is never a surprise. */
export const SUPPORTED_FILE_TYPES = [
  'Supported image file types: JPEG, PNG, WebP, GIF',
  'Supported video file types: MP4 (H.264)',
]
