#!/usr/bin/env python3

import sys
import time
import tkinter as tk
from pathlib import Path

import cv2
from PIL import Image, ImageTk


BG = "#050505"
GOLD = "#d4af37"
IVORY = "#f4ead5"


def cover(frame, width, height):
    """Fast OpenCV cover resize/crop."""
    h, w = frame.shape[:2]

    scale = max(width / max(1, w), height / max(1, h))

    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))

    frame = cv2.resize(
        frame,
        (nw, nh),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
    )

    x = max(0, (nw - width) // 2)
    y = max(0, (nh - height) // 2)

    return frame[y:y + height, x:x + width]


def read_loop(cap):
    ok, frame = cap.read()

    if not ok:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = cap.read()

    return frame if ok else None


def main():
    if len(sys.argv) < 2:
        return

    primary_path = Path(sys.argv[1])

    secondary_path = None
    if len(sys.argv) >= 3 and sys.argv[2]:
        candidate = Path(sys.argv[2])
        if candidate.is_file():
            secondary_path = candidate

    if not primary_path.is_file():
        return

    root = tk.Tk()
    root.overrideredirect(True)
    root.configure(bg=BG)
    root.attributes("-topmost", True)

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    width = min(820, max(680, int(screen_w * 0.52)))
    height = min(480, max(400, int(screen_h * 0.48)))

    left = max(0, (screen_w - width) // 2)
    top = max(0, (screen_h - height) // 2)

    root.geometry(f"{width}x{height}+{left}+{top}")

    canvas = tk.Canvas(
        root,
        width=width,
        height=height,
        bg=BG,
        highlightthickness=1,
        highlightbackground="#8a6d1d",
    )
    canvas.pack(fill="both", expand=True)

    primary = cv2.VideoCapture(str(primary_path))

    if not primary.isOpened():
        root.destroy()
        return

    secondary = None

    if secondary_path:
        test = cv2.VideoCapture(str(secondary_path))
        if test.isOpened():
            secondary = test
        else:
            test.release()

    fps = primary.get(cv2.CAP_PROP_FPS)

    if not fps or fps < 10 or fps > 60:
        fps = 24.0

    # Don't deliberately skip frames.
    # Cap redraw at 30 FPS — plenty for a startup splash.
    target_fps = min(30.0, max(24.0, fps))
    delay_ms = max(16, int(round(1000 / target_fps)))

    started = time.monotonic()

    image_item = canvas.create_image(
        0,
        0,
        anchor="nw",
    )

    x = width // 2
    y = int(height * 0.42)

    # Shadow + title are persistent canvas objects.
    canvas.create_text(
        x + 3,
        y + 3,
        text="GENESIS",
        anchor="center",
        fill="#000000",
        font=("DejaVu Sans", 52, "bold"),
    )

    canvas.create_text(
        x,
        y,
        text="GENESIS",
        anchor="center",
        fill=GOLD,
        font=("DejaVu Sans", 52, "bold"),
    )

    canvas.create_text(
        x,
        y + 58,
        text="COCKPIT",
        anchor="center",
        fill=IVORY,
        font=("DejaVu Sans", 25, "bold"),
    )

    canvas.create_text(
        x,
        y + 100,
        text="Keep walking, Allan.",
        anchor="center",
        fill="#d8c49a",
        font=("Z003", 21, "italic"),
    )

    canvas.create_text(
        width - 26,
        height - 20,
        text="LOADING GENESIS",
        anchor="e",
        fill="#8d826e",
        font=("DejaVu Sans", 8, "bold"),
    )

    progress = canvas.create_rectangle(
        0,
        height - 4,
        1,
        height,
        fill=GOLD,
        outline="",
    )

    running = True

    def close(_event=None):
        nonlocal running
        running = False

        try:
            primary.release()
        except Exception:
            pass

        if secondary is not None:
            try:
                secondary.release()
            except Exception:
                pass

        try:
            root.destroy()
        except Exception:
            pass

    root.bind("<Escape>", close)
    root.bind("<Button-1>", close)

    def tick():
        nonlocal running

        if not running:
            return

        frame1 = read_loop(primary)

        if frame1 is None:
            close()
            return

        if secondary is not None:
            frame2 = read_loop(secondary)

            if frame2 is not None:
                half = width // 2

                left_frame = cover(
                    frame1,
                    half,
                    height,
                )

                right_frame = cover(
                    frame2,
                    width - half,
                    height,
                )

                composed = cv2.hconcat(
                    [left_frame, right_frame]
                )
            else:
                composed = cover(
                    frame1,
                    width,
                    height,
                )
        else:
            composed = cover(
                frame1,
                width,
                height,
            )

        # Slight cinematic darkening, much cheaper than repeatedly
        # constructing and blending large PIL backgrounds.
        composed = cv2.convertScaleAbs(
            composed,
            alpha=0.72,
            beta=0,
        )

        rgb = cv2.cvtColor(
            composed,
            cv2.COLOR_BGR2RGB,
        )

        image = Image.fromarray(rgb)

        tk_image = ImageTk.PhotoImage(image)

        canvas.itemconfigure(
            image_item,
            image=tk_image,
        )

        # Keep reference alive.
        canvas._splash_image = tk_image

        # Keep image behind title objects.
        canvas.tag_lower(image_item)

        elapsed = time.monotonic() - started

        # Slowly approach full width rather than ending the splash itself.
        amount = min(
            0.96,
            elapsed / 5.0,
        )

        canvas.coords(
            progress,
            0,
            height - 4,
            int(width * amount),
            height,
        )

        root.after(
            delay_ms,
            tick,
        )

    tick()

    try:
        root.mainloop()
    finally:
        try:
            primary.release()
        except Exception:
            pass

        if secondary is not None:
            try:
                secondary.release()
            except Exception:
                pass


if __name__ == "__main__":
    main()
