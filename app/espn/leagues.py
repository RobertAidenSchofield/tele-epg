import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.parser import ProgramData

logger = logging.getLogger(__name__)

# Channel name substring -> (sport, league) for ESPN API
# Order matters: more specific patterns should come first.
LEAGUE_MAP: list[tuple[str, tuple[str, str]]] = [
    # Soccer - English
    ("PREMIER LEAGUE",      ("soccer", "eng.1")),
    ("EFL",                 ("soccer", "eng.2")),
    ("FA CUP",              ("soccer", "eng.fa")),
    ("CARABAO",             ("soccer", "eng.league_cup")),
    # Soccer - European
    ("CHAMPIONS LEAGUE",    ("soccer", "uefa.champions")),
    ("EUROPA LEAGUE",       ("soccer", "uefa.europa")),
    ("CONFERENCE LEAGUE",   ("soccer", "uefa.europa.conf")),
    # Soccer - Other top leagues
    ("LA LIGA",             ("soccer", "esp.1")),
    ("SERIE A",             ("soccer", "ita.1")),
    ("BUNDESLIGA",          ("soccer", "ger.1")),
    ("LIGUE 1",             ("soccer", "fra.1")),
    ("MLS",                 ("soccer", "usa.1")),
    ("LIGA MX",             ("soccer", "mex.1")),
    ("SCOTTISH",            ("soccer", "sco.1")),
    # American sports
    ("NFL",                 ("football", "nfl")),
    ("NBA",                 ("basketball", "nba")),
    ("MLB",                 ("baseball", "mlb")),
    ("NHL",                 ("hockey", "nhl")),
    ("COLLEGE FOOTBALL",    ("football", "college-football")),
    ("COLLEGE BASKETBALL",  ("basketball", "mens-college-basketball")),
    # Combat sports
    ("UFC",                 ("mma", "ufc")),
    ("BOXING",              ("boxing", "boxing")),
]

# Title-based detection for generic channels like ESPN+
TITLE_SPORT_HINTS: list[tuple[str, tuple[str, str]]] = [
    ("UFC",     ("mma", "ufc")),
    ("NFL",     ("football", "nfl")),
    ("NBA",     ("basketball", "nba")),
    ("MLB",     ("baseball", "mlb")),
    ("NHL",     ("hockey", "nhl")),
    ("MLS",     ("soccer", "usa.1")),
]


def detect_leagues(programs: "list[ProgramData]") -> set[tuple[str, str]]:
    """Scan all programs and return the set of (sport, league) tuples to query.

    Detects leagues from channel names first, then falls back to title hints
    for generic channels like ESPN+.
    """
    leagues: set[tuple[str, str]] = set()

    for prog in programs:
        channel_upper = prog.channel_name.upper()
        title_upper = prog.title.upper()

        # Try channel name first
        matched = False
        for pattern, league_tuple in LEAGUE_MAP:
            if pattern in channel_upper:
                leagues.add(league_tuple)
                matched = True
                break

        # For generic channels (ESPN+, etc.), try title hints
        if not matched:
            for hint, league_tuple in TITLE_SPORT_HINTS:
                if hint in title_upper or hint in channel_upper:
                    leagues.add(league_tuple)
                    break

    logger.info("Detected %d ESPN league(s) to query: %s", len(leagues), leagues)
    return leagues
