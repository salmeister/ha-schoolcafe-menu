"""Config flow for SchoolCafe integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import SchoolCafeAPI, SchoolCafeAPIError
from .const import (
    DOMAIN,
    CONF_SCHOOL_ID,
    CONF_GRADE,
    CONF_MEAL_TYPE,
    CONF_SERVING_LINE,
    CONF_PERSON_ID,
    CONF_MENU_LINES,
    CONF_DAYS_TO_FETCH,
    CONF_POLL_INTERVAL,
    DEFAULT_GRADE,
    DEFAULT_MEAL_TYPE,
    DEFAULT_SERVING_LINE,
    DEFAULT_MENU_LINES,
    DEFAULT_DAYS_TO_FETCH,
    DEFAULT_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
    MAX_POLL_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCHOOL_ID): str,
        vol.Optional(CONF_GRADE, default=DEFAULT_GRADE): str,
        vol.Optional(CONF_MEAL_TYPE, default=DEFAULT_MEAL_TYPE): str,
        vol.Optional(CONF_SERVING_LINE, default=DEFAULT_SERVING_LINE): str,
        vol.Optional(CONF_PERSON_ID): str,
    }
)

STEP_ADVANCED_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MENU_LINES, default=", ".join(DEFAULT_MENU_LINES)): str,
        vol.Optional(CONF_DAYS_TO_FETCH, default=DEFAULT_DAYS_TO_FETCH): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=30)
        ),
        vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Process menu lines from comma-separated string to list
    menu_lines_str = data.get(CONF_MENU_LINES, ", ".join(DEFAULT_MENU_LINES))
    menu_lines = [line.strip().upper() for line in menu_lines_str.split(",") if line.strip()]
    
    if not menu_lines:
        menu_lines = DEFAULT_MENU_LINES

    api = SchoolCafeAPI(
        school_id=data[CONF_SCHOOL_ID],
        grade=data.get(CONF_GRADE, DEFAULT_GRADE),
        meal_type=data.get(CONF_MEAL_TYPE, DEFAULT_MEAL_TYPE),
        serving_line=data.get(CONF_SERVING_LINE, DEFAULT_SERVING_LINE),
        person_id=data.get(CONF_PERSON_ID),
        menu_lines=menu_lines,
        days_to_fetch=data.get(CONF_DAYS_TO_FETCH, DEFAULT_DAYS_TO_FETCH),
    )

    try:
        await api.test_connection()
    except SchoolCafeAPIError as e:
        _LOGGER.error("Cannot connect to SchoolCafe API: %s", e)
        raise CannotConnect from e
    except Exception as e:
        _LOGGER.exception("Unexpected error connecting to SchoolCafe API: %s", e)
        raise CannotConnect from e
    finally:
        await api.close()

    # Return processed data
    processed_data = data.copy()
    processed_data[CONF_MENU_LINES] = menu_lines
    
    return {"title": f"SchoolCafe ({data[CONF_SCHOOL_ID][:8]}...)", "data": processed_data}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SchoolCafe."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: Dict[str, Any] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Store user input for the next step
                self._user_input.update(user_input)
                
                # Check if this school_id is already configured
                await self.async_set_unique_id(user_input[CONF_SCHOOL_ID])
                self._abort_if_unique_id_configured()
                
                # Move to advanced options step
                return await self.async_step_advanced()
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidSchoolId:
                errors[CONF_SCHOOL_ID] = "invalid_school_id"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_advanced(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the advanced options step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Combine all user input
                self._user_input.update(user_input)
                
                # Validate the complete configuration
                info = await validate_input(self.hass, self._user_input)
                
                return self.async_create_entry(title=info["title"], data=info["data"])
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidMenuLines:
                errors[CONF_MENU_LINES] = "invalid_menu_lines"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="advanced",
            data_schema=STEP_ADVANCED_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, user_input: Dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for SchoolCafe integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Process menu lines from comma-separated string to list
                menu_lines_str = user_input.get(CONF_MENU_LINES, ", ".join(DEFAULT_MENU_LINES))
                menu_lines = [line.strip().upper() for line in menu_lines_str.split(",") if line.strip()]
                
                if not menu_lines:
                    menu_lines = DEFAULT_MENU_LINES
                
                # Update the processed menu lines
                user_input[CONF_MENU_LINES] = menu_lines
                
                return self.async_create_entry(title="", data=user_input)
                
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Get current config values
        current_config = self.config_entry.data
        menu_lines_str = ", ".join(current_config.get(CONF_MENU_LINES, DEFAULT_MENU_LINES))
        
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_GRADE,
                    default=current_config.get(CONF_GRADE, DEFAULT_GRADE)
                ): str,
                vol.Optional(
                    CONF_MEAL_TYPE,
                    default=current_config.get(CONF_MEAL_TYPE, DEFAULT_MEAL_TYPE)
                ): str,
                vol.Optional(
                    CONF_SERVING_LINE,
                    default=current_config.get(CONF_SERVING_LINE, DEFAULT_SERVING_LINE)
                ): str,
                vol.Optional(
                    CONF_PERSON_ID,
                    default=current_config.get(CONF_PERSON_ID, "")
                ): str,
                vol.Optional(
                    CONF_MENU_LINES,
                    default=menu_lines_str
                ): str,
                vol.Optional(
                    CONF_DAYS_TO_FETCH,
                    default=current_config.get(CONF_DAYS_TO_FETCH, DEFAULT_DAYS_TO_FETCH)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
                vol.Optional(
                    CONF_POLL_INTERVAL,
                    default=current_config.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidSchoolId(HomeAssistantError):
    """Error to indicate the school ID is invalid."""


class InvalidMenuLines(HomeAssistantError):
    """Error to indicate the menu lines configuration is invalid."""