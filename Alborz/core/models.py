from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime

@dataclass
class MetadataEntry:
    group: str          # EXIF, GPS, QuickTime, Audio, File, ...
    tag: str            # نام تگ
    value: Any          # مقدار
    description: str = ""

@dataclass
class MetadataResult:
    filename: str
    filesize: int
    mime_type: str
    file_hash_md5: str = ""
    file_hash_sha256: str = ""
    entries: List[MetadataEntry] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": {
                "name": self.filename,
                "size": self.filesize,
                "mime": self.mime_type,
                "md5": self.file_hash_md5,
                "sha256": self.file_hash_sha256,
            },
            "entries": [
                {"group": e.group, "tag": e.tag, "value": e.value,
                 "description": e.description}
                for e in self.entries
            ],
            "errors": self.errors,
        }

    def get(self, tag: str):
        for e in self.entries:
            if e.tag.lower() == tag.lower():
                return e.value
        return None