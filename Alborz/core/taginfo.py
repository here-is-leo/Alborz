"""
توضیحات کامل تگ‌های متادیتا
"""

TAG_DESCRIPTIONS = {
    # EXIF - 0th IFD
    "Make": "سازنده دستگاه (مثلاً Canon, NIKON, Apple)",
    "Model": "مدل دقیق دستگاه عکاسی",
    "Orientation": "جهت عکس (افقی، عمودی، چرخیده)",
    "XResolution": "رزولوشن افقی (نقطه در اینچ)",
    "YResolution": "رزولوشن عمودی (نقطه در اینچ)",
    "ResolutionUnit": "واحد رزولوشن (اینچ یا سانتی‌متر)",
    "Software": "نرم‌افزار ویرایش یا ذخیره‌کننده",
    "DateTime": "آخرین زمان تغییر فایل",
    "YCbCrPositioning": "موقعیت نمونه‌های رنگ",
    "ImageDescription": "توضیحات تصویر",
    "Artist": "نام عکاس یا خالق",
    "Copyright": "اطلاعات کپی‌رایت",
    "ExifOffset": "آفست به Exif IFD",

    # ExifIFD
    "DateTimeOriginal": "🕐 زمان اصلی ثبت عکس (مهم‌ترین تگ)",
    "DateTimeDigitized": "زمان تبدیل به فرمت دیجیتال",
    "ExposureTime": "⏱️ زمان نوردهی (سرعت شاتر)",
    "FNumber": "🔆 عدد دیافراگم (f-stop)",
    "ApertureValue": "مقدار دیافراگم",
    "ShutterSpeedValue": "مقدار سرعت شاتر",
    "ISOSpeedRatings": "📊 حساسیت ISO",
    "ExposureProgram": "حالت نوردهی (دستی، خودکار، ...)",
    "ExposureMode": "حالت نوردهی (خودکار/دستی)",
    "ExposureBiasValue": "جبران نوردهی (EV)",
    "MeteringMode": "حالت اندازه‌گیری نور",
    "Flash": "وضعیت فلاش",
    "FocalLength": "📏 فاصله کانونی لنز (میلی‌متر)",
    "FocalLengthIn35mmFilm": "فاصله کانونی معادل ۳۵ میلی‌متر",
    "LensModel": "🔍 مدل لنز استفاده‌شده",
    "LensMake": "سازنده لنز",
    "LensSerialNumber": "⚠️ شماره سریال لنز (حساس)",
    "BodySerialNumber": "⚠️ شماره سریال بدنه دوربین (حساس)",
    "ColorSpace": "فضای رنگی (sRGB, Adobe RGB)",
    "WhiteBalance": "تعادل رنگ سفید",
    "SceneCaptureType": "نوع صحنه (استاندارد، پرتره، منظره)",
    "CustomRendered": "پردازش سفارشی",
    "DigitalZoomRatio": "نسبت زوم دیجیتال",
    "SubjectDistanceRange": "محدوده فاصله سوژه",
    "UserComment": "💬 نظر کاربر (می‌تواند حاوی اطلاعات شخصی باشد)",
    "ImageUniqueID": "⚠️ شناسه یکتای تصویر",
    "MakerNote": "🔒 یادداشت‌های اختصاصی سازنده (حجم بالا)",

    # GPS
    "GPSVersionID": "نسخه GPS",
    "GPSLatitude": "عرض جغرافیایی (DMS)",
    "GPSLongitude": "طول جغرافیایی (DMS)",
    "GPSLatitudeRef": "مرجع عرض (N/S)",
    "GPSLongitudeRef": "مرجع طول (E/W)",
    "DecimalLatitude": "⚠️ عرض جغرافیایی اعشاری",
    "DecimalLongitude": "⚠️ طول جغرافیایی اعشاری",
    "GPSAltitude": "ارتفاع از سطح دریا",
    "GPSAltitudeRef": "مرجع ارتفاع",
    "GPSTimeStamp": "زمان UTC ثبت GPS",
    "GPSDateStamp": "تاریخ UTC ثبت GPS",
    "GPSSatellites": "تعداد ماهواره‌های قفل‌شده",
    "GPSMapDatum": "سیستم مرجع نقشه (معمولاً WGS-84)",
    "GPSImgDirection": "جهت دوربین",
    "GPSImgDirectionRef": "مرجع جهت",
    "GPSProcessingMethod": "روش تعیین موقعیت",
    "GPSSpeed": "سرعت حرکت",
    "GPSTrack": "مسیر حرکت",

    # XMP
    "Rating": "امتیاز عکس (۱-۵ ستاره)",
    "Label": "برچسب (رنگی)",
    "Creator": "خالق",
    "CreatorTool": "ابزار ساخت",
    "CreateDate": "زمان ایجاد",
    "ModifyDate": "زمان تغییر",
    "MetadataDate": "زمان تغییر متادیتا",

    # Audio (ID3)
    "Title": "عنوان آهنگ",
    "Album": "آلبوم",
    "Artist_Audio": "خواننده",
    "AlbumArtist": "خواننده آلبوم",
    "Genre": "ژانر",
    "TrackNumber": "شماره ترک",
    "Year": "سال انتشار",
    "Comment": "توضیحات",

    # Video
    "creation_time": "زمان ساخت ویدیو",
    "duration": "مدت زمان (ثانیه)",
    "bit_rate": "نرخ بیت",
    "width": "عرض",
    "height": "ارتفاع",
    "codec_name": "نام کدک",
    "nb_frames": "تعداد فریم",
    "r_frame_rate": "نرخ فریم",
    "com.apple.quicktime.make": "سازنده (اپل)",
    "com.apple.quicktime.model": "مدل دستگاه (اپل)",
    "com.apple.quicktime.software": "نسخه iOS",
    "com.apple.quicktime.location.ISO6709": "⚠️ موقعیت GPS",
}


