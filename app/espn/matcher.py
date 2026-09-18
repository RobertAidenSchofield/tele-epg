import logging
import re

from rapidfuzz import fuzz

from app.espn.client import ESPNEvent
from app.parser import ProgramData

logger = logging.getLogger(__name__)

# Common noise words to strip from team/event names before matching
_NOISE_WORDS = re.compile(
    r"\b(FC|CF|SC|AC|AS|SS|SV|SK|FK|CD|CA|RC|RCD|BSC|TSG|VfB|VfL|1\.)\b",
    re.IGNORECASE,
)
_SEPARATORS = re.compile(r"(?:\b(?:vs\.?|v\.?|at)\b|@)", re.IGNORECASE)
_EXTRA_SPACES = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Normalize an event name for fuzzy comparison."""
    text = text.lower()
    text = _NOISE_WORDS.sub("", text)
    text = _SEPARATORS.sub(" ", text)
    text = _EXTRA_SPACES.sub(" ", text).strip()
    return text


def find_best_match(
    program: ProgramData,
    espn_events: list[ESPNEvent],
    score_cutoff: int = 65,
    max_time_diff_hours: int = 48,
) -> ESPNEvent | None:
    """Find the ESPN event that best matches a parsed program.

    Args:
        program: The parsed program from Telegram.
        espn_events: List of ESPN events to match against.
        score_cutoff: Minimum fuzzy match score (0-100) to accept.
        max_time_diff_hours: Maximum time difference to consider a match.

    Returns:
        The best matching ESPNEvent, or None if no match found.
    """
    if not espn_events:
        return None

    normalized_title = _normalize(program.title)
    if not normalized_title:
        return None

    best_match: ESPNEvent | None = None
    best_score: float = 0

    for event in espn_events:
        # Time proximity filter - skip events too far from parsed time
        time_diff = abs(
            (event.start_time - program.start_time.astimezone(event.start_time.tzinfo)).total_seconds()
        )
        if time_diff > max_time_diff_hours * 3600:
            continue

        # Try matching against both name and short_name
        normalized_name = _normalize(event.name)
        normalized_short = _normalize(event.short_name)

        score_name = fuzz.token_set_ratio(normalized_title, normalized_name)
        score_short = fuzz.token_set_ratio(normalized_title, normalized_short)
        score = max(score_name, score_short)

        if score >= score_cutoff and score > best_score:
            best_score = score
            best_match = event

    if best_match:
        logger.debug(
            "Matched '%s' → '%s' (score=%.0f)",
            program.title,
            best_match.name,
            best_score,
        )

    return best_match
