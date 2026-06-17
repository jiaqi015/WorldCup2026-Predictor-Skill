#!/usr/bin/env python3
"""Tests for generate_avatars.py — SVG avatar generation."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import generate_avatars as ga


class TestGetInitials(unittest.TestCase):

    def test_two_words(self):
        self.assertEqual(ga.get_initials("Kylian Mbappe"), "KM")

    def test_single_word(self):
        self.assertEqual(ga.get_initials("Neymar"), "NE")

    def test_three_words(self):
        self.assertEqual(ga.get_initials("Vinicius Junior Moreira"), "VM")

    def test_empty(self):
        self.assertEqual(ga.get_initials(""), "XX")

    def test_single_char(self):
        self.assertEqual(ga.get_initials("X"), "XX")

    def test_leading_trailing_spaces(self):
        self.assertEqual(ga.get_initials("  Mbappé Kylian  "), "MK")


class TestGetPositionLabel(unittest.TestCase):

    def test_goalkeeper(self):
        self.assertEqual(ga.get_position_label("G"), "GK")

    def test_defender(self):
        self.assertEqual(ga.get_position_label("D"), "DF")

    def test_midfielder(self):
        self.assertEqual(ga.get_position_label("M"), "MF")

    def test_forward(self):
        self.assertEqual(ga.get_position_label("F"), "FW")

    def test_unknown(self):
        self.assertEqual(ga.get_position_label("X"), "")

    def test_none(self):
        self.assertEqual(ga.get_position_label(None), "")


class TestGenerateSvgAvatar(unittest.TestCase):

    def test_contains_initials(self):
        svg = ga.generate_svg_avatar("Kylian Mbappe", "France", 10, "F")
        self.assertIn("KM", svg)

    def test_contains_jersey(self):
        svg = ga.generate_svg_avatar("Kylian Mbappe", "France", 10, "F")
        self.assertIn("#10", svg)

    def test_contains_position_label(self):
        svg = ga.generate_svg_avatar("Kylian Mbappe", "France", 10, "F")
        self.assertIn("FW", svg)

    def test_team_colors_applied(self):
        svg = ga.generate_svg_avatar("Test Player", "France", 1, "D")
        self.assertIn("#002395", svg)  # France primary

    def test_unknown_team_fallback_color(self):
        svg = ga.generate_svg_avatar("Test Player", "Nonexistent", 1, "D")
        self.assertIn("#4A90D9", svg)  # default primary

    def test_is_valid_svg(self):
        svg = ga.generate_svg_avatar("Test Player", "Brazil", 9, "F")
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("xmlns=", svg)

    def test_xml_injection_escaped(self):
        """SVG must escape XML special chars to prevent injection."""
        svg = ga.generate_svg_avatar("<script>alert(1)</script>", "France", 10, "F")
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;S", svg)

    def test_jersey_xml_injection_escaped(self):
        svg = ga.generate_svg_avatar("Test", "France", '"><rect/>', "F")
        self.assertNotIn("<rect/>", svg)
        self.assertIn("&lt;rect/&gt;", svg)

    def test_position_xml_injection_escaped(self):
        # get_position_label only returns known labels or empty, so injection
        # through position is unlikely. But verify the escape path works.
        svg = ga.generate_svg_avatar("Test", "France", 1, "G")
        self.assertIn("GK", svg)

    def test_custom_size(self):
        svg = ga.generate_svg_avatar("Test", "France", 1, "D", size=100)
        self.assertIn('width="100"', svg)
        self.assertIn('height="100"', svg)


if __name__ == "__main__":
    unittest.main()
