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

def add_reference(character_id: str, image: str, *, role: str = "anchor", category: str = "", approved: bool = False, path: Path = INDEX_PATH) -> dict:
    if category and category not in {"face", "body", "pose", "ignore"}:
        raise ValueError("Choose face, body, pose or ignore.")
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
            # Newly imported images require review even when a category was
            # not specified. Leave legacy references' existing flags alone.
            row.setdefault("reference_approved", {})[value] = bool(approved)
        roles = row.setdefault("reference_roles", {})
        roles[value] = role.strip() or "anchor"
        if category:
            row.setdefault("reference_categories", {})[value] = category
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
    refs = [ref for ref in row.get("references", []) if Path(ref).is_file() and reference_is_approved(row, ref)]
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
        "referenceSheets": [Path(sheet).as_uri() for sheet in row.get("reference_sheets", []) if Path(sheet).is_file()],
        "referenceCount": len(row.get("references", [])),
        "references": [Path(ref).as_uri() for ref in row.get("references", []) if Path(ref).is_file()],
        "referenceItems": [{
            "source": Path(ref).as_uri(),
            "path": ref,
            "approved": reference_is_approved(row, ref),
            "category": reference_category(row, ref),
            "master": ref == row.get("primary_image"),
            "role": row.get("reference_roles", {}).get(ref, "primary" if ref == row.get("primary_image") else "anchor"),
        } for ref in row.get("references", []) if Path(ref).is_file()],
    } for row in load_characters(path)]


REFERENCE_ANGLES = ("Primary/Front", "¾ Left", "¾ Right", "Profile", "Back", "Upper Body", "Full Body")

def update_reference(character_id: str, old_image: str, new_image: str = "", *, role: str = "", confirm_master: bool = False, path: Path = INDEX_PATH) -> dict:
    """Replace/delete a library link only; never modify either image file."""
    rows = load_characters(path)
    row = next((r for r in rows if r["id"] == character_id), None)
    if row is None:
        raise ValueError("Saved character was not found.")
    old = str(Path(old_image).expanduser().resolve())
    refs = row.get("references", [])
    if old not in refs:
        raise ValueError("Reference was not found.")
    new = str(Path(new_image).expanduser().resolve()) if new_image else ""
    if new and not Path(new).is_file():
        raise ValueError("Replacement reference does not exist.")
    if old == row["primary_image"] and not new:
        raise ValueError("Replace the primary reference before removing it.")
    if old == row["primary_image"] and new != old and not confirm_master:
        raise ValueError("Replacing the identity master requires explicit confirmation.")
    if new and new != old and new in refs:
        raise ValueError("That reference is already stored.")
    index = refs.index(old)
    roles = row.setdefault("reference_roles", {})
    previous_role = roles.pop(old, "Primary/Front" if old == row["primary_image"] else "anchor")
    for key in ("reference_categories", "reference_approved"):
        metadata = row.get(key, {})
        if old in metadata:
            value = metadata.pop(old)
            if new:
                metadata[new] = (False if key == "reference_approved" and new != old else value)
    if new and new != old and old != row["primary_image"]:
        # An approved old photo is not proof that its replacement is approved.
        row.setdefault("reference_approved", {})[new] = False
    if new:
        refs[index] = new
        roles[new] = role.strip() or previous_role
    else:
        refs.pop(index)
    if old == row["primary_image"]:
        row["primary_image"] = new
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "characters": rows}, indent=2), encoding="utf-8")
    return row


def reference_category(row: dict, image: str) -> str:
    if image == row.get("primary_image"):
        return "face"
    category = row.get("reference_categories", {}).get(image)
    if category in {"face", "body", "pose", "ignore"}:
        return category
    role = str(row.get("reference_roles", {}).get(image, "")).lower()
    if role == "ignore":
        return "ignore"
    if role in {"pose", "pose reference"}:
        return "pose"
    if "body" in role or role in {"back", "back view"}:
        return "body"
    return "face"


def reference_is_approved(row: dict, image: str) -> bool:
    # Legacy references remain usable; new candidates require explicit approval.
    return image == row.get("primary_image") or (
        row.get("reference_approved", {}).get(image, True)
        and reference_category(row, image) != "ignore")


def set_reference_details(character_id: str, image: str, category: str, approved: bool, *, path: Path = INDEX_PATH) -> dict:
    if category not in {"face", "body", "pose", "ignore"}:
        raise ValueError("Choose face, body, pose or ignore.")
    rows = load_characters(path)
    row = next((r for r in rows if r["id"] == character_id), None)
    image = str(Path(image).expanduser().resolve())
    if row is None or image not in row.get("references", []):
        raise ValueError("Saved character reference was not found.")
    if image == row["primary_image"] and (not approved or category != "face"):
        raise ValueError("Master identity must remain an approved face reference.")
    row.setdefault("reference_categories", {})[image] = category
    row.setdefault("reference_approved", {})[image] = bool(approved)
    path.write_text(json.dumps({"version": 1, "characters": rows}, indent=2), encoding="utf-8")
    return row


REFERENCE_BUILD_REQUESTS = (
    ("Primary/Front", "face", "Same adult character as the source, front-facing portrait, neutral expression, plain background, preserve facial identity."),
    ("¾ Left", "face", "Same adult character as the source, three-quarter left portrait, preserve facial identity, plain background."),
    ("¾ Right", "face", "Same adult character as the source, three-quarter right portrait, preserve facial identity, plain background."),
    ("Profile", "face", "Same adult character as the source, side-profile portrait, preserve facial identity, plain background."),
    ("Back", "body", "Same adult character as the source, full-body back view, neutral upright stance, preserve body proportions and identity."),
    ("Upper Body", "body", "Same adult character as the source, upper-body reference, neutral upright stance, preserve identity and body proportions."),
    ("Full Body", "body", "Same adult character as the source, full-body reference, neutral upright stance, preserve identity and body proportions."),
)


def best_reference(character_id: str, instruction: str, path: Path = INDEX_PATH) -> str:
    """Match explicit angle phrases to approved references; otherwise keep master."""
    row = get_character(character_id, path)
    if not row:
        return ""
    def canonical(value):
        value = value.lower().replace("¾", "three-quarter").replace("3/4", "three-quarter")
        return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())
    text = canonical(instruction)
    aliases = {
        "three quarter left": ("three quarter left", "left three quarter"),
        "three quarter right": ("three quarter right", "right three quarter"),
        "profile": ("profile", "side view"),
        "full body": ("full body",), "upper body": ("upper body",),
        "primary front": ("front view", "front facing"),
        "back": ("back view", "back facing"),
    }
    for angle, phrases in aliases.items():
        if not any(" " + phrase + " " in " " + text + " " for phrase in phrases):
            continue
        for image in row.get("references", []):
            if reference_is_approved(row, image) and reference_category(row, image) not in {"pose", "ignore"} and Path(image).is_file():
                role = canonical(row.get("reference_roles", {}).get(image, ""))
                if role == angle or role in phrases:
                    return image
    return preferred_reference(character_id, path=path)


def save_reference_sheet(character_id: str, sheet: str, *, path: Path = INDEX_PATH):
    rows = load_characters(path)
    row = next((r for r in rows if r['id'] == character_id), None)
    sheet = str(Path(sheet).resolve())
    if row is None or not Path(sheet).is_file():
        raise ValueError('Character or reference sheet is unavailable.')
    row.setdefault('reference_sheets', []).append(sheet)
    path.write_text(json.dumps({'version': 1, 'characters': rows}, indent=2), encoding='utf-8')
    return row
