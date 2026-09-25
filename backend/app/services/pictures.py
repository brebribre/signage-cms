"""Every uploaded picture, in a form every screen and browser can show.

The rules, applied on the server after upload (services/video_streams.py runs them, on the same
background thread as video conversion):

- **JPEG, PNG and WebP that need nothing are left exactly as uploaded.** Re-compressing a good
  photo only softens it, for nothing.
- **Anything else becomes JPEG** — HEIC and HEIF (iPhone photos), AVIF, TIFF, BMP — which only
  Safari (for HEIC) or nothing at all shows otherwise, and which Android before 9 can't decode.
- **A picture with transparent areas becomes PNG instead**, since JPEG has no transparency and a
  logo would get a white box around it.
- **Anything larger than 4K on its long side is brought down to 4K.** A phone photo is twelve
  megapixels or more; no panel shows more than 4K, and the extra only costs a cheap box
  download time, memory and decoding.
- **A photo's orientation flag is applied to the picture itself.** Phones store "turned" as a
  flag that browsers and Android don't always read alike; applied once, a photo can't be
  upright on one screen and sideways on another.

Only the result is kept: when a picture is converted, the converted copy replaces the upload.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

try:  # HEIC/HEIF support; without it those uploads simply fail to convert, and say so.
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

#: What every screen and browser shows as it is — anything else is converted.
SCREEN_SAFE_MIME = {"image/jpeg", "image/png", "image/webp"}
_SAFE_FORMATS = {"JPEG", "PNG", "WEBP"}
#: The long side a picture is brought down to — a 4K panel's.
MAX_EDGE_PX = 3840
#: The long side of the small preview in the media library; the same as the browser's.
THUMB_MAX_PX = 480
JPEG_QUALITY = 90
_EXIF_ORIENTATION = 0x0112


class PictureError(Exception):
    """The file could not be read as a picture."""


@dataclass(frozen=True)
class Picture:
    """What a picture ended up as. `converted` is False when the upload was already fine and
    `path` is the upload itself."""

    path: Path
    mime: str
    extension: str
    width: int
    height: int
    converted: bool


def _has_transparency(im: Image.Image) -> bool:
    if im.mode in ("RGBA", "LA", "PA"):
        alpha = im.getchannel("A")
        return alpha.getextrema()[0] < 255  # an alpha channel that is all opaque is no reason
    return im.mode == "P" and "transparency" in im.info


def normalise(source: Path, out_dir: Path) -> Picture:
    """Apply the rules to `source`. Writes a new file into `out_dir` only when something had
    to change. Raises PictureError when the file can't be read at all."""
    try:
        with Image.open(source) as im:
            im.load()
            fmt = im.format or ""
            orientation = im.getexif().get(_EXIF_ORIENTATION, 1)
            too_big = max(im.size) > MAX_EDGE_PX
            if fmt in _SAFE_FORMATS and not too_big and orientation in (0, 1):
                mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[fmt]
                ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[fmt]
                return Picture(source, mime, ext, im.width, im.height, converted=False)

            icc = im.info.get("icc_profile")
            picture = ImageOps.exif_transpose(im)
            if max(picture.size) > MAX_EDGE_PX:
                picture.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX), Image.Resampling.LANCZOS)

            if _has_transparency(picture):
                dest = out_dir / "picture.png"
                picture.convert("RGBA").save(dest, "PNG", optimize=True, icc_profile=icc)
                return Picture(dest, "image/png", "png", picture.width, picture.height, converted=True)
            dest = out_dir / "picture.jpg"
            picture.convert("RGB").save(
                dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True, icc_profile=icc
            )
            return Picture(dest, "image/jpeg", "jpg", picture.width, picture.height, converted=True)
    except PictureError:
        raise
    except Exception as exc:  # Pillow raises a handful of types for unreadable files
        raise PictureError(f"not a readable picture: {exc}") from exc


def thumbnail(source: Path, dest: Path) -> None:
    """The library's small preview: the picture as shown, at most THUMB_MAX_PX on its long
    side, as JPEG — what the browser makes at upload when it can read the file itself."""
    try:
        with Image.open(source) as im:
            picture = ImageOps.exif_transpose(im)
            picture.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX), Image.Resampling.LANCZOS)
            if _has_transparency(picture):
                # Flattened onto white: a preview tile, not the picture itself.
                background = Image.new("RGB", picture.size, "white")
                background.paste(picture.convert("RGBA"), mask=picture.convert("RGBA").getchannel("A"))
                picture = background
            picture.convert("RGB").save(dest, "JPEG", quality=80)
    except Exception as exc:
        raise PictureError(f"no preview: {exc}") from exc


def converted_filename(filename: str, extension: str) -> str:
    """The upload's own name with the extension of what it became: IMG_0042.HEIC → IMG_0042.jpg."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return f"{stem or 'picture'}.{extension}"
