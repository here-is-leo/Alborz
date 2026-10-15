"""
ویرایش و حذف متادیتا
"""
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Set

from PIL import Image

try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False

from .models import MetadataResult, MetadataEntry


# ---------- امتیاز حریم خصوصی ----------

# وزن هر گروه تگ در کاهش امتیاز
PRIVACY_WEIGHTS = {
    # GPS فوق‌العاده حساس
    "gps": 30,
    # اطلاعات هویتی
    "artist": 15,
    "copyright": 10,
    "owner": 15,
    "serialnumber": 15,
    "lensserialnumber": 10,
    "bodyserialnumber": 10,
    "imageuniqueid": 10,
    # تاریخ دقیق
    "datetimeoriginal": 10,
    "datetimedigitized": 5,
    "datetime": 5,
    # دستگاه
    "make": 3,
    "model": 5,
    "lensmodel": 3,
    "software": 3,
    # کامنت
    "usercomment": 5,
    "imagedescription": 3,
    # اطلاعات شبکه
    "gpsprocessingmethod": 2,
    "gpsdatestamp": 2,
    "gpstimestamp": 2,
}


def compute_privacy_score(entries: List[MetadataEntry]) -> dict:
    """
    محاسبه امتیاز حریم خصوصی از ۱۰۰
    هر چه پایین‌تر، خطرناک‌تر
    """
    score = 100
    risks = []

    # بررسی GPS
    has_gps = any(
        e.group == "GPS" and e.tag not in ("GPSVersionID",)
        for e in entries
    ) or any(e.tag in ("DecimalLatitude", "DecimalLongitude") for e in entries)

    if has_gps:
        score -= PRIVACY_WEIGHTS["gps"]
        risks.append({"level": "high", "label": "موقعیت GPS",
                      "detail": "مکان دقیق عکس در فایل ذخیره شده است"})

    # بررسی تگ‌های حساس
    checked = set()
    for e in entries:
        tag_lower = e.tag.lower().split()[-1]  # حذف پیشوندها
        if tag_lower in checked:
            continue
        weight = PRIVACY_WEIGHTS.get(tag_lower)
        if weight:
            checked.add(tag_lower)
            score -= weight
            if weight >= 10:
                risks.append({
                    "level": "medium",
                    "label": e.tag,
                    "detail": f"مقدار: {str(e.value)[:60]}",
                })

    # بررسی شماره سریال در MakerNotes
    for e in entries:
        t = e.tag.lower()
        if "serial" in t and t not in checked:
            score -= 8
            checked.add(t)

    score = max(0, min(100, score))

    # سطح
    if score >= 80:
        level = "safe"
        color = "green"
        label = "امن"
    elif score >= 50:
        level = "medium"
        color = "yellow"
        label = "متوسط"
    else:
        level = "danger"
        color = "red"
        label = "خطرناک"

    return {
        "score": score,
        "level": level,
        "color": color,
        "label": label,
        "risks": risks,
    }


# ---------- حذف متادیتا ----------

def strip_metadata(
    input_path: str,
    output_path: str,
    keep_groups: Optional[Set[str]] = None,
) -> str:
    """
    حذف متادیتا از فایل

    Args:
        input_path: مسیر فایل ورودی
        output_path: مسیر فایل خروجی
        keep_groups: گروه‌هایی که باید حفظ شوند (None = حذف همه)

    Returns:
        مسیر فایل خروجی
    """
    src = Path(input_path)
    dst = Path(output_path)
    mime = _guess_mime(src)

    if mime.startswith("image/"):
        return _strip_image(src, dst, keep_groups)
    elif mime.startswith("video/"):
        return _strip_video(src, dst, keep_groups)
    elif mime.startswith("audio/"):
        return _strip_audio(src, dst, keep_groups)
    else:
        # کپی خام
        import shutil
        shutil.copy2(src, dst)
        return str(dst)


def _guess_mime(path: Path) -> str:
    import mimetypes
    mime, _ = mimetypes.guess_type(str(path))
    return mime or ""


