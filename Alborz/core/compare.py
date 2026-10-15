"""
مقایسه متادیتای دو فایل
"""
from typing import Dict, List

from .models import MetadataResult
from .formatters import dedup_entries, humanize_value, get_dedup_key


def compare_results(a: MetadataResult, b: MetadataResult) -> dict:
    """
    مقایسه دو MetadataResult و برگرداندن diff

    Returns:
        {
          "file_a": "...",
          "file_b": "...",
          "only_in_a": [...],   # تگ‌هایی که فقط در A هستن
          "only_in_b": [...],   # تگ‌هایی که فقط در B هستن
          "changed": [...],     # تگ‌هایی که مقدارشون فرق داره
          "same": [...],        # تگ‌های یکسان
          "stats": {...},
        }
    """
    a_entries = {get_dedup_key(e): e for e in dedup_entries(a.entries)}
    b_entries = {get_dedup_key(e): e for e in dedup_entries(b.entries)}

    only_in_a = []
    only_in_b = []
    changed = []
    same = []

    all_keys = set(a_entries.keys()) | set(b_entries.keys())

    for k in sorted(all_keys):
        ea = a_entries.get(k)
        eb = b_entries.get(k)

        if ea and not eb:
            only_in_a.append(_entry_to_dict(ea))
        elif eb and not ea:
            only_in_b.append(_entry_to_dict(eb))
        else:
            va = str(humanize_value(ea.tag, ea.value)).strip()
            vb = str(humanize_value(eb.tag, eb.value)).strip()
            if va == vb:
                same.append({
                    "tag": ea.tag,
                    "group": ea.group,
                    "value": va,
                })
            else:
                changed.append({
                    "tag": ea.tag,
                    "group_a": ea.group,
                    "group_b": eb.group,
                    "value_a": va,
                    "value_b": vb,
                })

    return {
        "file_a": {
            "name": a.filename,
            "size": a.filesize,
            "md5": a.file_hash_md5,
            "count": len(a_entries),
        },
        "file_b": {
            "name": b.filename,
            "size": b.filesize,
            "md5": b.file_hash_md5,
            "count": len(b_entries),
        },
        "only_in_a": only_in_a,
        "only_in_b": only_in_b,
        "changed": changed,
        "same": same,
        "stats": {
            "only_in_a": len(only_in_a),
            "only_in_b": len(only_in_b),
            "changed": len(changed),
            "same": len(same),
            "total_diff": len(only_in_a) + len(only_in_b) + len(changed),
        },
    }


def _entry_to_dict(e) -> dict:
    return {
        "tag": e.tag,
        "group": e.group,
        "value": str(humanize_value(e.tag, e.value)),
    }