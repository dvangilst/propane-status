"""The Levac Propane (AirStatement) Home Assistant Integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LevacApiClient
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
)
from .coordinator import LevacDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Levac Propane from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    tenant_id = entry.data.get(CONF_TENANT_ID, DEFAULT_TENANT_ID)
    api_endpoint = entry.data.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT)

    # Allow scan_interval to be overridden in options
    scan_interval_minutes = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES),
    )
    update_interval = timedelta(minutes=scan_interval_minutes)

    session = async_get_clientsession(hass)
    client = LevacApiClient(
        username=username,
        password=password,
        session=session,
        tenant_id=tenant_id,
        api_endpoint=api_endpoint,
    )

    coordinator = LevacDataUpdateCoordinator(
        hass=hass,
        client=client,
        update_interval=update_interval,
    )

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
