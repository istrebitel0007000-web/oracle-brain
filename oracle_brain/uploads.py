"""
oracle_brain/uploads.py — File upload + text extraction
Supports: .txt .py .md .json .csv .pdf .png .jpg .jpeg
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("oracle.uploads")

ALLOWED_EXTENSIONS = {".txt", ".py", ".md", ".pdf", ".png", ".jpg", ".jpeg", ".csv", ".json", ".html"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_TEXT_PREVIEW = 8000  # chars fed into LLM context

try:
    import pypdf
    _PYPDF = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        _PYPDF = True
    except ImportError:
        _PYPDF = False
        log.info("pypdf not installed; PDF text extraction disabled. Run: pip install pypdf")

try:
    import pytesseract
    from PIL import Image as PILImage
    _OCR = True
except ImportError:
    _OCR = False
    log.info("pytesseract/Pillow not installed; OCR disabled.")


def get_upload_dir(cfg: dict) -> Path:
    d = Path(cfg.get("upload_dir", "uploads"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def allowed_file(filename: str, cfg: dict) -> bool:
    ext = Path(filename).suffix.lower()
    allowed = set(cfg.get("allowed_upload_exts", list(ALLOWED_EXTENSIONS)))
    return ext in allowed


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def save_upload(file_obj, filename: str, cfg: dict, user_email: str = "anonymous") -> dict:
    """
    Save uploaded file to disk.
    Returns dict with filepath, filename, size_bytes, extracted_text.
    """
    upload_dir = get_upload_dir(cfg)
    max_mb = cfg.get("max_upload_mb", 20)
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS and ext not in set(cfg.get("allowed_upload_exts", [])):
        raise ValueError(f"File type '{ext}' not allowed.")

    # Unique filename to avoid collisions
    safe_name = f"{user_email.replace('@','_')}_{uuid.uuid4().hex[:8]}_{Path(filename).name}"
    filepath = upload_dir / safe_name

    # Stream write + size check
    size = 0
    max_bytes = max_mb * 1024 * 1024
    chunks = []
    for chunk in _iter_chunks(file_obj):
        size += len(chunk)
        if size > max_bytes:
            raise ValueError(f"File exceeds maximum size of {max_mb}MB.")
        chunks.append(chunk)

    with open(filepath, "wb") as f:
        for chunk in chunks:
            f.write(chunk)

    extracted = extract_text(filepath, ext)

    return {
        "filename": filename,
        "filepath": str(filepath),
        "size_bytes": size,
        "filetype": ext,
        "extracted": extracted,
    }


def _iter_chunks(file_obj, chunk_size: int = 65536):
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        yield chunk


def extract_text(filepath: Path | str, ext: str = "") -> str:
    """Extract readable text from a file. Returns up to MAX_TEXT_PREVIEW chars."""
    filepath = Path(filepath)
    ext = ext or filepath.suffix.lower()

    try:
        if ext == ".pdf":
            return _extract_pdf(filepath)
        elif ext in IMAGE_EXTENSIONS:
            return _extract_image(filepath)
        elif ext in {".txt", ".py", ".md", ".json", ".csv", ".html"}:
            return _extract_text_file(filepath)
        else:
            return ""
    except Exception as e:
        log.warning(f"Text extraction failed for {filepath}: {e}")
        return ""


def _extract_text_file(filepath: Path) -> str:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read(MAX_TEXT_PREVIEW + 100)
    return text[:MAX_TEXT_PREVIEW]


def _extract_pdf(filepath: Path) -> str:
    if not _PYPDF:
        return "[PDF text extraction unavailable — install pypdf]"
    text_parts = []
    try:
        reader = pypdf.PdfReader(str(filepath))
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
            if sum(len(t) for t in text_parts) > MAX_TEXT_PREVIEW:
                break
    except Exception as e:
        return f"[PDF read error: {e}]"
    full = "\n".join(text_parts)
    return full[:MAX_TEXT_PREVIEW]


def _extract_image(filepath: Path) -> str:
    if not _OCR:
        return "[Image OCR unavailable — install pytesseract + Pillow]"
    try:
        img = PILImage.open(filepath)
        text = pytesseract.image_to_string(img)
        return text[:MAX_TEXT_PREVIEW]
    except Exception as e:
        return f"[OCR error: {e}]"


def build_file_context(extracted: str, filename: str) -> str:
    """Build an LLM-ready context block for an uploaded file."""
    if not extracted:
        return ""
    preview = extracted[:MAX_TEXT_PREVIEW]
    return (
        f"\n\n---\n"
        f"📎 **Attached file:** `{filename}`\n"
        f"**Content:**\n```\n{preview}\n```\n"
        f"---\n"
    )


def delete_upload(filepath: str) -> bool:
    """Delete a file from disk. Returns True if successful."""
    try:
        p = Path(filepath)
        if p.exists() and p.is_file():
            p.unlink()
            return True
    except Exception as e:
        log.warning(f"delete_upload failed: {e}")
    return False
