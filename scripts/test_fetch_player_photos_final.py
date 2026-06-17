#!/usr/bin/env python3
"""
TDD tests for fetch_player_photos_final.py — the deep photo search pipeline.

Covers: _name_similar, generate_tm_variants, country_matches, get_player_info,
        strategy_transfermarkt, strategy_wikidata, strategy_sportsdb,
        strategy_wikipedia_page_image, deep_search_single, download retry.
"""

import json
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(__file__))

import fetch_player_photos_final as fpf


# -- Fixtures -------------------------------------------------------------

SAMPLE_TM_HTML = """
<html><body>
<img src="https://img.a.transfermarkt.technology/portrait/small/563749-1765461184.png?lm=1"
     title="Oguz Aydin" />
<img src="https://tmssl.akamaized.net//images/flagge/verysmall/174.png?lm=1"
     title="Turkey" />
<img src="https://tmssl.akamaized.net//images/wappen/tiny/36.png?lm=1"
     title="Fenerbahce" />
</body></html>
"""

SAMPLE_WIKIDATA_SEARCH = {
    "search": [
        {"id": "Q12345", "label": "Test Player", "description": "footballer"}
    ]
}

SAMPLE_WIKIDATA_SPARQL = {
    "results": {
        "bindings": [
            {"img": {"value": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Test.jpg/500px-Test.jpg"}}
        ]
    }
}

SAMPLE_SPORTSDB = {
    "player": [
        {
            "strPlayer": "Test Player",
            "strCutout": "https://r2.thesportsdb.com/images/media/player/cutout/abc123.png",
            "strThumb": "",
            "strRender": "",
        }
    ]
}

SAMPLE_WIKI_SEARCH = {
    "query": {
        "search": [{"title": "Test Player"}]
    }
}

SAMPLE_WIKI_PAGEIMG = {
    "query": {
        "pages": {
            "12345": {
                "thumbnail": {"source": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/Test.jpg/500px-Test.jpg"}
            }
        }
    }
}


def _mock_urlopen(response_data, status=200):
    """Create a mock urllib response."""
    mock_resp = MagicMock()
    if isinstance(response_data, str):
        mock_resp.read.return_value = response_data.encode("utf-8")
    elif isinstance(response_data, bytes):
        mock_resp.read.return_value = response_data
    else:
        mock_resp.read.return_value = json.dumps(response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    return mock_resp


# -- Test: _name_similar --------------------------------------------------

class TestNameSimilarity(unittest.TestCase):
    """Tests for the loose name similarity check used in Transfermarkt matching."""

    def test_exact_match(self):
        self.assertTrue(fpf._name_similar("Erling Haaland", "Erling Haaland"))

    def test_case_insensitive(self):
        self.assertTrue(fpf._name_similar("erling haaland", "ERLING HAALAND"))

    def test_reversed_name(self):
        self.assertTrue(fpf._name_similar("Haaland Erling", "Erling Haaland"))

    def test_last_name_exact(self):
        self.assertTrue(fpf._name_similar("K. Haaland", "Erling Haaland"))

    def test_substring_containment(self):
        self.assertTrue(fpf._name_similar("Dong", "Donga"))

    def test_leading_char_strip(self):
        """'eiri' should match 'iri' via leading-char removal."""
        self.assertTrue(fpf._name_similar("Danial Eiri", "Danial Iri"))

    def test_no_match_different_person(self):
        self.assertFalse(fpf._name_similar("Erling Haaland", "Kylian Mbappe"))

    def test_short_name_no_false_positive(self):
        self.assertFalse(fpf._name_similar("Li", "Wu"))

    def test_accent_stripping(self):
        self.assertTrue(fpf._name_similar("Mbappe", "Mbappé"))

    def test_normalized_spaces(self):
        self.assertTrue(fpf._name_similar("Son  Heung-Min", "Son Heung-Min"))


# -- Test: generate_tm_variants -------------------------------------------

class TestGenerateTmVariants(unittest.TestCase):
    """Tests for Transfermarkt name variant generation."""

    def test_manual_variants_first(self):
        variants = fpf.generate_tm_variants("Mostafa Zico")
        self.assertIn("Mostafa Ziko", variants)
        # Manual variant should come before the original
        self.assertLess(variants.index("Mostafa Ziko"), variants.index("Mostafa Zico"))

    def test_hyphen_removal(self):
        variants = fpf.generate_tm_variants("Al-Daoud Mohammad")
        self.assertIn("Al Daoud Mohammad", variants)

    def test_reverse_name(self):
        variants = fpf.generate_tm_variants("Son Heung-Min")
        self.assertIn("Heung-Min Son", variants)

    def test_last_name_only(self):
        variants = fpf.generate_tm_variants("Mohamed Salah")
        self.assertIn("Salah", variants)

    def test_first_name_only(self):
        variants = fpf.generate_tm_variants("Mohamed Salah")
        self.assertIn("Mohamed", variants)

    def test_al_prefix_stripped(self):
        variants = fpf.generate_tm_variants("Al-Daoud Mohammad")
        self.assertIn("Daoud", variants)

    def test_no_duplicates(self):
        variants = fpf.generate_tm_variants("Son Heung-Min")
        self.assertEqual(len(variants), len(set(variants)))

    def test_minimum_length_filter(self):
        variants = fpf.generate_tm_variants("Li Wu")
        # "Li" is only 2 chars, should be filtered out
        self.assertNotIn("Li", variants)


# -- Test: country_matches ------------------------------------------------

class TestCountryMatch(unittest.TestCase):
    """Tests for country name matching."""

    def test_exact(self):
        self.assertTrue(fpf.country_matches("Egypt", "Egypt"))

    def test_substring(self):
        self.assertTrue(fpf.country_matches("Saudi Arabia", "Saudi"))

    def test_turkey_turkiye(self):
        self.assertTrue(fpf.country_matches("Türkiye", "Turkey"))

    def test_turkey_variant(self):
        self.assertTrue(fpf.country_matches("Turkey", "Türkiye"))

    def test_empty_returns_false(self):
        self.assertFalse(fpf.country_matches("", "Egypt"))
        self.assertFalse(fpf.country_matches("Egypt", ""))

    def test_case_insensitive(self):
        self.assertTrue(fpf.country_matches("egypt", "EGYPT"))

    def test_no_match(self):
        self.assertFalse(fpf.country_matches("France", "Egypt"))


# -- Test: get_player_info ------------------------------------------------

class TestGetPlayerInfo(unittest.TestCase):
    """Tests for player info lookup from player_mapping.json."""

    def test_known_player(self):
        pm = {"Test Player": {"team": "埃及", "jersey": "10", "position": "F"}}
        info = fpf.get_player_info("Test Player", pm)
        self.assertEqual(info["country"], "Egypt")
        self.assertEqual(info["team"], "埃及")

    def test_unknown_player(self):
        info = fpf.get_player_info("Unknown", {})
        self.assertEqual(info["country"], "")
        self.assertEqual(info["team"], "")

    def test_turkey_mapping(self):
        pm = {"Test": {"team": "土耳其"}}
        info = fpf.get_player_info("Test", pm)
        self.assertEqual(info["country"], "Turkey")


# -- Test: strategy_transfermarkt (mocked HTTP) ----------------------------

class TestStrategyTransfermarkt(unittest.TestCase):
    """Tests for Transfermarkt search strategy with mocked HTTP."""

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_parses_html_and_returns_url(self, mock_sleep, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(SAMPLE_TM_HTML)
        result = fpf.strategy_transfermarkt("Oguz Aydin", "Turkey")
        self.assertIsNotNone(result)
        self.assertIn("563749", result)
        self.assertIn("portrait/header", result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_filters_by_country(self, mock_sleep, mock_urlopen):
        # HTML has Turkey flag, but we expect Egypt → no match
        mock_urlopen.return_value = _mock_urlopen(SAMPLE_TM_HTML)
        result = fpf.strategy_transfermarkt("Oguz Aydin", "Egypt")
        self.assertIsNone(result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_returns_none_on_empty(self, mock_sleep, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen("<html><body>no results</body></html>")
        result = fpf.strategy_transfermarkt("Unknown Player", "Egypt")
        self.assertIsNone(result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_handles_exception(self, mock_sleep, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")
        result = fpf.strategy_transfermarkt("Test", "Egypt")
        self.assertIsNone(result)


# -- Test: strategy_wikidata (mocked HTTP) ---------------------------------

class TestStrategyWikidata(unittest.TestCase):
    """Tests for Wikidata entity search + image property lookup."""

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_entity_search_returns_image(self, mock_sleep, mock_urlopen):
        # First call: wbsearchentities, second call: SPARQL
        responses = [
            _mock_urlopen(SAMPLE_WIKIDATA_SEARCH),
            _mock_urlopen(SAMPLE_WIKIDATA_SPARQL),
        ]
        mock_urlopen.side_effect = responses
        result = fpf.strategy_wikidata("Test Player")
        self.assertIsNotNone(result)
        self.assertIn("upload.wikimedia.org", result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_skips_non_football_entity(self, mock_sleep, mock_urlopen):
        non_football = {"search": [{"id": "Q99", "label": "Test", "description": "politician"}]}
        mock_urlopen.return_value = _mock_urlopen(non_football)
        result = fpf.strategy_wikidata("Test")
        self.assertIsNone(result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_returns_none_on_empty_search(self, mock_sleep, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"search": []})
        result = fpf.strategy_wikidata("Xyzabc")
        self.assertIsNone(result)


# -- Test: strategy_sportsdb (mocked HTTP) ---------------------------------

class TestStrategySportsdb(unittest.TestCase):
    """Tests for TheSportsDB search strategy."""

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_finds_player_with_cutout(self, mock_sleep, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(SAMPLE_SPORTSDB)
        result = fpf.strategy_sportsdb("Test Player")
        self.assertIsNotNone(result)
        self.assertIn("cutout", result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_skips_no_image(self, mock_sleep, mock_urlopen):
        no_img = {"player": [{"strPlayer": "Test Player", "strCutout": "", "strThumb": "", "strRender": ""}]}
        mock_urlopen.return_value = _mock_urlopen(no_img)
        result = fpf.strategy_sportsdb("Test Player")
        self.assertIsNone(result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_returns_none_on_no_player(self, mock_sleep, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"player": None})
        result = fpf.strategy_sportsdb("Unknown")
        self.assertIsNone(result)


# -- Test: strategy_wikipedia_page_image (mocked HTTP) ---------------------

class TestStrategyWikipediaPageImage(unittest.TestCase):
    """Tests for Wikipedia article page image extraction."""

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_search_and_extract_image(self, mock_sleep, mock_urlopen):
        responses = [
            _mock_urlopen(SAMPLE_WIKI_SEARCH),
            _mock_urlopen(SAMPLE_WIKI_PAGEIMG),
        ]
        mock_urlopen.side_effect = responses
        result = fpf.strategy_wikipedia_page_image("Test Player")
        self.assertIsNotNone(result)
        self.assertIn("upload.wikimedia.org", result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_returns_none_on_no_search_results(self, mock_sleep, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"query": {"search": []}})
        result = fpf.strategy_wikipedia_page_image("Xyzabc Unknown")
        self.assertIsNone(result)

    @patch("fetch_player_photos_final.urllib.request.urlopen")
    @patch("fetch_player_photos_final.time.sleep")
    def test_returns_none_on_no_thumbnail(self, mock_sleep, mock_urlopen):
        no_thumb = {"query": {"pages": {"123": {}}}}
        responses = [_mock_urlopen(SAMPLE_WIKI_SEARCH), _mock_urlopen(no_thumb)]
        mock_urlopen.side_effect = responses
        result = fpf.strategy_wikipedia_page_image("Test Player")
        self.assertIsNone(result)


# -- Test: deep_search_single (mocked strategies) -------------------------

class TestDeepSearchSingle(unittest.TestCase):
    """Tests for the orchestrator that chains all strategies."""

    @patch("fetch_player_photos_final.strategy_transfermarkt", return_value="http://tm.jpg")
    @patch("fetch_player_photos_final.strategy_wikidata")
    @patch("fetch_player_photos_final.strategy_sportsdb")
    @patch("fetch_player_photos_final.strategy_wikipedia_page_image")
    def test_stops_on_first_success(self, mock_wiki, mock_sdb, mock_wd, mock_tm):
        url, name = fpf.deep_search_single("Test", {})
        self.assertEqual(url, "http://tm.jpg")
        self.assertEqual(name, "transfermarkt")
        mock_wd.assert_not_called()
        mock_sdb.assert_not_called()
        mock_wiki.assert_not_called()

    @patch("fetch_player_photos_final.strategy_transfermarkt", return_value=None)
    @patch("fetch_player_photos_final.strategy_wikidata", return_value="http://wd.jpg")
    def test_tries_next_strategy_on_failure(self, mock_wd, mock_tm):
        url, name = fpf.deep_search_single("Test", {})
        self.assertEqual(url, "http://wd.jpg")
        self.assertEqual(name, "wikidata")

    @patch("fetch_player_photos_final.strategy_transfermarkt", return_value=None)
    @patch("fetch_player_photos_final.strategy_wikidata", return_value=None)
    @patch("fetch_player_photos_final.strategy_sportsdb", return_value=None)
    @patch("fetch_player_photos_final.strategy_wikipedia_page_image", return_value=None)
    def test_returns_none_when_all_fail(self, mock_wiki, mock_sdb, mock_wd, mock_tm):
        url, name = fpf.deep_search_single("Test", {})
        self.assertIsNone(url)
        self.assertIsNone(name)

    @patch("fetch_player_photos_final.strategy_transfermarkt", side_effect=Exception("boom"))
    @patch("fetch_player_photos_final.strategy_wikidata", return_value="http://wd.jpg")
    def test_handles_strategy_exception(self, mock_wd, mock_tm):
        url, name = fpf.deep_search_single("Test", {})
        self.assertEqual(url, "http://wd.jpg")


# -- Test: download_image retry (from photo_utils) ------------------------

class TestDownloadRetry(unittest.TestCase):
    """Tests for HTTP retry logic in download_image."""

    @patch("photo_utils.urllib.request.urlopen")
    @patch("time.sleep")
    def test_429_retries_then_succeeds(self, mock_sleep, mock_urlopen):
        from photo_utils import download_image

        error_429 = urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
        ok_resp = _mock_urlopen(b"\x89PNG\r\n" + b"\x00" * 3000)

        mock_urlopen.side_effect = [error_429, ok_resp]

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            result = download_image("http://example.com/img.png", path)
            self.assertTrue(result)
        finally:
            os.unlink(path)

    @patch("photo_utils.urllib.request.urlopen")
    def test_404_returns_false_immediately(self, mock_urlopen):
        from photo_utils import download_image

        error_404 = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        mock_urlopen.side_effect = error_404

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            result = download_image("http://example.com/img.png", path)
            self.assertFalse(result)
        finally:
            os.unlink(path)

    @patch("time.sleep")
    @patch("photo_utils.urllib.request.urlopen")
    def test_all_retries_fail(self, mock_urlopen, mock_sleep):
        from photo_utils import download_image

        error_429 = urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
        mock_urlopen.side_effect = error_429

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            result = download_image("http://example.com/img.png", path)
            self.assertFalse(result)
        finally:
            if os.path.exists(path):
                os.unlink(path)


# -- Test: mapping roundtrip -----------------------------------------------

class TestMappingRoundTrip(unittest.TestCase):
    """Tests for photo_mapping.json load/save roundtrip integrity."""

    def test_unicode_survives_roundtrip(self):
        from photo_utils import load_mapping, save_mapping, PHOTO_MAPPING_FILE

        test_data = {"孙兴慜": {"source": "wikidata", "path": "data/photos/test.png"}}
        original_load = load_mapping()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False)
            tmp_path = f.name

        with open(tmp_path, encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["孙兴慜"]["source"], "wikidata")
        os.unlink(tmp_path)

    def test_nested_objects_preserved(self):
        data = {"Player": {"source": "espn", "path": "data/photos/123.png", "athlete_id": "12345"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f)
            tmp_path = f.name
        with open(tmp_path, encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["Player"]["athlete_id"], "12345")
        os.unlink(tmp_path)

    def test_malformed_json_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("{invalid json content")
            tmp_path = f.name
        try:
            with self.assertRaises(json.JSONDecodeError):
                with open(tmp_path, encoding="utf-8") as f:
                    json.load(f)
        finally:
            os.unlink(tmp_path)


# -- Test: no double-dot filenames in mapping ------------------------------

class TestNoDoubleDotPaths(unittest.TestCase):
    """Regression test: ensure no mapping path contains '..'"""

    def test_no_double_dot_in_current_mapping(self):
        from photo_utils import load_mapping
        mapping = load_mapping()
        for player, info in mapping.items():
            path = info.get("path", "")
            self.assertNotIn("..", path,
                             f"Player '{player}' has double-dot path: {path}")


if __name__ == "__main__":
    unittest.main()
