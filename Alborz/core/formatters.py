import json
from .models import MetadataResult


# ---------- ترجمه مقادیر عددی به متن خوانا ----------
EXIF_TRANSLATIONS = {
    "Orientation": {
        1: "افقی (نرمال)", 2: "افقی (آینه‌ای)", 3: "چرخیده ۱۸۰°",
        4: "عمودی (آینه‌ای)", 5: "افقی چرخیده ۹۰° CCW",
        6: "عمودی چرخیده ۹۰° CW", 7: "عمودی چرخیده ۹۰° CCW",
        8: "عمودی چرخیده ۹۰° CW",
    },
    "Flash": {
        0: "بدون فلاش", 1: "فلاش زده شد", 5: "فلاش زده شد (بدون بازتاب)",
        7: "فلاش زده شد (با بازتاب)", 9: "فلاش زده شد (اجباری)",
        16: "بدون فلاش (اجباری)", 24: "بدون فلاش (خودکار)",
        25: "فلاش زده شد (خودکار)",
    },
    "ExposureProgram": {
        0: "تعریف‌نشده", 1: "دستی", 2: "برنامه عادی", 3: "اولویت دیافراگم",
        4: "اولویت شاتر", 5: "خلاقانه", 6: "ورزشی", 7: "منظره", 8: "پرتره",
    },
    "ExposureMode": {
        0: "خودکار", 1: "دستی", 2: "براکت خودکار",
    },
    "MeteringMode": {
        0: "نامشخص", 1: "میانگین", 2: "میانگین وزن‌دار مرکزی",
        3: "نقطه‌ای", 4: "چندنقطه‌ای", 5: "الگویی", 6: "جزئی",
    },
    "WhiteBalance": {
        0: "خودکار", 1: "دستی",
    },
    "ColorSpace": {
        1: "sRGB", 65535: "Adobe RGB",
    },
    "SceneCaptureType": {
        0: "استاندارد", 1: "منظره", 2: "پرتره", 3: "شبانه",
    },
    "CustomRendered": {
        0: "عادی", 1: "سفارشی",
    },
    "ResolutionUnit": {
        1: "بدون واحد", 2: "اینچ", 3: "سانتی‌متر",
    },
    "YCbCrPositioning": {
        1: "مرکزی", 2: "هم‌مکان",
    },
}


def humanize_value(tag: str, value):
    """مقدار خام رو به متن خوانا تبدیل می‌کنه"""
    clean_tag = tag.split()[-1] if " " in tag else tag
    table = EXIF_TRANSLATIONS.get(clean_tag)
    if table:
        try:
            key = int(float(value))
            if key in table:
                return f"{table[key]} ({value})"
        except (ValueError, TypeError):
            pass
    return value


# ---------- Dedup هوشمند ----------

# نگاشت نام‌های مختلف به یک نام یکتا
TAG_ALIASES = {
    "exifimagelength": "exifimageheight",
    "imagelength": "exifimageheight",
    "imagewidth": "exifimagewidth",
    "exifinteroperabilityoffset": "interoperabilityoffset",
    "imageexifoffset": "exifoffset",
    "imagegpsinfo": "gpsinfo",
    "imageorientation": "orientation",
    "imagemake": "make",
    "imagemodel": "model",
    "imagesoftware": "software",
    "imagedatetime": "datetime",
    "imagexresolution": "xresolution",
    "imageyresolution": "yresolution",
    "imageresolutionunit": "resolutionunit",
    "imageycbcrpositioning": "ycbcrpositioning",
    "gpsgpsversionid": "gpsversionid",
    "exifdatetimeoriginal": "datetimeoriginal",
    "exifdatetimedigitized": "datetimedigitized",
    "exifexposuretime": "exposuretime",
    "exiffnumber": "fnumber",
    "exifexposureprogram": "exposureprogram",
    "exifisospeedratings": "isospeedratings",
    "exifexifversion": "exifversion",
    "exifcomponentsconfiguration": "componentsconfiguration",
    "exifshutterspeedvalue": "shutterspeedvalue",
    "exifaperturevalue": "aperturevalue",
    "exifexposurebiasvalue": "exposurebiasvalue",
    "exifmeteringmode": "meteringmode",
    "exifflash": "flash",
    "exiffocallength": "focallength",
    "exifusercomment": "usercomment",
    "exifsubsectime": "subsectime",
    "exifsubsectimeoriginal": "subsectimeoriginal",
    "exifsubsectimedigitized": "subsectimedigitized",
    "exifflashpixversion": "flashpixversion",
    "exifcolorspace": "colorspace",
    "exifexifimagewidth": "exifimagewidth",
    "exifexifimagelength": "exifimageheight",
    "exiffocalplanexresolution": "focalplanexresolution",
    "exiffocalplaneyresolution": "focalplaneyresolution",
    "exiffocalplaneresolutionunit": "focalplaneresolutionunit",
    "exifcustomrendered": "customrendered",
    "exifexposuremode": "exposuremode",
    "exifwhitebalance": "whitebalance",
    "exifscenecapturetype": "scenecapturetype",
    "interoperabilityinteroperabilityindex": "interoperabilityindex",
    "interoperabilityinteroperabilityversion": "interoperabilityversion",
}


