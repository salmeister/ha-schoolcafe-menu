"""SchoolCafe API client for Home Assistant integration."""
from __future__ import annotations

import asyncio
import logging
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

_LOGGER = logging.getLogger(__name__)


class SchoolCafeAPIError(Exception):
    """Base exception for SchoolCafe API errors."""


class SchoolCafeConnectionError(SchoolCafeAPIError):
    """Connection error."""


class SchoolCafeDataError(SchoolCafeAPIError):
    """Data parsing error."""


class SchoolCafeAPI:
    """Class to interact with the SchoolCafe API."""

    def __init__(
        self,
        school_id: str,
        grade: str = "09",
        meal_type: str = "Lunch",
        serving_line: str = "Main Lines",
        person_id: Optional[str] = None,
        menu_lines: Optional[List[str]] = None,
        days_to_fetch: int = 7,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the SchoolCafe API client."""
        self.school_id = school_id
        self.grade = grade
        self.meal_type = meal_type
        self.serving_line = serving_line
        self.person_id = person_id or "null"
        self.menu_lines = menu_lines or ["BLUE LINE", "GOLD LINE"]
        self.days_to_fetch = days_to_fetch
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(ssl=True, limit=10),
            )
            _LOGGER.debug("Created new aiohttp session")
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
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
            f"?SchoolId={self.school_id}"
            f"&ServingDate={date_str}"
            f"&ServingLine={serving_line_encoded}"
            f"&MealType={meal_type_encoded}"
            f"&Grade={self.grade}"
            f"&PersonId={self.person_id}"
        )
        
        return url

    async def test_connection(self) -> bool:
        """Test the connection to SchoolCafe API."""
        try:
            # Test with today's date
            today = datetime.now().date()
            menu_data = await self.get_menu_for_date(today)
            
            # If we get data back (even if empty), connection is working
            _LOGGER.debug("Connection test successful")
            return True
            
        except Exception as e:
            _LOGGER.error("Connection test failed: %s", e)
            raise SchoolCafeConnectionError(f"Connection test failed: {e}") from e

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
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                session = await self._get_session()
                async with session.get(url) as response:
                    _LOGGER.debug("Attempt %d: Response status: %s", attempt, response.status)
                    
                    if response.status == 404:
                        _LOGGER.warning("No menu data found for date: %s", serving_date)
                        return {}
                    elif response.status != 200:
                        error_text = await response.text()
                        _LOGGER.warning("HTTP error %d: %s", response.status, error_text)
                        if attempt < MAX_RETRIES:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        raise SchoolCafeConnectionError(
                            f"HTTP error {response.status}: {error_text}"
                        )
                    
                    try:
                        response_json = await response.json()
                        _LOGGER.debug("Successfully retrieved menu data for %s", serving_date)
                        return response_json
                    except Exception as e:
                        raise SchoolCafeDataError(f"Invalid JSON response: {e}") from e
                        
            except ClientError as e:
                if attempt < MAX_RETRIES:
                    _LOGGER.warning(
                        "Attempt %d failed with connection error: %s, retrying...", 
                        attempt, e
                    )
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                else:
                    raise SchoolCafeConnectionError(
                        f"Connection failed after {MAX_RETRIES} attempts: {e}"
                    ) from e
        
        raise SchoolCafeAPIError(f"Failed to retrieve data after {MAX_RETRIES} attempts")

    async def get_menu_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get menu data for the configured number of days.
        
        Returns:
            Dictionary with date strings as keys and menu data as values
        """
        results = {}
        today = datetime.now().date()
        
        for i in range(self.days_to_fetch):
            target_date = today + timedelta(days=i)
            date_key = target_date.strftime("%Y-%m-%d")
            
            try:
                menu_data = await self.get_menu_for_date(target_date)
                results[date_key] = menu_data
                _LOGGER.debug("Retrieved menu data for %s", date_key)
            except Exception as e:
                _LOGGER.warning("Failed to get menu data for %s: %s", date_key, e)
                results[date_key] = {}
        
        return results

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