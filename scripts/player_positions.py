"""Shared player-position normalization for ESPN squad data.

ESPN's World Cup roster feed exposes only G/D/M/F. Jersey numbers are not a
reliable source for distinguishing centre-backs from full-backs or attacking
midfielders from forwards, so the fallback deliberately stays conservative.
More specific positions should come from an explicit, reviewed data source.
"""

ESPN_POSITION_FALLBACK = {
    "G": "门将",
    "D": "中卫",
    "M": "中前卫",
    "F": "边锋",
}


def normalize_espn_position(position):
    """Map ESPN's coarse position code to the app's safest compatible role."""
    return ESPN_POSITION_FALLBACK.get(str(position or "").strip().upper(), "中前卫")
