#!/usr/bin/env python3
"""TDD tests for photo_utils.py — shared photo utilities."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent))
import photo_utils


class TestNormalizeName(unittest.TestCase):
    """NFKD normalization: strip accents, lowercase, collapse spaces."""

    def test_plain_ascii(self):
        self.assertEqual(photo_utils.normalize_name("Erling Haaland"), "erling haaland")

    def test_accented(self):
        self.assertEqual(photo_utils.normalize_name("Kylian Mbappé"), "kylian mbappe")

    def test_cedilla(self):
        self.assertEqual(photo_utils.normalize_name("Aïssa Mandi"), "aissa mandi")

    def test_turkish(self):
        self.assertEqual(photo_utils.normalize_name("Abdülkerim Bardakçı"), "abdulkerim bardakci")

    def test_multiple_spaces(self):
        self.assertEqual(photo_utils.normalize_name("  Erling   Haaland  "), "erling haaland")

    def test_empty(self):
        self.assertEqual(photo_utils.normalize_name(""), "")

    def test_single_word(self):
        self.assertEqual(photo_utils.normalize_name("Neymar"), "neymar")


class TestSurname(unittest.TestCase):

    def test_two_words(self):
        self.assertEqual(photo_utils.surname("Erling Haaland"), "Haaland")

    def test_three_words(self):
        self.assertEqual(photo_utils.surname("Da Silva Santos"), "Santos")

    def test_single_word(self):
        self.assertEqual(photo_utils.surname("Neymar"), "Neymar")

    def test_empty(self):
        self.assertEqual(photo_utils.surname(""), "")

    def test_trailing_spaces(self):
        self.assertEqual(photo_utils.surname("Erling Haaland  "), "Haaland")


class TestSafeName(unittest.TestCase):
    """Convert player name to safe filename (strip accents, spaces->underscore)."""

    def test_plain(self):
        self.assertEqual(photo_utils.safe_name("Erling Haaland"), "Erling_Haaland")

    def test_accented(self):
        self.assertEqual(photo_utils.safe_name("Kylian Mbappé"), "Kylian_Mbappe")

    def test_turkish(self):
        self.assertEqual(photo_utils.safe_name("Abdülkerim Bardakçı"), "Abdulkerim_Bardakci")

    def test_empty(self):
        self.assertEqual(photo_utils.safe_name(""), "")

    def test_path_traversal(self):
        """H2: safe_name must neutralize path traversal attempts."""
        result = photo_utils.safe_name("../etc/passwd")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)

    def test_slash_in_name(self):
        """H2: slashes must be stripped."""
        result = photo_utils.safe_name("O'Brien/Test")
        self.assertNotIn("/", result)
        self.assertNotIn("\\", result)

    def test_null_byte(self):
        """H2: null bytes must be stripped."""
        result = photo_utils.safe_name("Test\x00Player")
        self.assertNotIn("\x00", result)

    def test_only_unsafe_chars(self):
        """H2: if all chars are unsafe, return 'unknown'."""
        self.assertEqual(photo_utils.safe_name("/..:\\"), "unknown")


class TestValidateImage(unittest.TestCase):
    """Magic bytes validation: accept PNG/JPEG/WEBP, reject HTML/SVG/other."""

    def _write_temp(self, header_bytes, suffix=""):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(header_bytes + b"\x00" * 100)
        return path

    def test_valid_png(self):
        path = self._write_temp(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')
        self.assertTrue(photo_utils.validate_image(path))
        # Valid files should NOT be deleted
        self.assertTrue(os.path.exists(path))
        os.unlink(path)

    def test_valid_jpeg(self):
        path = self._write_temp(b'\xFF\xD8\xFF\xE0\x00\x10JFIF')
        self.assertTrue(photo_utils.validate_image(path))

    def test_valid_webp(self):
        header = b'RIFF\x00\x00\x00\x00WEBP'
        path = self._write_temp(header)
        self.assertTrue(photo_utils.validate_image(path))

    def test_reject_html(self):
        path = self._write_temp(b'<!DOCTYPE html><html>')
        self.assertFalse(photo_utils.validate_image(path))
        self.assertFalse(os.path.exists(path))  # rejected files deleted

    def test_reject_svg(self):
        path = self._write_temp(b'<svg xmlns="http://www.w3.org/2000/svg">')
        self.assertFalse(photo_utils.validate_image(path))
        self.assertFalse(os.path.exists(path))

    def test_reject_empty(self):
        path = self._write_temp(b'')
        self.assertFalse(photo_utils.validate_image(path))

    def test_nonexistent_file(self):
        self.assertFalse(photo_utils.validate_image("/tmp/nonexistent_file_12345.png"))


class TestLoadMapping(unittest.TestCase):

    def test_loads_valid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"Test Player": {"source": "placeholder", "path": "x.svg"}}, f)
            f.flush()
            result = photo_utils.load_mapping(f.name)
        os.unlink(f.name)
        self.assertIn("Test Player", result)

    def test_missing_file_returns_empty(self):
        result = photo_utils.load_mapping("/tmp/nonexistent_mapping_12345.json")
        self.assertEqual(result, {})


class TestSaveMapping(unittest.TestCase):

    def test_atomic_write(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            path = f.name
        data = {"Player": {"source": "wikidata", "path": "data/photos/test.png"}}
        photo_utils.save_mapping(data, path)
        with open(path) as f:
            loaded = json.load(f)
        self.assertEqual(loaded, data)
        os.unlink(path)

    def test_no_corruption_on_same_file(self):
        """Writing to the same file we read from must not corrupt."""
        path = tempfile.mktemp(suffix=".json")
        original = {"A": {"source": "a"}}
        with open(path, "w") as f:
            json.dump(original, f)
        updated = {"A": {"source": "a"}, "B": {"source": "b"}}
        photo_utils.save_mapping(updated, path)
        with open(path) as f:
            self.assertEqual(json.load(f), updated)
        os.unlink(path)


class TestDetermineExt(unittest.TestCase):
    """M3: Shared determine_ext function."""

    def test_png(self):
        self.assertEqual(photo_utils.determine_ext("http://example.com/img.png"), ".png")

    def test_webp(self):
        self.assertEqual(photo_utils.determine_ext("http://example.com/img.webp"), ".webp")

    def test_default_jpg(self):
        self.assertEqual(photo_utils.determine_ext("http://example.com/img"), ".jpg")

    def test_strips_query_params(self):
        self.assertEqual(photo_utils.determine_ext("http://example.com/img.png?width=256"), ".png")


class TestDownloadImageSizeLimit(unittest.TestCase):
    """H3: download_image must reject files exceeding MAX_IMAGE_SIZE."""

    def test_rejects_oversized(self):
        """Files larger than MAX_IMAGE_SIZE must be rejected."""
        import urllib.request
        from unittest.mock import MagicMock

        # Simulate a response returning more than MAX_IMAGE_SIZE bytes
        oversized = b"x" * (photo_utils.MAX_IMAGE_SIZE + 1)
        mock_resp = MagicMock()
        mock_resp.read.return_value = oversized
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_resp):
            result = photo_utils.download_image("http://example.com/huge.jpg", "/tmp/test_huge.jpg")
        self.assertFalse(result)

    def test_rejects_tiny(self):
        """Files smaller than 2000 bytes must be rejected."""
        import urllib.request
        from unittest.mock import MagicMock

        tiny = b"x" * 100
        mock_resp = MagicMock()
        mock_resp.read.return_value = tiny
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_resp):
            result = photo_utils.download_image("http://example.com/tiny.jpg", "/tmp/test_tiny.jpg")
        self.assertFalse(result)


class TestGetPlaceholders(unittest.TestCase):

    def test_returns_only_placeholders(self):
        mapping = {
            "A": {"source": "espn", "path": "a.png"},
            "B": {"source": "placeholder", "path": "b.svg"},
            "C": {"source": "wikidata", "path": "c.jpg"},
        }
        result = photo_utils.get_placeholders(mapping)
        self.assertEqual(list(result.keys()), ["B"])

    def test_empty_mapping_returns_empty(self):
        result = photo_utils.get_placeholders({})
        self.assertEqual(result, {})

    def test_no_placeholders(self):
        mapping = {
            "A": {"source": "espn", "path": "a.png"},
            "B": {"source": "sofifa", "path": "b.png"},
        }
        result = photo_utils.get_placeholders(mapping)
        self.assertEqual(result, {})


class TestDownloadImageSuccess(unittest.TestCase):

    def test_success_path(self):
        """Valid PNG image should be saved and return True."""
        import urllib.request
        from unittest.mock import MagicMock
        import tempfile

        png_data = b"\x89PNG\r\n" + b"\x00" * 3000
        mock_resp = MagicMock()
        mock_resp.read.return_value = png_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            with patch.object(urllib.request, "urlopen", return_value=mock_resp):
                result = photo_utils.download_image("http://example.com/ok.png", path)
            self.assertTrue(result)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), png_data)
        finally:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    unittest.main()
