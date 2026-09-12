"""Local persistent character/reference profiles for GENESIS.

Profiles reference existing images in place; GENESIS does not copy or alter source files.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

CHARACTER_ROOT = Path.home() / ".local/share/genesis-cockpit/characters"
INDEX_PATH = CHARACTER_ROOT / "characters.json"

def _safe_id(name: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
    return stem or f"character-{int(time.time())}"

def load_characters(path: Path = INDEX_PATH) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    rows = data.get("characters", []) if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict) and row.get("id") and row.get("primary_image")]

def save_character(name: str, primary_image: str, *, adult_confirmed: bool, path: Path = INDEX_PATH) -> dict:
    if not adult_confirmed:
        raise ValueError("Character must be explicitly confirmed as an adult (18+).")
    source = Path(primary_image).expanduser().resolve()
    if not source.is_file():
        raise ValueError("Primary character image does not exist.")
    clean_name = name.strip() or source.stem
    rows = load_characters(path)
    base = _safe_id(clean_name)
    existing = {row["id"] for row in rows}
    cid = base
    n = 2
    while cid in existing:
        cid = f"{base}-{n}"; n += 1
    row = {
        "id": cid, "name": clean_name, "adult_confirmed": True,
        "primary_image": str(source), "references": [str(source)],
        "created": int(time.time()),
    }
    rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "characters": rows}, indent=2), encoding="utf-8")
    return row

def add_reference(character_id: str, image: str, *, role: str = "anchor", path: Path = INDEX_PATH) -> dict:
    source = Path(image).expanduser().resolve()
    if not source.is_file():
        raise ValueError("Character reference image does not exist.")
    rows = load_characters(path)
    for row in rows:
        if row["id"] != character_id:
            continue
        refs = row.setdefault("references", [])
        value = str(source)
        if value not in refs:
            refs.append(value)
        roles = row.setdefault("reference_roles", {})
        roles[value] = role.strip() or "anchor"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 1, "characters": rows}, indent=2), encoding="utf-8")
        return row
    raise ValueError("Saved character was not found.")

def get_character(character_id: str, path: Path = INDEX_PATH) -> dict | None:
    return next((row for row in load_characters(path) if row["id"] == character_id), None)

def preferred_reference(character_id: str, role: str = "", path: Path = INDEX_PATH) -> str:
    row = get_character(character_id, path)
    if not row:
        return ""
    refs = [ref for ref in row.get("references", []) if Path(ref).is_file()]
    roles = row.get("reference_roles", {})
    wanted = role.strip().lower()
    if wanted:
        for ref in refs:
            if str(roles.get(ref, "")).lower() == wanted:
                return ref
    primary = row.get("primary_image", "")
    return primary if primary and Path(primary).is_file() else (refs[0] if refs else "")

def character_items(path: Path = INDEX_PATH) -> list[dict]:
    return [{
        "id": row["id"], "name": row.get("name", row["id"]),
        "primaryImage": Path(row["primary_image"]).as_uri(),
        "primaryPath": row["primary_image"],
        "referenceCount": len(row.get("references", [])),
        "references": [Path(ref).as_uri() for ref in row.get("references", []) if Path(ref).is_file()],
        "referenceItems": [{
            "source": Path(ref).as_uri(),
            "path": ref,
            "role": row.get("reference_roles", {}).get(ref, "primary" if ref == row.get("primary_image") else "anchor"),
        } for ref in row.get("references", []) if Path(ref).is_file()],
    } for row in load_characters(path)]
