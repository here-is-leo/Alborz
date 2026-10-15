"""
کارهای مرتبط با GPS
"""
import requests
from functools import lru_cache
from typing import Optional, Dict


@lru_cache(maxsize=256)
def reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, str]]:
    """
    تبدیل مختصات به نام مکان (شهر، کشور) با Nominatim (OpenStreetMap)
    بدون نیاز به API key. محدودیت: ۱ درخواست در ثانیه.
    """
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "accept-language": "fa,en",
            "zoom": 10,
        }
        headers = {
            "User-Agent": "Alborz/1.0 (metadata extractor)",
        }
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        addr = data.get("address", {})

        # انتخاب بهترین نام
        city = (addr.get("city") or addr.get("town") or
                addr.get("village") or addr.get("county") or "")
        country = addr.get("country", "")
        state = addr.get("state", "")

        result = {
            "display_name": data.get("display_name", ""),
            "city": city,
            "state": state,
            "country": country,
            "country_code": addr.get("country_code", "").upper(),
        }
        return result
    except Exception:
        return None


def extract_gps_from_entries(entries) -> Optional[Dict[str, float]]:
    """
    استخراج مختصات GPS از لیست entries
    """
    lat = None
    lon = None
    alt = None

    for e in entries:
        tag = e.tag.lower()
        if tag == "decimallatitude":
            try:
                lat = float(e.value)
            except (ValueError, TypeError):
                pass
        elif tag == "decimallongitude":
            try:
                lon = float(e.value)
            except (ValueError, TypeError):
                pass
        elif tag in ("gpsaltitude", "altitude"):
            try:
                alt = float(e.value)
            except (ValueError, TypeError):
                pass

    if lat is None or lon is None:
        return None
    if lat == 0 and lon == 0:
        return None

    return {"lat": lat, "lon": lon, "alt": alt}