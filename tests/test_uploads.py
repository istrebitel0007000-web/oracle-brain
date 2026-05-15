"""tests/test_uploads.py — Upload module tests"""
import io, os, sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def cfg(tmp_path):
    return {
        "upload_dir": str(tmp_path / "uploads"),
        "max_upload_mb": 5,
        "allowed_upload_exts": [".txt",".py",".md",".pdf",".png",".jpg",".jpeg",".csv",".json"],
    }


def test_allowed_extensions(cfg):
    from oracle_brain.uploads import allowed_file
    assert allowed_file("report.txt", cfg)
    assert allowed_file("image.jpg", cfg)
    assert allowed_file("data.csv", cfg)
    assert not allowed_file("archive.zip", cfg)
    assert not allowed_file("script.exe", cfg)


def test_is_image():
    from oracle_brain.uploads import is_image
    assert is_image("photo.jpg")
    assert is_image("photo.PNG")
    assert is_image("img.jpeg")
    assert not is_image("doc.txt")
    assert not is_image("doc.pdf")


def test_save_and_extract_txt(tmp_path, cfg):
    from oracle_brain.uploads import save_upload
    content = b"Hello Oracle Brain!\nSecond line of content."
    result = save_upload(io.BytesIO(content), "hello.txt", cfg, "test@test.com")
    assert result["filename"] == "hello.txt"
    assert result["size_bytes"] == len(content)
    assert result["filetype"] == ".txt"
    assert "Hello Oracle Brain!" in result["extracted"]
    assert Path(result["filepath"]).exists()


def test_rejects_oversized_file(tmp_path, cfg):
    from oracle_brain.uploads import save_upload
    cfg["max_upload_mb"] = 1
    content = b"x" * (2 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds maximum size"):
        save_upload(io.BytesIO(content), "big.txt", cfg)


def test_rejects_bad_extension(cfg):
    from oracle_brain.uploads import save_upload
    with pytest.raises(ValueError, match="not allowed"):
        save_upload(io.BytesIO(b"data"), "evil.exe", cfg)


def test_extract_text_file(tmp_path):
    from oracle_brain.uploads import extract_text
    p = tmp_path / "test.txt"
    p.write_text("Line one\nLine two\nLine three")
    result = extract_text(p, ".txt")
    assert "Line one" in result and "Line three" in result


def test_build_file_context():
    from oracle_brain.uploads import build_file_context
    ctx = build_file_context("print('hello')", "script.py")
    assert "script.py" in ctx
    assert "print('hello')" in ctx


def test_build_file_context_empty_returns_empty():
    from oracle_brain.uploads import build_file_context
    assert build_file_context("", "empty.txt") == ""


def test_delete_upload(tmp_path):
    from oracle_brain.uploads import delete_upload
    p = tmp_path / "todelete.txt"
    p.write_text("bye")
    assert delete_upload(str(p)) is True
    assert not p.exists()


def test_delete_nonexistent_returns_false():
    from oracle_brain.uploads import delete_upload
    assert delete_upload("/nonexistent/ghost.txt") is False
