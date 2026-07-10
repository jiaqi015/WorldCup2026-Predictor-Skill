#!/usr/bin/env python3
"""Tests for deterministic prediction-data embedding boundaries."""

import unittest

import embed_prediction_data as embed


class TestPredictionDataEmbedding(unittest.TestCase):
    def test_upsert_only_replaces_the_named_generated_variable(self):
        source = (
            "before\n"
            "var TARGET={\"old\":1};\n"
            "function businessLogic(){return 42;}\n"
            "// === END REAL DATA ===\n"
            "after\n"
        )

        updated = embed.upsert_var(source, "TARGET", '{"new":2}')

        self.assertEqual(updated.count("var TARGET="), 1)
        self.assertIn('var TARGET={"new":2};', updated)
        self.assertIn("function businessLogic(){return 42;}", updated)
        self.assertNotIn('"old":1', updated)

    def test_upsert_requires_the_generated_data_boundary(self):
        with self.assertRaisesRegex(RuntimeError, "missing data marker"):
            embed.upsert_var("var TARGET={};", "TARGET", "{}")

    def test_runtime_contract_is_validated_instead_of_rewritten(self):
        source = """
function weightedPick(players,team,weights,fallback,type){
  var threatMap=PLAYER_THREATS_MAP;
  var entry=threatMap[team+"|"+p];
  return type==="assist"?entry.a:entry.g;
}
function normalizeOddsMarket(market,matchId){
  var co=COMPLETE_ODDS[matchId];
  return normalizeOddsMarket(options.oddsMarket,options.matchId);
}
"""
        embed.validate_runtime_integrations(source)

        with self.assertRaisesRegex(RuntimeError, "complete odds integration"):
            embed.validate_runtime_integrations(source.replace("COMPLETE_ODDS[matchId]", "null"))


if __name__ == "__main__":
    unittest.main()
