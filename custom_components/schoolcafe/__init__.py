"""
Custom integration to integrate SchoolCafe menu with Home Assistant.

For more details about this integration, please refer to
https://github.com/salmeister/ha-schoolcafe-menu
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .api import SchoolCafeAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


def _combined_config(entry: ConfigEntry) -> dict:
    """Merge entry data with options. Options win when both are set."""
    combined = dict(entry.data)
    combined.update(entry.options)
    return combined


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SchoolCafe from a config entry."""
    config = _combined_config(entry)

    # Validate required configuration
    required_fields = ["school_id"]
    missing_fields = [field for field in required_fields if not config.get(field)]
    
    if missing_fields:
        _LOGGER.error("Missing required configuration fields: %s", missing_fields)
        raise ConfigEntryError(f"Missing configuration fields: {missing_fields}")

    # Initialize the API object
    api = SchoolCafeAPI(
        school_id=config["school_id"],
        grade=config.get("grade", "09"),
        meal_type=config.get("meal_type", "Lunch"),
        serving_line=config.get("serving_line", "Main Line"),
        person_id=config.get("person_id"),
        menu_lines=config.get("menu_lines", ["BLUE LINE", "GOLD LINE"]),
        days_to_fetch=config.get("days_to_fetch", 7),
        view_id=config.get("view_id"),
        menu_url=config.get("menu_url"),
        school_name=config.get("school_name"),
    )

    # Test the connection
    try:
        await api.test_connection()
        _LOGGER.info("Successfully connected to SchoolCafe API")
    except Exception as e:
        _LOGGER.error("Failed to connect to SchoolCafe API: %s", e)
        await api.close()
        raise ConfigEntryError(f"Cannot connect to SchoolCafe: {e}") from e

    # Store the API instance in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = api

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Clean up API connection
        api = hass.data[DOMAIN].get(entry.entry_id)
        if api:
            await api.close()
        
        # Remove data
        hass.data[DOMAIN].pop(entry.entry_id, None)
        
        # Remove domain data if no entries left
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
    
    return unload_ok
