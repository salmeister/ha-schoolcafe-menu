"""Config flow for SchoolCafe integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import SchoolCafeAPI, SchoolCafeAPIError, looks_like_public_menu
from .const import (
    DOMAIN,
    CONF_SCHOOL_ID,
    CONF_SCHOOL_NAME,
    CONF_VIEW_ID,
    CONF_MENU_URL,
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


async def apply_public_menu(data: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a guest menu URL into a school id. Bare school ids pass through."""
    identifier = str(data.get(CONF_SCHOOL_ID, "")).strip()
    if not looks_like_public_menu(identifier):
        data[CONF_SCHOOL_ID] = identifier
        return data

    resolved = await SchoolCafeAPI.resolve_public_menu(identifier)
    if not resolved:
        raise InvalidSchoolId

    updated = data.copy()
    updated[CONF_MENU_URL] = resolved["menu_url"]
    updated[CONF_VIEW_ID] = resolved["view_id"]
    updated[CONF_SCHOOL_ID] = resolved["school_id"]
    if resolved.get("school_name"):
        updated[CONF_SCHOOL_NAME] = resolved["school_name"]

    # Keep an explicit grade, meal, or line. Replace only the form defaults.
    if resolved.get("grade") and data.get(CONF_GRADE, DEFAULT_GRADE) == DEFAULT_GRADE:
        updated[CONF_GRADE] = resolved["grade"]
    if resolved.get("meal_type") and data.get(CONF_MEAL_TYPE, DEFAULT_MEAL_TYPE) == DEFAULT_MEAL_TYPE:
        updated[CONF_MEAL_TYPE] = resolved["meal_type"]
    current_line = (data.get(CONF_SERVING_LINE) or DEFAULT_SERVING_LINE).strip().lower()
    if resolved.get("serving_line") and current_line in {DEFAULT_SERVING_LINE.lower(), "main lines"}:
        updated[CONF_SERVING_LINE] = resolved["serving_line"]
    return updated


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
        view_id=data.get(CONF_VIEW_ID) or None,
        menu_url=data.get(CONF_MENU_URL) or None,
        school_name=data.get(CONF_SCHOOL_NAME) or None,
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
    title = data.get(CONF_SCHOOL_NAME) or f"SchoolCafe ({data[CONF_SCHOOL_ID][:8]}...)"
    
    return {"title": title, "data": processed_data}


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
                user_input = await apply_public_menu(user_input)
                self._user_input.update(user_input)

                await self.async_set_unique_id(user_input[CONF_SCHOOL_ID])
                self._abort_if_unique_id_configured()

                return await self.async_step_advanced()

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidSchoolId:
                errors[CONF_SCHOOL_ID] = "invalid_school_id"
            except SchoolCafeAPIError as err:
                _LOGGER.error("Cannot resolve SchoolCafe menu link: %s", err)
                errors["base"] = "cannot_connect"
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
                menu_lines_str = user_input.get(CONF_MENU_LINES, ", ".join(DEFAULT_MENU_LINES))
                menu_lines = [line.strip().upper() for line in menu_lines_str.split(",") if line.strip()]
                if not menu_lines:
                    menu_lines = DEFAULT_MENU_LINES
                user_input[CONF_MENU_LINES] = menu_lines

                identifier = str(user_input.get(CONF_SCHOOL_ID, "")).strip()
                if looks_like_public_menu(identifier):
                    user_input = await apply_public_menu(user_input)
                else:
                    user_input[CONF_SCHOOL_ID] = identifier
                    user_input[CONF_VIEW_ID] = ""
                    user_input[CONF_MENU_URL] = ""
                    user_input[CONF_SCHOOL_NAME] = ""

                new_school_id = user_input[CONF_SCHOOL_ID]
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    if entry.entry_id != self.config_entry.entry_id and entry.unique_id == new_school_id:
                        errors["base"] = "already_configured"
                        break
                else:
                    title = user_input.get(CONF_SCHOOL_NAME) or self.config_entry.title
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        unique_id=new_school_id,
                        title=title,
                        data={**self.config_entry.data, **user_input},
                    )
                    return self.async_create_entry(title="", data=user_input)

            except InvalidSchoolId:
                errors[CONF_SCHOOL_ID] = "invalid_school_id"
            except SchoolCafeAPIError as err:
                _LOGGER.error("Cannot resolve SchoolCafe menu link: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Get current config values, preferring previously saved options
        current_config = {**self.config_entry.data, **self.config_entry.options}
        menu_lines = current_config.get(CONF_MENU_LINES, DEFAULT_MENU_LINES)
        if isinstance(menu_lines, str):
            menu_lines_str = menu_lines
        else:
            menu_lines_str = ", ".join(menu_lines)
        school_identifier = current_config.get(CONF_MENU_URL) or current_config.get(CONF_SCHOOL_ID, "")
        
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCHOOL_ID,
                    default=school_identifier,
                ): str,
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