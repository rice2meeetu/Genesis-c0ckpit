"""CPU-only OpenPose document editing. No model, service or network dependencies."""
from __future__ import annotations

from copy import deepcopy
import math

PARTS = ("pose_keypoints_2d", "hand_left_keypoints_2d",
         "hand_right_keypoints_2d", "face_keypoints_2d")
BODY18 = [(1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),(9,10),
          (1,11),(11,12),(12,13),(1,0),(0,14),(14,16),(0,15),(15,17)]
BODY25 = [(1,2),(2,3),(3,4),(1,5),(5,6),(6,7),(1,8),(8,9),(9,10),
          (10,11),(8,12),(12,13),(13,14),(1,0),(0,15),(15,17),(0,16),
          (16,18),(14,19),(19,20),(14,21),(11,22),(22,23),(11,24)]
HAND = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),
        (9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),
        (0,17),(17,18),(18,19),(19,20)]


def validate_document(raw, dimensions=None):
    """Preserve unknown metadata; accept one standard OpenPose/DWPose frame."""
    if isinstance(raw, list):
        if len(raw) != 1:
            raise ValueError("Import one frame at a time, not a multi-frame sequence.")
        raw = raw[0]
    if not isinstance(raw, dict) or not isinstance(raw.get("people"), list):
        raise ValueError("Expected an OpenPose object with a people list.")
    doc = deepcopy(raw)
    dims = dimensions or (doc.get("canvas_width"), doc.get("canvas_height"))
    if any(isinstance(n, bool) or not isinstance(n, (int, float))
           or not math.isfinite(n) or int(n) != n or not 16 <= n <= 8192 for n in dims):
        raise ValueError("Canvas width and height must be whole numbers from 16 to 8192.")
    width, height = map(int, dims)
    if len(doc["people"]) > 32:
        raise ValueError("At most 32 people can be edited in one document.")
    for person in doc["people"]:
        if not isinstance(person, dict):
            raise ValueError("Each person must be an object.")
        for key in PARTS:
            values = person.get(key, [])
            if values is None:
                values = []
            if isinstance(values,list) and values and all(isinstance(v,list) and len(v)==3 for v in values):
                values = [n for triple in values for n in triple]
            if not isinstance(values, list) or len(values) % 3:
                raise ValueError(key + " must contain x, y, confidence triples.")
            count = len(values) // 3
            valid_counts = {0,18,25} if key == PARTS[0] else ({0,68,70} if key == PARTS[3] else {0,21})
            if count not in valid_counts:
                raise ValueError("Unsupported joint count for " + key + ": " + str(count))
            if any(isinstance(v, bool) or not isinstance(v, (int,float))
                   or not math.isfinite(v) for v in values):
                raise ValueError("Keypoints must contain finite numbers.")
            if any(not 0 <= c <= 1 for c in values[2::3]):
                raise ValueError("Keypoint confidence must be between zero and one.")
            values = list(values)
            visible = [(values[i],values[i+1]) for i in range(0,len(values),3) if values[i+2]>0]
            # controlnet_aux exports normalized coordinates and null absent parts.
            # Mark our pixel-space exports explicitly to avoid rescaling them twice.
            normalized = doc.get("genesis_coordinate_space") != "pixels" and bool(visible) and all(
                abs(x)<=1 and abs(y)<=1 for x,y in visible)
            if normalized:
                for i in range(0,len(values),3):
                    values[i] *= width
                    values[i+1] *= height
            person[key] = values
    doc["canvas_width"], doc["canvas_height"] = width, height
    doc.setdefault("version", 1.3)
    doc["genesis_coordinate_space"] = "pixels"
    return doc


def standing_person(width, height, index=0):
    xy = [(0.5,.14),(.5,.25),(.39,.26),(.33,.39),(.29,.51),(.61,.26),
          (.67,.39),(.71,.51),(.43,.52),(.42,.70),(.41,.89),
          (.57,.52),(.58,.70),(.59,.89),(.47,.12),(.53,.12),(.44,.14),(.56,.14)]
    offset = (.18 if index % 2 else -.18) if index else 0
    return {PARTS[0]: [v for x,y in xy for v in ((x+offset)*width,y*height,1.0)],
            PARTS[1]: [], PARTS[2]: [], PARTS[3]: []}


def new_document(width=768, height=1024):
    return validate_document({"people": [standing_person(width,height)],
                              "canvas_width": width, "canvas_height": height})


def merged_document(target, incoming):
    """Scale imported people into the existing canvas without altering either input."""
    target, incoming = validate_document(target), validate_document(incoming)
    sx = target["canvas_width"] / incoming["canvas_width"]
    sy = target["canvas_height"] / incoming["canvas_height"]
    for person in incoming["people"]:
        for key in PARTS:
            points = person[key]
            for i in range(0,len(points),3):
                points[i] *= sx
                points[i+1] *= sy
        target["people"].append(person)
    return validate_document(target)


def add_hands(person, width, height):
    """Add editable schematic hands at existing wrists; never replace imported hands."""
    for key, wrist, direction in [(PARTS[1],7,1),(PARTS[2],4,-1)]:
        body = person[PARTS[0]]
        if person[key] or len(body) < (wrist+1)*3 or body[wrist*3+2] <= 0:
            continue
        x,y = body[wrist*3:wrist*3+2]
        points = [x,y,1.0]
        for finger in range(5):
            for joint in range(1,5):
                px = x + direction * (finger-2) * width * .009
                py = y + joint * height * .009 + abs(finger-2) * height * .004
                points.extend([max(0,min(width,px)),max(0,min(height,py)),1.0])
        person[key] = points
