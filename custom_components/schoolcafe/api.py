"""SchoolCafe API client for Home Assistant integration."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp
from aiohttp import ClientTimeout, ClientError

from .const import (
    SCHOOLCAFE_API_BASE,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
)

_VIEW_ID_RE = re.compile(
    r"(?:[?&]viewid=)([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
    re.IGNORECASE,
)

_LOGGER = logging.getLogger(__name__)


class SchoolCafeAPIError(Exception):
    """Base exception for SchoolCafe API errors."""


class SchoolCafeConnectionError(SchoolCafeAPIError):
    """Connection error."""


class SchoolCafeDataError(SchoolCafeAPIError):
    """Data parsing error."""


def extract_view_id(value: str) -> Optional[str]:
    """Return a viewID from a public SchoolCafe menu URL."""
    if not value:
        return None
    match = _VIEW_ID_RE.search(value.strip())
    return match.group(1) if match else None


def looks_like_public_menu(value: str) -> bool:
    """Return True when the value is a guest menu link rather than a school id."""
    if not value:
        return False
    lowered = value.strip().lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or "schoolcafe.com" in lowered
        or "viewid=" in lowered
    )


def format_serving_line(serving_line: str) -> str:
    """Join one or more serving lines the way the menu API expects."""
    parts: List[str] = []
    for part in re.split(r"[,~]", serving_line or ""):
        cleaned = part.strip()
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    return "~".join(parts) if parts else "Main Line"


def menu_has_items(menu_data: Any) -> bool:
    """Return True when a menu payload contains at least one item."""
    if not isinstance(menu_data, dict):
        return False
    return any(isinstance(items, list) and items for items in menu_data.values())


class SchoolCafeAPI:
    """Class to interact with the SchoolCafe API."""

    def __init__(
        self,
        school_id: str,
        grade: str = "09",
        meal_type: str = "Lunch",
        serving_line: str = "Main Line",
        person_id: Optional[str] = None,
        menu_lines: Optional[List[str]] = None,
        days_to_fetch: int = 7,
        timeout: int = DEFAULT_TIMEOUT,
        view_id: Optional[str] = None,
        menu_url: Optional[str] = None,
        school_name: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        """Initialize the SchoolCafe API client."""
        self.school_id = school_id
        self.school_name = school_name
        self.view_id = view_id
        self.menu_url = menu_url
        self.grade = grade
        self.meal_type = meal_type
        self.serving_line = format_serving_line(serving_line)
        self.person_id = person_id or "null"
        self.menu_lines = menu_lines or ["BLUE LINE", "GOLD LINE"]
        self.days_to_fetch = days_to_fetch
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = session
        # Only close sessions we created; a shared HA session must stay open.
        self._owns_session = session is None
        self._reported_unknown_school = False
        # Dates whose fetch failed on the last run (callers keep prior data for them).
        self.last_failed_dates: List[str] = []
        # Callable returning today's local date; set by the integration to dt_util.
        self.today_provider = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._owns_session = True
            timeout = ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(ssl=True, limit=10),
            )
            _LOGGER.debug("Created new aiohttp session")
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    def _format_date(self, date: datetime) -> str:
        """Format date for SchoolCafe API (MM/DD/YYYY)."""
        return date.strftime("%m/%d/%Y")

    def _build_api_url(self, serving_date: datetime) -> str:
        """Build the API URL for a specific serving date."""
        date_str = quote(self._format_date(serving_date))
        serving_line_encoded = quote(self.serving_line)
        meal_type_encoded = quote(self.meal_type)
        
        url = (
            f"{SCHOOLCAFE_API_BASE}/CalendarView/GetDailyMenuitemsByGrade"
            f"?SchoolId={quote(self.school_id)}"
            f"&ServingDate={date_str}"
            f"&ServingLine={serving_line_encoded}"
            f"&MealType={meal_type_encoded}"
            f"&Grade={quote(self.grade)}"
            f"&PersonId={self.person_id}"
        )
        
        return url

    async def _request_json(self, url: str) -> Any:
        """GET a URL and return decoded JSON, unwrapping double-encoded payloads.

        Retries timeouts, connection errors, 429 and 5xx responses with
        exponential backoff. Other 4xx responses fail immediately.
        """
        last_err: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            delay = RETRY_DELAY * (2 ** (attempt - 1))
            try:
                session = await self._get_session()
                async with session.get(
                    url, timeout=ClientTimeout(total=self.timeout)
                ) as response:
                    _LOGGER.debug("Attempt %d: %s -> %s", attempt, url, response.status)

                    if response.status == 404:
                        return None
                    if response.status != 200:
                        error_text = (await response.text())[:300]
                        last_err = SchoolCafeConnectionError(
                            f"HTTP error {response.status}: {error_text}"
                        )
                        retryable = response.status == 429 or response.status >= 500
                        if retryable and attempt < MAX_RETRIES:
                            _LOGGER.warning(
                                "SchoolCafe HTTP %d (attempt %d/%d), retrying in %ss",
                                response.status, attempt, MAX_RETRIES, delay,
                            )
                            await asyncio.sleep(delay)
                            continue
                        raise last_err

                    try:
                        payload = await response.json(content_type=None)
                    except Exception as err:
                        raise SchoolCafeDataError(f"Invalid JSON response: {err}") from err

                    if isinstance(payload, str):
                        payload = payload.strip()
                        if not payload:
                            return None
                        try:
                            payload = json.loads(payload)
                        except json.JSONDecodeError:
                            return payload
                    return payload

            except (ClientError, asyncio.TimeoutError) as err:
                last_err = err
                if attempt < MAX_RETRIES:
                    _LOGGER.warning(
                        "SchoolCafe request failed (attempt %d/%d): %s, retrying in %ss",
                        attempt, MAX_RETRIES, repr(err), delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise SchoolCafeConnectionError(
                    f"Connection failed after {MAX_RETRIES} attempts: {err!r}"
                ) from err

        raise SchoolCafeAPIError(
            f"Failed to retrieve data after {MAX_RETRIES} attempts: {last_err}"
        )

    async def get_menu_bookmark(self, view_id: str) -> Optional[Dict[str, Any]]:
        """Resolve a public guest menu link to the school and filters it was saved with."""
        url = f"{SCHOOLCAFE_API_BASE}/GetMenuBookmarkURL?viewID={quote(view_id)}"
        payload = await self._request_json(url)
        if isinstance(payload, dict) and (payload.get("school") or {}).get("id"):
            return payload
        return None

    async def refresh_school_from_bookmark(self) -> None:
        """Update the school id from the public menu link when one is configured."""
        if not self.view_id:
            return

        bookmark = await self.get_menu_bookmark(self.view_id)
        if not bookmark:
            _LOGGER.warning(
                "Public menu link %s did not resolve to a school. Keeping school id %s.",
                self.view_id,
                self.school_id,
            )
            return

        school = bookmark["school"]
        resolved_id = school["id"]
        if resolved_id != self.school_id:
            _LOGGER.info(
                "Public menu link resolved school %s to %s",
                self.school_id,
                resolved_id,
            )
        self.school_id = resolved_id
        if school.get("name"):
            self.school_name = school["name"]

    async def get_service_lines(self, start_date: datetime.date, end_date: datetime.date) -> List[Dict[str, Any]]:
        """Return serving lines published for this school and meal."""
        url = (
            f"{SCHOOLCAFE_API_BASE}/GetServiceLine"
            f"?schoolid={quote(self.school_id)}"
            f"&startdate={quote(start_date.strftime('%m/%d/%Y'))}"
            f"&enddate={quote(end_date.strftime('%m/%d/%Y'))}"
            f"&mealtype={quote(self.meal_type)}"
        )
        payload = await self._request_json(url)
        if isinstance(payload, list):
            return payload
        return []

    @classmethod
    async def resolve_public_menu(cls, identifier: str) -> Optional[Dict[str, Any]]:
        """Resolve a public menu URL to a school id and saved filters."""
        view_id = extract_view_id(identifier)
        if not view_id:
            return None

        api = cls(school_id=view_id, view_id=view_id, menu_url=identifier.strip())
        try:
            bookmark = await api.get_menu_bookmark(view_id)
        finally:
            await api.close()

        if not bookmark:
            return None

        school = bookmark["school"]
        lines = bookmark.get("servingLine") or []
        if isinstance(lines, str):
            lines = [lines]

        return {
            "school_id": school["id"],
            "school_name": school.get("name"),
            "view_id": view_id,
            "menu_url": identifier.strip(),
            "grade": bookmark.get("grade"),
            "meal_type": bookmark.get("mealType"),
            "serving_line": format_serving_line("~".join(lines)) if lines else None,
        }

    async def test_connection(self) -> bool:
        """Test the connection to SchoolCafe API."""
        try:
            await self.refresh_school_from_bookmark()
            await self.get_menu_for_date(self._today())
            _LOGGER.debug("Connection test successful")
            return True
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            raise SchoolCafeConnectionError(f"Connection test failed: {err}") from err

    async def get_menu_for_date(self, serving_date: datetime.date) -> Dict[str, Any]:
        """
        Get menu data for a specific date.
        
        Args:
            serving_date: The date to get menu data for
            
        Returns:
            Dictionary containing menu data for all categories
            
        Raises:
            SchoolCafeAPIError: If the request fails
        """
        url = self._build_api_url(datetime.combine(serving_date, datetime.min.time()))
        _LOGGER.debug("Requesting menu data from: %s", url)
        payload = await self._request_json(url)
        if not isinstance(payload, dict):
            _LOGGER.debug("No menu data found for date: %s", serving_date)
            return {}
        _LOGGER.debug("Successfully retrieved menu data for %s", serving_date)
        return payload

    def _today(self):
        """Return today's date in HA's configured time zone."""
        if self.today_provider is not None:
            return self.today_provider()
        return datetime.now().date()

    async def get_menu_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get menu data for the configured number of days.
        
        Returns:
            Dictionary with date strings as keys and menu data as values
        """
        await self.refresh_school_from_bookmark()
        results = await self._fetch_menu_range()
        if self._range_has_items(results):
            return results

        probe = self._first_weekday()
        if probe is None:
            return results

        await self._adopt_published_serving_lines(probe)
        if self._reported_unknown_school:
            return results
        return await self._fetch_menu_range()

    async def _fetch_menu_range(self) -> Dict[str, Dict[str, Any]]:
        """Fetch menu payloads for each configured day."""
        results = {}
        failed: List[str] = []
        today = self._today()

        for i in range(self.days_to_fetch):
            target_date = today + timedelta(days=i)
            date_key = target_date.strftime("%Y-%m-%d")

            try:
                menu_data = await self.get_menu_for_date(target_date)
                results[date_key] = menu_data
                _LOGGER.debug("Retrieved menu data for %s", date_key)
            except Exception as err:
                _LOGGER.warning("Failed to get menu data for %s: %s", date_key, err)
                failed.append(date_key)

        self.last_failed_dates = failed
        if failed and len(failed) == self.days_to_fetch:
            raise SchoolCafeConnectionError(
                f"All {self.days_to_fetch} menu requests failed"
            )
        return results

    def _first_weekday(self) -> Optional[datetime.date]:
        """Return the first weekday in the fetch window."""
        today = self._today()
        for offset in range(self.days_to_fetch):
            target_date = today + timedelta(days=offset)
            if target_date.weekday() < 5:
                return target_date
        return None

    def _range_has_items(self, results: Dict[str, Dict[str, Any]]) -> bool:
        """Return True when any fetched day includes menu items."""
        return any(menu_has_items(menu_data) for menu_data in results.values())

    async def _adopt_published_serving_lines(self, probe: datetime.date) -> None:
        """Switch to the lines SchoolCafe actually publishes when the configured line is empty."""
        try:
            published = await self.get_service_lines(probe, probe)
        except SchoolCafeAPIError as err:
            _LOGGER.debug("Serving line lookup failed: %s", err)
            return

        names: List[str] = []
        for line in published:
            name = (line.get("ServingLineDescription") or "").strip()
            if name and name not in names:
                names.append(name)

        if not names:
            if not self._reported_unknown_school:
                self._reported_unknown_school = True
                _LOGGER.warning(
                    "SchoolCafe returned no menu and no serving lines for school %s. "
                    "The school id is no longer recognized. Open the integration options "
                    "and paste the public guest menu URL (the link that contains viewID).",
                    self.school_id,
                )
            return

        configured = {
            part.strip().lower()
            for part in re.split(r"[,~]", self.serving_line)
            if part.strip()
        }
        published_names = {name.lower() for name in names}
        if configured and configured.issubset(published_names):
            _LOGGER.debug(
                "SchoolCafe published lines for %s but none of the fetched days had menu items",
                self.school_id,
            )
            self._reported_unknown_school = True
            return

        updated = format_serving_line("~".join(names))
        _LOGGER.info(
            "Serving line %r is not published for this school. Requesting %s instead.",
            self.serving_line,
            updated,
        )
        self.serving_line = updated

    def extract_menu_items_for_line(self, menu_data: Dict[str, Any], line: str) -> List[Dict[str, Any]]:
        """
        Extract menu items for a specific menu line.
        
        Args:
            menu_data: Raw menu data from API
            line: Menu line name (e.g., "BLUE LINE", "GOLD LINE")
            
        Returns:
            List of menu items for the specified line
        """
        return menu_data.get(line, [])

    def format_menu_description(self, menu_items: List[Dict[str, Any]]) -> str:
        """
        Format menu items into a readable description.
        
        Args:
            menu_items: List of menu item dictionaries
            
        Returns:
            Formatted string description of menu items
        """
        if not menu_items:
            return "No items available"
            
        descriptions = []
        for item in menu_items:
            desc = item.get("MenuItemDescription", "Unknown Item")
            descriptions.append(desc)
            
        return ", ".join(descriptions)

    def get_nutrition_info(self, menu_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract nutrition information from a menu item.
        
        Args:
            menu_item: Menu item dictionary
            
        Returns:
            Dictionary with nutrition information
        """
        return {
            "calories": menu_item.get("Calories", 0),
            "total_fat": menu_item.get("TotalFat", 0.0),
            "carbs": menu_item.get("Carbs", 0.0),
            "protein": menu_item.get("Protein", 0),
        }

    def get_allergen_info(self, menu_item: Dict[str, Any]) -> List[str]:
        """
        Extract allergen information from a menu item.
        
        Args:
            menu_item: Menu item dictionary
            
        Returns:
            List of allergen strings
        """
        allergens_str = menu_item.get("Allergens", "")
        if allergens_str:
            return [allergen.strip() for allergen in allergens_str.split(",")]
        return []