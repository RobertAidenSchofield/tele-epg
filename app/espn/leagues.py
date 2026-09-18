import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.parser import ProgramData

logger = logging.getLogger(__name__)

# Channel name substring -> (sport, league) for ESPN API
# Order matters: more specific patterns should come first.
# Channel name substring -> (sport, league) for ESPN API
# Order matters: more specific patterns should come first.
LEAGUE_MAP: list[tuple[str, tuple[str, str]]] = [
    # Soccer - English & UK
    ("PREMIER LEAGUE",      ("soccer", "eng.1")),
    ("EPL",                 ("soccer", "eng.1")),
    ("CHAMPIONSHIP",        ("soccer", "eng.2")),
    ("EFL",                 ("soccer", "eng.2")),
    ("FA CUP",              ("soccer", "eng.fa")),
    ("CARABAO",             ("soccer", "eng.league_cup")),
    ("SCOTTISH",            ("soccer", "sco.1")),
    # Soccer - European Competitions
    ("CHAMPIONS LEAGUE",    ("soccer", "uefa.champions")),
    ("UCL",                 ("soccer", "uefa.champions")),
    ("EUROPA LEAGUE",       ("soccer", "uefa.europa")),
    ("CONFERENCE LEAGUE",   ("soccer", "uefa.europa.conf")),
    # Soccer - Top Continental Leagues
    ("LA LIGA",             ("soccer", "esp.1")),
    ("SERIE A",             ("soccer", "ita.1")),
    ("BUNDESLIGA",          ("soccer", "ger.1")),
    ("LIGUE 1",             ("soccer", "fra.1")),
    ("MLS",                 ("soccer", "usa.1")),
    ("LIGA MX",             ("soccer", "mex.1")),
    # American sports
    ("NFL",                 ("football", "nfl")),
    ("NBA",                 ("basketball", "nba")),
    ("WNBA",                ("basketball", "wnba")),
    ("MLB",                 ("baseball", "mlb")),
    ("NHL",                 ("hockey", "nhl")),
    ("COLLEGE FOOTBALL",    ("football", "college-football")),
    ("COLLEGE BASKETBALL",  ("basketball", "mens-college-basketball")),
    # Combat sports (verified site scoreboard leagues from Public-ESPN-API)
    ("UFC",                 ("mma", "ufc")),
    ("BELLATOR",            ("mma", "bellator")),
    ("PFL",                 ("mma", "pfl")),
    ("MMA",                 ("mma", "ufc")),
    # Racing
    ("FORMULA 1",           ("racing", "f1")),
    ("F1",                  ("racing", "f1")),
    ("NASCAR",              ("racing", "nascar-cup")),
]

# Keywords indicating a generic sports or event-based channel
GENERIC_CHANNEL_KEYWORDS: tuple[str, ...] = (
    "EVENT",
    "SPORT",
    "DAZN",
    "TNT",
    "SETANTA",
    "HBOMAX",
    "HBO MAX",
    "SN0",
    "SUPERSPORT",
    "BEIN",
    "STAN",
    "TSN",
    "FOXTEL",
    "OPTUS",
    "ESPN",
)

# Core in-season leagues queried when generic multi-sport channels are present
CORE_SPORTS_LEAGUES: list[tuple[str, str]] = [
    ("football", "nfl"),
    ("football", "college-football"),
    ("soccer", "eng.1"),
    ("soccer", "uefa.champions"),
    ("soccer", "esp.1"),
    ("soccer", "ita.1"),
    ("soccer", "ger.1"),
    ("baseball", "mlb"),
    ("basketball", "nba"),
    ("hockey", "nhl"),
    ("mma", "ufc"),
]

# Title-based detection hints
TITLE_SPORT_HINTS: list[tuple[str, tuple[str, str]]] = [
    ("UFC",     ("mma", "ufc")),
    ("BELLATOR",("mma", "bellator")),
    ("PFL",     ("mma", "pfl")),
    ("NFL",     ("football", "nfl")),
    ("NBA",     ("basketball", "nba")),
    ("MLB",     ("baseball", "mlb")),
    ("NHL",     ("hockey", "nhl")),
    ("MLS",     ("soccer", "usa.1")),
    ("NASCAR",  ("racing", "nascar-cup")),
    ("F1",      ("racing", "f1")),
]


def detect_leagues(programs: "list[ProgramData]") -> set[tuple[str, str]]:
    """Scan all programs and return the set of (sport, league) tuples to query.

    Detects specific leagues from channel names and titles, and automatically
    includes core major sports when generic event channels (e.g. DAZN, TNT Sports)
    are present.
    """
    leagues: set[tuple[str, str]] = set()
    has_generic_channels = False

    for prog in programs:
        channel_upper = prog.channel_name.upper()
        title_upper = prog.title.upper()

        # Check for specific channel patterns
        matched = False
        for pattern, league_tuple in LEAGUE_MAP:
            if pattern in channel_upper:
                leagues.add(league_tuple)
                matched = True
                break

        # Check for specific title hints
        for hint, league_tuple in TITLE_SPORT_HINTS:
            if hint in title_upper:
                leagues.add(league_tuple)
                matched = True
                break

        # Check if this program is on a generic multi-sport event channel
        if not matched and any(kw in channel_upper for kw in GENERIC_CHANNEL_KEYWORDS):
            has_generic_channels = True

    # If generic sports event channels exist, include core major leagues
    if has_generic_channels:
        leagues.update(CORE_SPORTS_LEAGUES)

    logger.info("Detected %d ESPN league(s) to query: %s", len(leagues), leagues)
    return leagues
