"""Create a review contact sheet without changing its source images."""
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter


def create_reference_sheet(images, output, *, cell_size=256, columns=4):
    images = list(images)
    if not images or cell_size < 1 or columns < 1:
        raise ValueError('Reference sheet needs images and a valid layout.')
    rows = (len(images) + columns - 1) // columns
    sheet = QImage(columns * cell_size, rows * cell_size, QImage.Format.Format_RGB32)
    if sheet.isNull():
        raise ValueError('Unable to allocate reference sheet.')
    sheet.fill(QColor('#14171c'))
    painter = QPainter(sheet)
    try:
        for index, path in enumerate(images):
            image = QImage(str(path))
            if image.isNull():
                raise ValueError('Candidate image cannot be read: ' + str(path))
            thumb = image.scaled(cell_size, cell_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (index % columns) * cell_size + (cell_size - thumb.width()) // 2
            y = (index // columns) * cell_size + (cell_size - thumb.height()) // 2
            painter.drawImage(x, y, thumb)
    finally:
        painter.end()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not sheet.save(str(output)):
        raise ValueError('Unable to save reference sheet.')
    return output
