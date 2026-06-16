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


if __name__ == "__main__":
    unittest.main()
