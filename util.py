from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import config

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def ensure_dirs() -> None:
    for d in (
        config.CORPUS,
        config.RAW,
        config.RAW_COURSE,
        config.RAW_SUBJECT,
        config.RAW_PROGRAM,
        config.RAW_INDEX,
    ):
        d.mkdir(parents=True, exist_ok=True)

def load_manifest() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not config.MANIFEST.exists():
        return out
    with config.MANIFEST.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("ok"):
                out[rec["url"]] = rec
    return out

def append_manifest(rec: dict) -> None:
    with config.MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")

def write_jsonl(path: Path, records: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)

def read_html(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")

def apps_path_allowed(url: str) -> bool:
    from urllib.parse import urlparse

    path = urlparse(url).path
    return not any(path.startswith(p) for p in config.APPS_ROBOTS_DISALLOW)

def cal_path_allowed(url: str) -> bool:
    from urllib.parse import urlparse

    path = urlparse(url).path
    return not any(path.startswith(p) for p in config.CAL_ROBOTS_DISALLOW)
