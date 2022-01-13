"""Config flow for the sma webbox integration."""
from __future__ import annotations

import logging
from ipaddress import ip_address
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResult

from . import async_setup_connection
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .sma_webbox import WEBBOX_PORT, SmaWebboxConnectionException

_LOGGER = logging.getLogger(__name__)

# Schema definition for configuration.yaml
COMPONENT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Optional(CONF_PORT, default=WEBBOX_PORT): cv.port,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)


def get_title(user_input) -> str:
    """Create component title."""
    return f"{user_input[CONF_IP_ADDRESS]}"


def get_unique_id(user_input) -> str:
    """Create component unique id."""
    return f"{user_input[CONF_IP_ADDRESS]}-{user_input[CONF_PORT]}"


class SmaWebboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMA."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._data = {
            CONF_IP_ADDRESS: vol.UNDEFINED,
            CONF_PORT: WEBBOX_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        }

    async def async_step_import(self, user_input=None):
        """Update or create a new component from configuration.yaml."""
        # Parameter validation
        try:
            # Validate configuration data format and add default values
            self._data = COMPONENT_SCHEMA(user_input)
            # Verify ip address format
            ip_address(user_input[CONF_IP_ADDRESS])
        except Exception as ex:  # pylint: disable=broad-except
            msg = f"Invalid yaml configuration ({ex})"
            _LOGGER.error(msg)
            self.hass.components.persistent_notification.create(
                msg,
                title=f"{DOMAIN} configuration",
                notification_id=f"{DOMAIN} notification",
            )
            return self.async_abort(reason="invalid_parameter")

        # Update entry with yaml configuration then abort if it exists already
        unique_id = get_unique_id(user_input)
        config_entry = await self.async_set_unique_id(unique_id)
        if config_entry:
            if self.hass.config_entries.async_update_entry(
                config_entry, data=self._data
            ):
                _LOGGER.info(
                    "Updating configuration for %s:%s from yaml",
                    DOMAIN,
                    unique_id,
                )
            return self.async_abort(reason="existing_entry")

        # Create a new entry otherwise
        return self.async_create_entry(
            title=get_title(self._data), data=self._data
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create a new component from config flow UI."""
        errors = {}
        if user_input is not None:
            self._data[CONF_IP_ADDRESS] = user_input[CONF_IP_ADDRESS]
            self._data[CONF_PORT] = user_input[CONF_PORT]
            self._data[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

            # Abort if a webbox is already configured with the same ip:port
            await self.async_set_unique_id(get_unique_id(self._data))
            self._abort_if_unique_id_configured()

            # Parameter validation
            try:
                # Verify ip address format
                ip_address(user_input[CONF_IP_ADDRESS])
                # Try to connect to check ip:port correctness
                transport,_ = await async_setup_connection(
                    self.hass,
                    user_input[CONF_IP_ADDRESS],
                    user_input[CONF_PORT],
                )
                transport.close()
            except ValueError:
                errors["base"] = "invalid_host"
            except SmaWebboxConnectionException:
                errors["base"] = "cannot_connect"
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception (%s)", ex)
                errors["base"] = "unknown"

            # Create new entry if successful
            if not errors:
                _LOGGER.info(
                    "Create entry for %s:%d (scan_interval = %d) "
                    "from configflow",
                    user_input[CONF_IP_ADDRESS],
                    user_input[CONF_PORT],
                    user_input[CONF_SCAN_INTERVAL],
                )
                return self.async_create_entry(
                    title=get_title(self._data), data=self._data
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IP_ADDRESS, default=self._data[CONF_IP_ADDRESS]
                    ): cv.string,
                    vol.Optional(
                        CONF_PORT, default=self._data[CONF_PORT]
                    ): cv.port,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._data[CONF_SCAN_INTERVAL],
                    ): cv.positive_int,
                }
            ),
            errors=errors,
        )
