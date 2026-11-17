"""Read the CWE snapshot: which weakness type each CVE belongs to.

CWE is a defect taxonomy, not a news taxonomy: it says "this is a command
injection", not "this story is a patch advisory". It is used here to confirm a
CVE is a weakness record and to give the assessment a precise, quotable type.

Refresh with tools/refresh_cwe.py; the file is data/cwe.json.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "cwe.json"


@lru_cache(maxsize=1)
def _payload() -> dict:
    if not PATH.exists():
        return {"generated": "", "source": "", "cves": {}}
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except ValueError:
        return {"generated": "", "source": "", "cves": {}}


def all_cves() -> dict[str, list[dict]]:
    return _payload().get("cves") or {}


def for_cve(cve: str) -> list[dict]:
    return list(all_cves().get(cve.upper()) or [])


def labels(cve: str) -> list[str]:
    """Short "CWE-78 OS Command Injection" strings for a UI chip."""
    out = []
    for entry in for_cve(cve):
        name = entry.get("name") or ""
        out.append(f"{entry.get('id', '')} {name}".strip())
    return out


# Coarse families for filtering. Ordered: the first matching family wins, so
# the list is sorted from "most specific exploit primitive" to "generic".
FAMILIES: tuple[tuple[str, str, set[int]], ...] = (
    ("RCE", "遠端執行", {77, 78, 94, 95, 96, 99, 1336, 917}),
    ("DESERIALIZE", "反序列化", {502, 915}),
    ("SQLI", "SQL 注入", {89}),
    ("XSS", "XSS", {79, 80, 83, 87}),
    ("AUTH", "認證繞過", {287, 288, 290, 306, 620, 640, 862, 863, 269, 284, 285, 732}),
    ("PATH", "路徑遍歷", {22, 23, 36, 434, 538}),
    ("SSRF", "SSRF", {918}),
    ("XXE", "XXE", {611}),
    ("MEMORY", "記憶體安全", {119, 120, 121, 122, 125, 190, 191, 416, 476, 787}),
    ("INPUT", "輸入驗證", {20, 116, 128, 444, 707, 754, 1287}),
    ("CRYPTO", "加密／憑證", {259, 295, 327, 330, 347, 798}),
    ("INFO", "資訊洩露", {200, 209, 532, 552}),
)


def family(cve: str) -> str:
    """Coarse family key for a CVE: one of FAMILIES keys, OTHER or UNKNOWN."""
    entries = for_cve(cve)
    if not entries:
        return "UNKNOWN"
    ids: set[int] = set()
    for entry in entries:
        raw = str(entry.get("id") or "")
        if raw.startswith("CWE-"):
            try:
                ids.add(int(raw[4:]))
            except ValueError:
                continue
    for key, _label, members in FAMILIES:
        if ids & members:
            return key
    return "OTHER"


def family_label(key: str) -> str:
    for name, label, _members in FAMILIES:
        if name == key:
            return label
    return {"OTHER": "其他弱點", "UNKNOWN": "未標示"}.get(key, key)


def meta() -> dict:
    payload = _payload()
    entries = payload.get("cves") or {}
    return {
        "generated": payload.get("generated", ""),
        "source": payload.get("source", ""),
        "cves": len(entries),
        "with_cwe": sum(1 for value in entries.values() if value),
    }


def reset() -> None:
    _payload.cache_clear()
