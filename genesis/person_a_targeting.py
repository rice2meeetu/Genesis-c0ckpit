"""Manual, image-bound Person A regions; no automatic identity inference."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


def image_snapshot(path):
    data = Path(path).read_bytes()
    with Image.open(BytesIO(data)) as image:
        rgb = ImageOps.exif_transpose(image).convert("RGB")
    return rgb, sha256(data).hexdigest()


@dataclass(frozen=True)
class FaceRegion:
    digest: str
    box: tuple[int, int, int, int]

    def checked_image(self, path):
        image, digest = image_snapshot(path)
        if digest != self.digest:
            raise ValueError("The reviewed image changed. Select Person A again.")
        x1, y1, x2, y2 = self.box
        if not (0 <= x1 < x2 <= image.width and 0 <= y1 < y2 <= image.height
                and x2 - x1 >= 32 and y2 - y1 >= 32):
            raise ValueError("Select a face area at least 32 pixels wide and high.")
        return image


def prepare_crops(target, source, regions, directory):
    if not isinstance(regions, tuple) or len(regions) != 2 or not all(isinstance(r, FaceRegion) for r in regions):
        raise ValueError("Review and confirm Person A in both images first.")
    target_region, source_region = regions
    target_image = target_region.checked_image(target)
    source_image = source_region.checked_image(source)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target_crop, source_crop = directory / "target.png", directory / "source.png"
    target_image.crop(target_region.box).save(target_crop)
    source_image.crop(source_region.box).save(source_crop)
    return target_crop, source_crop


def composite_crop(target, region, swapped_crop, output):
    image = region.checked_image(target)
    crop, _ = image_snapshot(swapped_crop)
    x1, y1, x2, y2 = region.box
    if crop.size != (x2 - x1, y2 - y1):
        raise ValueError("ReActor changed the crop size; refusing an unverified placement.")
    image.paste(crop, (x1, y1))
    image.save(output, format="PNG")
    return Path(output)


def choose_face_region(path, role):
    """Human confirms the face itself, not an ordering-dependent face index."""
    from PyQt6.QtCore import QPoint, QRect, Qt
    from PyQt6.QtGui import QImage, QPixmap
    from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QLabel,
                                QRubberBand, QVBoxLayout)

    original, digest = image_snapshot(path)
    preview = original.copy()
    preview.thumbnail((900, 650))
    data = preview.tobytes()
    pixmap = QPixmap.fromImage(QImage(data, preview.width, preview.height,
                                    preview.width * 3, QImage.Format.Format_RGB888).copy())
    dialog = QDialog()
    dialog.setWindowTitle("GENESIS · Confirm Person A · " + role)
    layout = QVBoxLayout(dialog)
    note = QLabel("Drag a box around Person A's face, with a little surrounding space.\n"
                  "Exclude every other face. Cancel if the identity is uncertain.")
    layout.addWidget(note)
    confirmation = QCheckBox("I confirm this box contains only Person A's face.")
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
    ok.setEnabled(False)

    class Selector(QLabel):
        def __init__(self):
            super().__init__()
            self.setPixmap(pixmap)
            self.setFixedSize(pixmap.size())
            self.origin = QPoint()
            self.selection = None
            self.band = QRubberBand(QRubberBand.Shape.Rectangle, self)

        def bounded(self, position):
            return QPoint(max(0, min(self.width() - 1, int(position.x()))),
                          max(0, min(self.height() - 1, int(position.y()))))

        def mousePressEvent(self, event):
            if event.button() != Qt.MouseButton.LeftButton:
                return
            confirmation.setChecked(False)
            self.selection = None
            self.origin = self.bounded(event.position())
            self.band.setGeometry(QRect(self.origin, self.origin))
            self.band.show()

        def mouseMoveEvent(self, event):
            if event.buttons() & Qt.MouseButton.LeftButton:
                self.band.setGeometry(QRect(self.origin, self.bounded(event.position())).normalized())

        def mouseReleaseEvent(self, event):
            if event.button() != Qt.MouseButton.LeftButton:
                return
            rect = QRect(self.origin, self.bounded(event.position())).normalized()
            sx, sy = original.width / self.width(), original.height / self.height()
            box = (int(rect.left() * sx), int(rect.top() * sy),
                   min(original.width, int((rect.right() + 1) * sx)),
                   min(original.height, int((rect.bottom() + 1) * sy)))
            self.selection = FaceRegion(digest, box) if box[2] - box[0] >= 32 and box[3] - box[1] >= 32 else None
            ok.setEnabled(bool(self.selection and confirmation.isChecked()))

    selector = Selector()
    layout.addWidget(selector)
    layout.addWidget(confirmation)
    layout.addWidget(buttons)
    confirmation.toggled.connect(lambda checked: ok.setEnabled(bool(checked and selector.selection)))
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return selector.selection
