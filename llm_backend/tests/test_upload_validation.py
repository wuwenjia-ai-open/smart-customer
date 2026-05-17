"""测试文件上传校验逻辑"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi import UploadFile, HTTPException
from app.api.upload import _validate_file, MAX_FILE_SIZE, ALLOWED_EXTENSIONS


class FakeUploadFile:
    def __init__(self, filename, content_type=None):
        self.filename = filename
        self.content_type = content_type or "application/octet-stream"


class TestValidateFile:
    def test_allows_jpg(self):
        f = FakeUploadFile("photo.jpg", "image/jpeg")
        _validate_file(f)  # 不应抛异常

    def test_allows_png(self):
        f = FakeUploadFile("screenshot.png", "image/png")
        _validate_file(f)

    def test_allows_pdf(self):
        f = FakeUploadFile("doc.pdf", "application/pdf")
        _validate_file(f)

    def test_allows_txt(self):
        f = FakeUploadFile("notes.txt", "text/plain")
        _validate_file(f)

    def test_allows_csv(self):
        f = FakeUploadFile("data.csv", "text/csv")
        _validate_file(f)

    def test_rejects_exe(self):
        f = FakeUploadFile("virus.exe")
        with pytest.raises(HTTPException) as exc:
            _validate_file(f)
        assert exc.value.status_code == 400
        assert "exe" in str(exc.value.detail)

    def test_rejects_no_extension(self):
        f = FakeUploadFile("noext")
        with pytest.raises(HTTPException) as exc:
            _validate_file(f)
        assert exc.value.status_code == 400

    def test_rejects_empty_filename(self):
        f = FakeUploadFile("")
        with pytest.raises(HTTPException) as exc:
            _validate_file(f)
        assert exc.value.status_code == 400

    def test_case_insensitive(self):
        f = FakeUploadFile("PHOTO.JPG", "image/jpeg")
        _validate_file(f)  # 不应抛异常
        f2 = FakeUploadFile("Photo.PnG", "image/png")
        _validate_file(f2)

    def test_allowed_extensions_are_complete(self):
        """确保白名单覆盖了常见图片和文档格式"""
        assert ".jpg" in ALLOWED_EXTENSIONS
        assert ".png" in ALLOWED_EXTENSIONS
        assert ".pdf" in ALLOWED_EXTENSIONS
        assert ".txt" in ALLOWED_EXTENSIONS

    def test_max_file_size_is_reasonable(self):
        assert 1 * 1024 * 1024 <= MAX_FILE_SIZE <= 100 * 1024 * 1024
