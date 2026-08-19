from __future__ import annotations

import io
import re
from urllib.parse import urlsplit

MAX_QR_IMAGE_BYTES = 15 * 1024 * 1024
TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{20,160}")


def qr_png(payload: str) -> bytes:
    import qrcode

    image = qrcode.make(payload)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def student_token_from_qr_payload(payload: str) -> str | None:
    """Extrahiert nur die Identität und ignoriert eine veraltete QR-Adresse."""
    value = payload.strip()
    if value.startswith("collector:student:"):
        candidate = value.removeprefix("collector:student:")
    else:
        try:
            path = urlsplit(value).path
        except ValueError:
            return None
        match = re.search(r"(?:^|/)p/([A-Za-z0-9_-]{20,160})(?:/|$)", path)
        candidate = match.group(1) if match else ""
    return candidate if TOKEN_RE.fullmatch(candidate) else None


def _decode_candidate(detector, image, cv2) -> str | None:
    decoded, points, _ = detector.detectAndDecode(image)
    if decoded:
        return decoded
    try:
        ok, values, _, _ = detector.detectAndDecodeMulti(image)
        if ok:
            return next((value for value in values if value), None)
    except (AttributeError, cv2.error):
        pass
    return None


def decode_qr_image(image_bytes: bytes) -> str | None:
    """Liest ein Kamerabild ausschließlich im Arbeitsspeicher."""
    if not image_bytes or len(image_bytes) > MAX_QR_IMAGE_BYTES:
        return None
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("QR-Bilderkennung ist nicht installiert.") from exc

    image = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    if image is None:
        return None
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest > 3200:
        scale = 3200 / longest
        image = cv2.resize(
            image,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    detector = cv2.QRCodeDetector()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    candidates = [image, gray]
    try:
        candidates.append(
            cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        )
    except cv2.error:
        pass
    for candidate in candidates:
        for rotated in (
            candidate,
            cv2.rotate(candidate, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(candidate, cv2.ROTATE_180),
            cv2.rotate(candidate, cv2.ROTATE_90_COUNTERCLOCKWISE),
        ):
            decoded = _decode_candidate(detector, rotated, cv2)
            if decoded:
                return decoded
    return None
