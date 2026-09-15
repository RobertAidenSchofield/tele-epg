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

    Args:
        sport: ESPN sport slug (e.g. "soccer", "football")
        league: ESPN league slug (e.g. "eng.1", "nfl")
        days: Number of days to fetch (centered on today)

    Returns:
        List of ESPNEvent objects, or empty list on failure.
    """
    today = datetime.now(NY_TZ)
    start_date = (today - timedelta(days=1)).strftime("%Y%m%d")
    end_date = (today + timedelta(days=days)).strftime("%Y%m%d")

    url = f"{ESPN_BASE_URL}/{sport}/{league}/scoreboard"
    params = {
        "dates": f"{start_date}-{end_date}",
        "limit": 200,
    }

    logger.info("Fetching ESPN events: %s/%s (%s to %s)", sport, league, start_date, end_date)

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning("ESPN API request failed for %s/%s: %s", sport, league, e)
        return []
    except ValueError as e:
        logger.warning("ESPN API returned invalid JSON for %s/%s: %s", sport, league, e)
        return []

    events = []
    league_info = data.get("leagues", [{}])[0] if data.get("leagues") else {}
    league_name = league_info.get("name", "")
    logos = league_info.get("logos", [])
    default_logo = logos[0].get("href", "") if logos else ""

    for event_data in data.get("events", []):
        event = _parse_event(
            event_data,
            sport=sport,
            league_name=league_name,
            default_logo=default_logo,
        )
        if event is not None:
            events.append(event)

    logger.info("Fetched %d events from ESPN %s/%s", len(events), sport, league)
    return events