# دسته‌بندی تگ‌ها
TAG_CATEGORIES = {
    "camera": ["Make", "Model", "LensModel", "LensMake", "BodySerialNumber",
               "LensSerialNumber", "FocalLength", "MaxApertureValue"],
    "exposure": ["ExposureTime", "FNumber", "ApertureValue", "ISOSpeedRatings",
                 "ExposureProgram", "ExposureMode", "ExposureBiasValue",
                 "MeteringMode", "Flash", "ShutterSpeedValue"],
    "time": ["DateTimeOriginal", "DateTimeDigitized", "DateTime", "CreateDate",
             "ModifyDate", "GPSTimeStamp", "creation_time"],
    "location": ["DecimalLatitude", "DecimalLongitude", "GPSAltitude",
                 "GPSLatitude", "GPSLongitude", "GPSMapDatum"],
    "author": ["Artist", "Copyright", "Creator", "UserComment", "ImageDescription"],
    "privacy_sensitive": [
        "DecimalLatitude", "DecimalLongitude", "GPSAltitude",
        "LensSerialNumber", "BodySerialNumber", "ImageUniqueID",
        "UserComment", "Artist", "Copyright",
    ],
    "technical": ["Orientation", "XResolution", "YResolution", "ResolutionUnit",
                  "ColorSpace", "WhiteBalance", "YCbCrPositioning"],
}


def get_tag_info(tag_name: str) -> dict:
    """اطلاعات یک تگ رو برمی‌گردونه"""
    # جستجوی مستقیم
    desc = TAG_DESCRIPTIONS.get(tag_name)

    # جستجو با حذف پیشوند (EXIF, Image و...)
    if not desc:
        clean = tag_name.split()[-1] if " " in tag_name else tag_name
        desc = TAG_DESCRIPTIONS.get(clean)

    # جستجو case-insensitive
    if not desc:
        lower = tag_name.lower()
        for k, v in TAG_DESCRIPTIONS.items():
            if k.lower() == lower:
                desc = v
                break

    # دسته‌بندی
    categories = []
    for cat, tags in TAG_CATEGORIES.items():
        if tag_name in tags:
            categories.append(cat)

    # آیا حساس است؟
    is_sensitive = tag_name in TAG_CATEGORIES["privacy_sensitive"]

    return {
        "tag": tag_name,
        "description": desc or "توضیحی موجود نیست",
        "categories": categories,
        "is_sensitive": is_sensitive,
    }