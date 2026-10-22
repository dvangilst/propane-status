"""Config flow for Levac Propane (AirStatement) integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LevacApiClient, LevacAuthError, LevacConnectionError
from .const import (
    CONF_API_ENDPOINT,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TENANT_ID,
    CONF_USERNAME,
    DEFAULT_API_ENDPOINT,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_TENANT_ID,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class LevacPropaneConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Levac Propane."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            tenant_id = user_input.get(CONF_TENANT_ID, DEFAULT_TENANT_ID).strip()
            api_endpoint = user_input.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT).strip()
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES)

            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = LevacApiClient(
                username=username,
                password=password,
                session=session,
                tenant_id=tenant_id,
                api_endpoint=api_endpoint,
            )

            try:
                await client.async_login(force=True)
                # Verify we can also fetch tanks successfully
                await client.async_get_tanks()
            except LevacAuthError:
                errors["base"] = "invalid_auth"
            except LevacConnectionError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error during setup validation: %s", err)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Levac Propane ({username})",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_TENANT_ID: tenant_id,
                        CONF_API_ENDPOINT: api_endpoint,
                        CONF_SCAN_INTERVAL: scan_interval,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_MINUTES
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_MINUTES)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return LevacPropaneOptionsFlowHandler(config_entry)


class LevacPropaneOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Levac Propane."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES),
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_MINUTES)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