def get_dedup_key(entry) -> str:
    """کلید نرمال برای تشخیص تگ‌های تکراری"""
    t = entry.tag.strip()
    for prefix in ("EXIF ", "Image ", "GPS ", "Interoperability ", "MakerNote "):
        if t.startswith(prefix):
            t = t[len(prefix):]
            break
    key = t.lower().replace(" ", "").replace("-", "").replace("_", "")
    return TAG_ALIASES.get(key, key)


def dedup_entries(entries):
    """حذف تگ‌های تکراری با اولویت گروه‌های معتبرتر"""
    priority = {
        "EXIF": 0, "ExifIFD": 1, "GPS": 2,
        "VideoFormat": 1, "QuickTime": 1,
        "Audio": 1, "AudioTag": 2,
        "ExifRead": 99,
        "Error": 200, "Warning": 200,
    }

    seen = {}
    for e in entries:
        key = get_dedup_key(e)
        if key not in seen:
            seen[key] = e
        else:
            old = seen[key]
            if priority.get(e.group, 50) < priority.get(old.group, 50):
                seen[key] = e

    return sorted(
        seen.values(),
        key=lambda x: (priority.get(x.group, 50), x.tag),
    )


# ---------- JSON ----------

def to_json(result: MetadataResult, indent: int = 2) -> str:
    deduped = dedup_entries(result.entries)
    data = result.to_dict()
    data["entries"] = [
        {
            "group": e.group,
            "tag": e.tag,
            "value": humanize_value(e.tag, e.value),
            "description": e.description,
        }
        for e in deduped
    ]
    return json.dumps(data, ensure_ascii=False, indent=indent, default=str)


# ---------- CSV ----------

def to_csv(result: MetadataResult) -> str:
    deduped = dedup_entries(result.entries)
    lines = ["group,tag,value"]
    for e in deduped:
        v = str(humanize_value(e.tag, e.value)).replace('"', '""')
        lines.append(f'{e.group},"{e.tag}","{v}"')
    return "\n".join(lines)


# ---------- HTML ----------

def to_html(result: MetadataResult) -> str:
    deduped = dedup_entries(result.entries)
    rows = "".join(
        f"<tr><td>{e.group}</td><td>{e.tag}</td>"
        f"<td>{humanize_value(e.tag, e.value)}</td></tr>"
        for e in deduped
    )
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<title>متادیتا {result.filename}</title>
<style>
body{{font-family:Tahoma;background:#111;color:#eee;padding:20px}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px;border:1px solid #333;text-align:right}}
th{{background:#222}}tr:nth-child(even){{background:#1a1a1a}}
h1{{color:#7dd3fc}}
</style></head><body>
<h1>متادیتای {result.filename}</h1>
<p>حجم: {result.filesize} بایت | MIME: {result.mime_type}</p>
<p>MD5: {result.file_hash_md5}</p>
<p>SHA256: {result.file_hash_sha256}</p>
<table><thead><tr><th>گروه</th><th>تگ</th><th>مقدار</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""