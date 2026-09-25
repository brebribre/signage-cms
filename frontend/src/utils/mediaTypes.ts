/**
 * What the media library accepts — the same list the backend enforces
 * (backend/app/services/media.py::ALLOWED_MIME). Change both together.
 *
 * Screens never get these as uploaded: the server turns every video into one H.264 MP4 and every
 * picture into JPEG or PNG (backend services/video_streams.py and pictures.py), keeping only the
 * converted copy. GIF is not accepted for now — screens would show only its first frame.
 */

/** Type by extension, for the files a browser leaves untyped — Windows often has no type for
 *  .heic, and sometimes none for .mov. */
const BY_EXTENSION: Record<string, string> = {
  jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp',
  heic: 'image/heic', heif: 'image/heif', avif: 'image/avif', tif: 'image/tiff', tiff: 'image/tiff', bmp: 'image/bmp',
  mp4: 'video/mp4', m4v: 'video/mp4', mov: 'video/quicktime',
}

/** For a file picker's `accept`: the types, and the extensions a browser may not type. */
export const ACCEPTED_MEDIA = [
  'image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif', 'image/avif', 'image/tiff', 'image/bmp',
  'video/mp4', 'video/quicktime',
  '.heic', '.heif', '.mov', '.avif', '.tif', '.tiff', '.bmp',
].join(',')

/** Shown under every upload area, so a refused file is never a surprise. */
export const SUPPORTED_FILE_TYPES = [
  'Supported image file types: JPEG, PNG, WebP, HEIC, AVIF, TIFF, BMP',
  'Supported video file types: MP4, MOV',
]

/** A file's type as the server should be told it: the browser's own when it has one, else read
 *  from the extension. Empty when neither says — the server then refuses it with its list. */
export function mediaContentType(file: File): string {
  if (file.type && file.type !== 'application/octet-stream') {
    // Some browsers say image/x-ms-bmp; the server knows it as image/bmp.
    return file.type === 'image/x-ms-bmp' ? 'image/bmp' : file.type
  }
  const ext = file.name.includes('.') ? file.name.split('.').pop()!.toLowerCase() : ''
  return BY_EXTENSION[ext] ?? file.type
}
