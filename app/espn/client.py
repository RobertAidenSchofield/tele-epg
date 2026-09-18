import logging
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
NY_TZ = ZoneInfo("America/New_York")



@dataclass
class ESPNEvent:
    """A single event from the ESPN API."""
    espn_id: str
    name: str               # e.g. "Newcastle United at Leeds United"
    short_name: str          # e.g. "NEW @ LEE"
    start_time: datetime     # UTC, timezone-aware
    broadcast: str           # e.g. "USA Net", "ESPN"
    status: str              # "pre", "in", "post"
    sport: str = ""
    league_name: str = ""
    venue: str = ""
    summary_desc: str = ""
    icon_url: str = ""


def _parse_event(
    event_data: dict,
    sport: str = "",
    league_name: str = "",
    default_logo: str = "",
) -> ESPNEvent | None:
    """Parse a single event from ESPN API JSON response."""
    try:
        # Parse the UTC start time
        date_str = event_data.get("date", "")
        start_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        name = event_data.get("name", "")
        short_name = event_data.get("shortName", "")

        # Competitions info
        broadcast = ""
        status = "pre"
        venue_name = ""
        icon_url = default_logo

        competitions = event_data.get("competitions", [])
        if competitions:
            comp = competitions[0]

            # Broadcasts
            broadcasts = comp.get("broadcasts", [])
            if broadcasts:
                names = broadcasts[0].get("names", [])
                if names:
                    broadcast = names[0]

            # Status
            status_data = comp.get("status", {})
            type_data = status_data.get("type", {})
            status = type_data.get("state", "pre")

            # Venue
            venue_data = comp.get("venue", {})
            venue_name = venue_data.get("fullName", "")
            city = venue_data.get("address", {}).get("city")
            if venue_name and city:
                venue_str = f"{venue_name}, {city}"
            else:
                venue_str = venue_name

            # Team logos (prefer home team logo if available)
            for c in comp.get("competitors", []):
                logo = c.get("team", {}).get("logo", "")
                if logo:
                    icon_url = logo
                    if c.get("homeAway") == "home":
                        break

        # Build informative summary description
        desc_parts = []
        if league_name:
            desc_parts.append(league_name)
        if venue_str:
            desc_parts.append(f"Live from {venue_str}")
        if broadcast:
            desc_parts.append(f"Broadcast: {broadcast}")

        if desc_parts:
            summary_desc = f"{name} ({' | '.join(desc_parts)})"
        else:
            summary_desc = name

        return ESPNEvent(
            espn_id=str(event_data.get("id", "")),
            name=name,
            short_name=short_name,
            start_time=start_time,
            broadcast=broadcast,
            status=status,
            sport=sport,
            league_name=league_name,
            venue=venue_str,
            summary_desc=summary_desc,
            icon_url=icon_url,
        )
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("Failed to parse ESPN event: %s", e)
        return None


def fetch_espn_events(
    sport: str,
    league: str,
    days: int = 7,
) -> list[ESPNEvent]:
    """Fetch events from the ESPN scoreboard API for a given sport/league.

    Uses month-based querying (e.g. dates=YYYYMM) which is supported across
    all major ESPN sports on site v2, with a fallback to the default week scoreboard.

    Args:
        sport: ESPN sport slug (e.g. "soccer", "football")
        league: ESPN league slug (e.g. "eng.1", "nfl")
        days: Number of days in the window (centered on today)

    Returns:
        List of ESPNEvent objects, or empty list on failure.
    """
    today = datetime.now(NY_TZ)
    months = [today.strftime("%Y%m")]
    end_month = (today + timedelta(days=days)).strftime("%Y%m")
    if end_month != months[0]:
        months.append(end_month)

    url = f"{ESPN_BASE_URL}/{sport}/{league}/scoreboard"
    raw_events: list[dict] = []
    league_name = ""
    default_logo = ""

    # Fetch events for the month(s) covering the guide window
    for ym in months:
        logger.info("Fetching ESPN events: %s/%s for %s", sport, league, ym)
        try:
            response = requests.get(url, params={"dates": ym, "limit": 500}, timeout=15)
            response.raise_for_status()
            data = response.json()
            if not league_name:
                league_info = data.get("leagues", [{}])[0] if data.get("leagues") else {}
                league_name = league_info.get("name", "")
                logos = league_info.get("logos", [])
                default_logo = logos[0].get("href", "") if logos else ""
            raw_events.extend(data.get("events", []))
        except Exception as e:
            logger.warning("ESPN API month request failed for %s/%s (%s): %s", sport, league, ym, e)

    # Fallback to default (current week/round) if month queries returned nothing
    if not raw_events:
        logger.info("Falling back to default scoreboard call for %s/%s", sport, league)
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            if not league_name:
                league_info = data.get("leagues", [{}])[0] if data.get("leagues") else {}
                league_name = league_info.get("name", "")
                logos = league_info.get("logos", [])
                default_logo = logos[0].get("href", "") if logos else ""
            raw_events.extend(data.get("events", []))
        except Exception as e:
            logger.warning("ESPN API fallback request failed for %s/%s: %s", sport, league, e)
            return []

    # Parse and deduplicate events by id
    events: list[ESPNEvent] = []
    seen_ids: set[str] = set()

    for event_data in raw_events:
        eid = str(event_data.get("id", ""))
        if eid and eid in seen_ids:
            continue
        event = _parse_event(
            event_data,
            sport=sport,
            league_name=league_name,
            default_logo=default_logo,
        )
        if event is not None:
            if eid:
                seen_ids.add(eid)
            events.append(event)

    logger.info("Fetched %d events from ESPN %s/%s", len(events), sport, league)
    return events
