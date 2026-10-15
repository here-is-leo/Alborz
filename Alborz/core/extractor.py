import hashlib
import mimetypes
import subprocess
import json
from pathlib import Path
from typing import List

import exifread
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from mutagen import File as MutagenFile

from .models import MetadataEntry, MetadataResult


# ---------- Helpers ----------

def _file_hashes(path: Path):
    """محاسبه MD5 و SHA256 فایل"""
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
            sha.update(chunk)
    return md5.hexdigest(), sha.hexdigest()


def _guess_mime(path: Path) -> str:
    """تشخیص MIME type از روی پسوند"""
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _safe_decode(value):
    """تبدیل هر مقدار به نوع سازگار با JSON"""
    cls_name = value.__class__.__name__

    # IFDRational از Pillow
    if cls_name == "IFDRational":
        try:
            return float(value)
        except Exception:
            return str(value)

    # Ratio و Fraction از exifread
    if cls_name in ("Ratio", "Fraction"):
        try:
            return float(value)
        except Exception:
            return str(value)

    # بایت‌ها
    if isinstance(value, (bytes, bytearray)):
        try:
            decoded = value.decode("utf-8", errors="ignore").strip("\x00")
            # اگه کاراکتر کنترلی داره، به صورت هگز نشون بده
            if any(ord(c) < 32 and c not in "\t\n\r" for c in decoded):
                return value.hex()
            return decoded
        except Exception:
            return str(value)

    # لیست و تاپل
    if isinstance(value, (list, tuple)):
        return [_safe_decode(v) for v in value]

    # دیکشنری
    if isinstance(value, dict):
        return {str(k): _safe_decode(v) for k, v in value.items()}

    # انواع پایه
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value

    # هر چیز دیگه
    return str(value)


def _convert_gps_to_degrees(value):
    """تبدیل مختصات GPS (درجه، دقیقه، ثانیه) به درجه اعشاری"""
    try:
        d = float(value[0].num) / float(value[0].den)
        m = float(value[1].num) / float(value[1].den)
        s = float(value[2].num) / float(value[2].den)
        return round(d + m / 60 + s / 3600, 6)
    except Exception:
        try:
            # گاهی مقادیر IFDRational هستن
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return round(d + m / 60 + s / 3600, 6)
        except Exception:
            return None


# ---------- EXIF via Pillow (comprehensive) ----------

def _extract_exif_pillow(path: Path) -> List[MetadataEntry]:
    """استخراج کامل EXIF/GPS/ExifIFD با Pillow"""
    entries = []
    try:
        img = Image.open(path)

        # 1) IFD0 - تگ‌های اصلی
        exif = img.getexif()
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, f"Tag_{tag_id}")
                entries.append(MetadataEntry(
                    group="EXIF",
                    tag=tag,
                    value=_safe_decode(value),
                ))

            # 2) ExifIFD (0x8769) - DateTimeOriginal, LensModel, ISO و...
            try:
                exif_ifd = exif.get_ifd(0x8769)
                for tag_id, value in (exif_ifd or {}).items():
                    tag = TAGS.get(tag_id, f"ExifTag_{tag_id}")
                    entries.append(MetadataEntry(
                        group="ExifIFD",
                        tag=tag,
                        value=_safe_decode(value),
                    ))
            except Exception:
                pass

            # 3) GPS IFD (0x8825)
            try:
                gps_ifd = exif.get_ifd(0x8825)
                for tag_id, value in (gps_ifd or {}).items():
                    tag = GPSTAGS.get(tag_id, f"GPSTag_{tag_id}")
                    entries.append(MetadataEntry(
                        group="GPS",
                        tag=tag,
                        value=_safe_decode(value),
                    ))

                # مختصات اعشاری
                lat = gps_ifd.get(2)
                lat_ref = gps_ifd.get(1)
                lon = gps_ifd.get(4)
                lon_ref = gps_ifd.get(3)
                if lat and lon:
                    lat_d = _convert_gps_to_degrees(lat)
                    lon_d = _convert_gps_to_degrees(lon)
                    if lat_d is not None and lon_d is not None:
                        if lat_ref == "S":
                            lat_d = -lat_d
                        if lon_ref == "W":
                            lon_d = -lon_d
                        entries.append(MetadataEntry(
                            group="GPS", tag="DecimalLatitude", value=lat_d))
                        entries.append(MetadataEntry(
                            group="GPS", tag="DecimalLongitude", value=lon_d))
            except Exception:
                pass

    except Exception as e:
        entries.append(MetadataEntry(group="Error", tag="PillowExif", value=str(e)))
    return entries


