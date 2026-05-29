from __future__ import annotations

from pathlib import Path

from src.models import KeyFrame


def _frame_score(frame) -> float:
    import cv2

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    contrast = gray.std()
    return float(sharpness + contrast)


def extract_key_frames(video_path: Path, output_dir: Path, count: int) -> list[KeyFrame]:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Install `opencv-python` and `numpy` to extract video key frames.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return []

    fps = capture.get(cv2.CAP_PROP_FPS) or 24
    frame_total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_total <= 0:
        capture.release()
        return []

    sample_count = min(max(count * 5, count), frame_total)
    indices = np.linspace(0, frame_total - 1, sample_count, dtype=int)
    scored: list[tuple[float, int, np.ndarray]] = []

    for index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, frame = capture.read()
        if ok:
            scored.append((_frame_score(frame), int(index), frame.copy()))
    capture.release()

    selected = sorted(scored, key=lambda item: item[0], reverse=True)[:count]
    selected = sorted(selected, key=lambda item: item[1])

    frames: list[KeyFrame] = []
    for rank, (_, index, frame) in enumerate(selected, start=1):
        timestamp = index / fps
        path = output_dir / f"key_frame_{rank:02d}_{int(timestamp):04d}s.jpg"
        cv2.imwrite(str(path), frame)
        frames.append(
            KeyFrame(
                path=path,
                timestamp_seconds=timestamp,
                caption="Important visual moment detected from the video",
            )
        )
    return frames
