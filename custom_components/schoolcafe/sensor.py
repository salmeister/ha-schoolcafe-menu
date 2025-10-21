"""SchoolCafe menu sensor platform."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import SchoolCafeAPI, SchoolCafeAPIError
from .const import (
    DOMAIN,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    ATTR_SERVING_DATE,
    ATTR_CATEGORY,
    ATTR_SERVING_LINE,
    ATTR_CALORIES,
    ATTR_ALLERGENS,
    ATTR_RATING,
    ATTR_LIKES_PERCENTAGE,
    ATTR_THUMBNAIL_URL,
    ATTR_SERVING_SIZE,
    ATTR_INGREDIENTS,
    ATTR_NUTRITION,
    ATTR_IS_WEEKDAY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SchoolCafe sensor platform."""
    _LOGGER.debug("Setting up SchoolCafe sensor platform")

    api: SchoolCafeAPI = hass.data[DOMAIN][config_entry.entry_id]
    poll_interval: int = config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    # Create update coordinator
    coordinator = SchoolCafeDataUpdateCoordinator(
        hass=hass,
        api=api,
        update_interval=timedelta(minutes=poll_interval),
        entry_id=config_entry.entry_id,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Create sensor entities for each day and menu line combination
    entities = []
    
    for day_offset in range(api.days_to_fetch):
        target_date = datetime.now().date() + timedelta(days=day_offset)
        date_key = target_date.strftime("%Y-%m-%d")
        
        for menu_line in api.menu_lines:
            entity = SchoolCafeMenuSensor(
                coordinator=coordinator,
                config_entry=config_entry,
                api=api,
                menu_line=menu_line,
                day_offset=day_offset,
                date_key=date_key,
            )
            entities.append(entity)

    async_add_entities(entities, update_before_add=True)
    _LOGGER.debug("SchoolCafe sensor entities added successfully")


class SchoolCafeDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching SchoolCafe data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SchoolCafeAPI,
        update_interval: timedelta,
        entry_id: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry_id}",
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the SchoolCafe API."""
        try:
            _LOGGER.debug("Fetching data from SchoolCafe API")
            data = await self.api.get_menu_data()
            
            if data is None:
                _LOGGER.warning("No data received from SchoolCafe API")
                return self.data or {}
            
            _LOGGER.debug("Successfully fetched menu data for %d days", len(data))
            return data
            
        except SchoolCafeAPIError as e:
            _LOGGER.error("Error fetching data from SchoolCafe API: %s", e)
            raise UpdateFailed(f"Error communicating with SchoolCafe API: {e}") from e
        except Exception as e:
            _LOGGER.exception("Unexpected error fetching SchoolCafe data: %s", e)
            raise UpdateFailed(f"Unexpected error: {e}") from e


class SchoolCafeMenuSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SchoolCafe menu sensor."""

    _attr_icon = "mdi:food"

    def __init__(
        self,
        coordinator: SchoolCafeDataUpdateCoordinator,
        config_entry: ConfigEntry,
        api: SchoolCafeAPI,
        menu_line: str,
        day_offset: int,
        date_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._config_entry = config_entry
        self._api = api
        self._menu_line = menu_line
        self._day_offset = day_offset
        self._date_key = date_key
        
        # Generate unique ID and name
        school_id_short = api.school_id[:8]
        line_clean = menu_line.replace(" ", "_").lower()
        
        # Create suffix based on day offset (purely numeric for predictability)
        if day_offset == 0:
            day_suffix = "today"
        elif day_offset == 1:
            day_suffix = "tomorrow"
        else:
            day_suffix = f"today_plus{day_offset}"
            
        self._attr_unique_id = f"schoolcafe_{line_clean}_{day_suffix}"
        
        # Friendly name based on day offset
        if day_offset == 0:
            day_name = "Today"
        elif day_offset == 1:
            day_name = "Tomorrow"
        else:
            target_date = datetime.now().date() + timedelta(days=day_offset)
            day_name = f"Today +{day_offset} ({target_date.strftime('%A')})"
        
        self._attr_name = f"SchoolCafe {menu_line} {day_name}"
        
        _LOGGER.debug("Initialized SchoolCafe menu sensor: %s", self._attr_name)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data is not None
            and self._date_key in self.coordinator.data
        )

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if not self.available:
            return None
            
        menu_data = self.coordinator.data.get(self._date_key, {})
        menu_items = self._api.extract_menu_items_for_line(menu_data, self._menu_line)
        
        if not menu_items:
            return "No items available"
            
        return self._api.format_menu_description(menu_items)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.available:
            return {}
            
        menu_data = self.coordinator.data.get(self._date_key, {})
        menu_items = self._api.extract_menu_items_for_line(menu_data, self._menu_line)
        
        # Calculate if this is a weekday (Monday=0, Sunday=6)
        target_date = datetime.now().date() + timedelta(days=self._day_offset)
        is_weekday = target_date.weekday() < 5  # Monday(0) through Friday(4)
        
        attributes = {
            ATTR_SERVING_DATE: self._date_key,
            ATTR_CATEGORY: self._menu_line,
            ATTR_SERVING_LINE: self._api.serving_line,
            ATTR_IS_WEEKDAY: is_weekday,
            "school_id": self._api.school_id,
            "grade": self._api.grade,
            "meal_type": self._api.meal_type,
            "item_count": len(menu_items),
            "items": [],
        }
        
        # Add detailed information for each menu item
        for item in menu_items:
            item_info = {
                "description": item.get("MenuItemDescription", "Unknown Item"),
                "category": item.get("Category", ""),
                ATTR_SERVING_SIZE: item.get("ServingSizeByGrade", item.get("DefaultServingSize", "")),
                ATTR_CALORIES: item.get("Calories", 0),
                ATTR_RATING: item.get("MyRating", 0),
                ATTR_LIKES_PERCENTAGE: item.get("LikesPercentage", 0),
                ATTR_THUMBNAIL_URL: item.get("ThumbnailImageURL", ""),
                ATTR_ALLERGENS: self._api.get_allergen_info(item),
                ATTR_NUTRITION: self._api.get_nutrition_info(item),
                ATTR_INGREDIENTS: item.get("SubIngredientsDisplay", ""),
            }
            attributes["items"].append(item_info)
        
        return attributes

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        school_id_short = self._api.school_id[:8]
        
        return {
            "identifiers": {(DOMAIN, f"schoolcafe_{self._api.school_id}")},
            "name": f"SchoolCafe Menu ({school_id_short}...)",
            "manufacturer": "SchoolCafe",
            "model": "Menu Service",
            "configuration_url": "https://webapis.schoolcafe.com",
        }

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug("SchoolCafe sensor added to hass: %s", self._attr_unique_id)