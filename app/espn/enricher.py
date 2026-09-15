import logging
from dataclasses import replace
from zoneinfo import ZoneInfo

from app.parser import ProgramData
from app.espn.client import ESPNEvent, fetch_espn_events
from app.espn.leagues import detect_leagues
from app.espn.matcher import find_best_match

logger = logging.getLogger(__name__)
NY_TZ = ZoneInfo("America/New_York")


def enrich_programs(programs: list[ProgramData]) -> list[ProgramData]:
    """Enrich parsed programs with accurate times from ESPN.

    Cross-references each program against ESPN's public scoreboard API
    using fuzzy title matching. When a match is found, the program's
    start_time is replaced with ESPN's exact UTC time (converted to NY).

    Programs that don't match any ESPN event keep their original times.
    If the ESPN API is unavailable, all programs are returned unchanged.

    Args:
        programs: List of parsed ProgramData from Telegram.

    Returns:
        A new list of ProgramData with enriched times where possible.
    """
    if not programs:
        return programs

    # 1. Detect which leagues to query based on channel names
    leagues = detect_leagues(programs)
    if not leagues:
        logger.info("No ESPN-supported leagues detected. Skipping enrichment.")
        return list(programs)

    # 2. Fetch ESPN events for each detected league
    all_espn_events: list[ESPNEvent] = []
    for sport, league in leagues:
        events = fetch_espn_events(sport, league)
        all_espn_events.extend(events)

    if not all_espn_events:
        logger.warning("No ESPN events fetched. Skipping enrichment.")
        return list(programs)

    logger.info(
        "Enriching %d programs against %d ESPN events",
        len(programs),
        len(all_espn_events),
    )

    # 3. Match and enrich each program
    enriched: list[ProgramData] = []
    matched_count = 0

    for prog in programs:
        match = find_best_match(prog, all_espn_events)
        if match is not None:
            # Replace start_time with ESPN's exact time, converted to NY
            espn_time_ny = match.start_time.astimezone(NY_TZ)
            enriched_prog = replace(
                prog,
                start_time=espn_time_ny,
                # Clear stop_time so the generator can re-infer it
                stop_time=None if prog.stop_time is None else prog.stop_time,
                desc=match.summary_desc or prog.desc,
                icon_url=match.icon_url or prog.icon_url,
                sport=match.sport or prog.sport,
            )
            enriched.append(enriched_prog)
            matched_count += 1
            logger.info(
                "Enriched: '%s' on [%s] — %s → %s",
                prog.title,
                prog.channel_name,
                prog.start_time.strftime("%Y-%m-%d %H:%M %Z"),
                espn_time_ny.strftime("%Y-%m-%d %H:%M %Z"),
            )
        else:
            enriched.append(prog)

    logger.info(
        "ESPN enrichment complete: %d/%d programs matched",
        matched_count,
        len(programs),
    )
    return enriched