# ---------- EXIF via exifread (backup) ----------

def _extract_exif_exifread(path: Path) -> List[MetadataEntry]:
    """پشتیبان: استخراج EXIF با exifread"""
    entries = []
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=True)
        for tag, value in tags.items():
            if tag.startswith("Thumbnail") or tag.startswith("JPEGThumbnail"):
                continue
            entries.append(MetadataEntry(
                group="ExifRead",
                tag=tag,
                value=_safe_decode(str(value)),
            ))
    except Exception as e:
        entries.append(MetadataEntry(group="Error", tag="ExifRead", value=str(e)))
    return entries


# ---------- Audio ----------

def _extract_audio(path: Path) -> List[MetadataEntry]:
    """استخراج متادیتای فایل صوتی با Mutagen"""
    entries = []
    try:
        audio = MutagenFile(path)
        if not audio:
            return entries
        entries.append(MetadataEntry(
            group="Audio", tag="Format", value=type(audio).__name__))

        if hasattr(audio, "info") and audio.info:
            for k in ("length", "bitrate", "sample_rate", "channels"):
                v = getattr(audio.info, k, None)
                if v is not None:
                    entries.append(MetadataEntry(
                        group="Audio", tag=k, value=_safe_decode(v)))

        if audio.tags:
            for k, v in audio.tags.items():
                entries.append(MetadataEntry(
                    group="AudioTag", tag=str(k), value=_safe_decode(str(v))))
    except Exception as e:
        entries.append(MetadataEntry(group="Error", tag="Mutagen", value=str(e)))
    return entries


# ---------- Video (ffprobe) ----------

def _extract_video_ffprobe(path: Path) -> List[MetadataEntry]:
    """استخراج متادیتای ویدیو با ffprobe"""
    entries = []
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout or "{}")
    except FileNotFoundError:
        entries.append(MetadataEntry(
            group="Warning", tag="ffprobe",
            value="FFmpeg نصب نیست - ویدیو پردازش نشد"))
        return entries
    except Exception as e:
        entries.append(MetadataEntry(group="Error", tag="ffprobe", value=str(e)))
        return entries

    # Format
    fmt = data.get("format", {})
    for k, v in fmt.items():
        if k != "tags":
            entries.append(MetadataEntry(
                group="VideoFormat", tag=k, value=_safe_decode(v)))
    for k, v in fmt.get("tags", {}).items():
        entries.append(MetadataEntry(
            group="QuickTime", tag=k, value=_safe_decode(v)))

    # Streams
    for i, s in enumerate(data.get("streams", [])):
        for k, v in s.items():
            if k == "tags":
                for tk, tv in v.items():
                    entries.append(MetadataEntry(
                        group=f"Stream{i}", tag=tk, value=_safe_decode(tv)))
            else:
                entries.append(MetadataEntry(
                    group=f"Stream{i}", tag=k, value=_safe_decode(v)))
    return entries


# ---------- Main entry ----------

def extract_metadata(file_path: str) -> MetadataResult:
    """تابع اصلی: استخراج تمام متادیتای یک فایل"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"فایل یافت نشد: {file_path}")

    md5, sha = _file_hashes(path)
    mime = _guess_mime(path)

    result = MetadataResult(
        filename=path.name,
        filesize=path.stat().st_size,
        mime_type=mime,
        file_hash_md5=md5,
        file_hash_sha256=sha,
    )

    # بر اساس نوع فایل extractor مناسب رو انتخاب کن
    if mime.startswith("image/"):
        result.entries += _extract_exif_pillow(path)
        result.entries += _extract_exif_exifread(path)
    elif mime.startswith("video/"):
        result.entries += _extract_video_ffprobe(path)
    elif mime.startswith("audio/"):
        result.entries += _extract_audio(path)
    else:
        # ناشناخته: همه رو امتحان کن
        result.entries += _extract_exif_pillow(path)
        result.entries += _extract_video_ffprobe(path)
        result.entries += _extract_audio(path)

    return result