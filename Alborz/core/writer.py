"""
نوشتن و ویرایش متادیتا در فایل
"""
from pathlib import Path
from typing import Dict, Any, Optional

from PIL import Image

try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False


# نگاشت نام تگ به (ifd, tag_id)
def _build_tag_map():
    """ساخت نگاشت کامل نام تگ به (ifd, id)"""
    tag_map = {}
    if not HAS_PIEXIF:
        return tag_map

    for ifd_name in ("0th", "Exif", "GPS", "1st", "Interop"):
        if ifd_name not in piexif.TAGS:
            continue
        for tag_id, info in piexif.TAGS[ifd_name].items():
            name = info.get("name", "")
            if name:
                tag_map[name.lower()] = (ifd_name, tag_id)
    return tag_map


TAG_MAP = _build_tag_map()


def edit_image_metadata(
    input_path: str,
    output_path: str,
    changes: Dict[str, Any],
) -> str:
    """
    ویرایش متادیتای یک عکس

    Args:
        input_path: مسیر فایل ورودی
        output_path: مسیر فایل خروجی
        changes: دیکشنری {tag_name: new_value}

    Returns:
        مسیر فایل خروجی
    """
    if not HAS_PIEXIF:
        raise RuntimeError("piexif نصب نیست: pip install piexif")

    src = Path(input_path)
    dst = Path(output_path)
    suffix = src.suffix.lower()

    if suffix not in (".jpg", ".jpeg", ".tiff", ".tif"):
        raise ValueError("ویرایش فقط برای JPEG/TIFF پشتیبانی می‌شود")

    try:
        exif_dict = piexif.load(str(src))
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "Interop": {}}

    # اعمال تغییرات
    for tag_name, new_value in changes.items():
        entry = TAG_MAP.get(tag_name.lower())
        if not entry:
            continue
        ifd_name, tag_id = entry

        if ifd_name not in exif_dict:
            exif_dict[ifd_name] = {}

        # تبدیل مقدار بر اساس نوع مورد انتظار
        converted = _convert_value(ifd_name, tag_id, new_value)

        # اگه None، یعنی حذف تگ
        if converted is None:
            exif_dict[ifd_name].pop(tag_id, None)
        else:
            exif_dict[ifd_name][tag_id] = converted

    # ذخیره
    exif_bytes = piexif.dump(exif_dict)
    img = Image.open(src)
    img.save(dst, exif=exif_bytes, quality=95)
    return str(dst)


def _convert_value(ifd_name: str, tag_id: int, value: Any):
    """تبدیل مقدار به نوع مورد انتظار piexif"""
    if value is None or value == "":
        return None

    # بررسی نوع تگ از piexif
    try:
        info = piexif.TAGS.get(ifd_name, {}).get(tag_id, {})
        expected_type = info.get("type", None)
    except Exception:
        expected_type = None

    # ASCII (رشته)
    if expected_type == piexif.TYPES.Ascii:
        if isinstance(value, bytes):
            return value
        return str(value).encode("utf-8")

    # SHORT (عدد صحیح کوچک)
    if expected_type == piexif.TYPES.Short:
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return int(value)

    # LONG (عدد صحیح بزرگ)
    if expected_type == piexif.TYPES.Long:
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return int(value)

    # RATIONAL (کسری)
    if expected_type == piexif.TYPES.Rational:
        try:
            f = float(value)
            # تبدیل به کسر ساده (حداکثر ۴ رقم اعشار)
            num = int(f * 10000)
            den = 10000
            from math import gcd
            g = gcd(num, den)
            return (num // g, den // g)
        except (ValueError, TypeError):
            return (1, 1)

    # SRATIONAL (کسری علامت‌دار)
    if expected_type == piexif.TYPES.SRational:
        try:
            f = float(value)
            num = int(f * 10000)
            den = 10000
            from math import gcd
            g = gcd(abs(num), den)
            return (num // g, den // g)
        except (ValueError, TypeError):
            return (0, 1)

    # پیش‌فرض: string → bytes
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


def delete_tags(input_path: str, output_path: str, tags: list) -> str:
    """حذف تگ‌های مشخص"""
    changes = {t: None for t in tags}
    return edit_image_metadata(input_path, output_path, changes)