def _strip_image(src: Path, dst: Path, keep_groups: Optional[Set[str]]) -> str:
    """حذف متادیتا از عکس"""
    # اگه کامل باید پاک بشه
    if not keep_groups:
        img = Image.open(src)
        # کپی داده‌های خام تصویر
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        # ذخیره با کیفیت بالا و بدون exif
        save_kwargs = {"optimize": True}
        if src.suffix.lower() in (".jpg", ".jpeg"):
            save_kwargs["quality"] = 95
            save_kwargs["exif"] = b""
        elif src.suffix.lower() == ".png":
            save_kwargs["pnginfo"] = None
        clean.save(dst, **save_kwargs)
        return str(dst)

    # حالت انتخابی: باید piexif داشته باشیم
    if not HAS_PIEXIF:
        raise RuntimeError("برای حذف انتخابی، piexif نصب باشد: pip install piexif")

    if src.suffix.lower() not in (".jpg", ".jpeg", ".tiff", ".tif"):
        # برای فرمت‌های غیر JPEG، به حالت کامل برگرد
        return _strip_image(src, dst, None)

    exif_dict = piexif.load(str(src))

    # حذف گروه‌های درخواستی
    if "GPS" not in keep_groups:
        exif_dict["GPS"] = {}
    if "EXIF" not in keep_groups:
        # فقط تگ‌های پایه IFD0 رو نگه دار
        exif_dict["Exif"] = {}
    if "MakerNote" not in keep_groups:
        exif_dict["Exif"].pop(piexif.ExifIFD.MakerNote, None)

    exif_bytes = piexif.dump(exif_dict)

    img = Image.open(src)
    img.save(dst, exif=exif_bytes, quality=95)
    return str(dst)


def _strip_video(src: Path, dst: Path, keep_groups: Optional[Set[str]]) -> str:
    """حذف متادیتا از ویدیو با ffmpeg"""
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-map_metadata", "-1",  # حذف همه متادیتا
            "-map", "0",            # کپی همه استریم‌ها
            "-c", "copy",
            str(dst),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {result.stderr.decode()[:200]}")
        return str(dst)
    except FileNotFoundError:
        raise RuntimeError("FFmpeg نصب نیست. برای پردازش ویدیو لازم است.")


def _strip_audio(src: Path, dst: Path, keep_groups: Optional[Set[str]]) -> str:
    """حذف متادیتا از صدا با mutagen"""
    import shutil
    from mutagen import File as MutagenFile

    # کپی فایل
    shutil.copy2(src, dst)

    # تلاش برای حذف تگ‌ها
    try:
        audio = MutagenFile(dst)
        if audio and audio.tags:
            audio.tags.clear()
            audio.save()
    except Exception:
        pass
    return str(dst)


# ---------- حذف انتخابی بر اساس تگ ----------

def strip_tags(
    input_path: str,
    output_path: str,
    remove_tags: Set[str],
) -> str:
    """حذف تگ‌های مشخص از فایل"""
    if not HAS_PIEXIF:
        raise RuntimeError("piexif نصب نیست")

    src = Path(input_path)
    dst = Path(output_path)

    if src.suffix.lower() not in (".jpg", ".jpeg", ".tiff", ".tif"):
        raise ValueError("حذف انتخابی فقط برای JPEG/TIFF پشتیبانی می‌شود")

    exif_dict = piexif.load(str(src))
    remove_lower = {t.lower() for t in remove_tags}

    for ifd_name in ("0th", "Exif", "GPS", "1st", "Interop"):
        if ifd_name not in exif_dict:
            continue
        ifd = exif_dict[ifd_name]
        to_remove = []
        for tag_id in list(ifd.keys()):
            tag_name = _piexif_tag_name(ifd_name, tag_id)
            if tag_name and tag_name.lower() in remove_lower:
                to_remove.append(tag_id)
        for tag_id in to_remove:
            del ifd[tag_id]

    exif_bytes = piexif.dump(exif_dict)
    img = Image.open(src)
    img.save(dst, exif=exif_bytes, quality=95)
    return str(dst)


def _piexif_tag_name(ifd_name: str, tag_id: int) -> Optional[str]:
    """گرفتن نام تگ از piexif"""
    try:
        if ifd_name == "0th":
            return piexif.TAGS["0th"].get(tag_id, {}).get("name")
        if ifd_name == "Exif":
            return piexif.TAGS["Exif"].get(tag_id, {}).get("name")
        if ifd_name == "GPS":
            return piexif.TAGS["GPS"].get(tag_id, {}).get("name")
        if ifd_name == "1st":
            return piexif.TAGS["1st"].get(tag_id, {}).get("name")
    except Exception:
        return None
    return None