"""SMA Webbox component entry point."""
import logging
import asyncio
from datetime import timedelta
from typing import Tuple

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import *

from .sma_webbox import (
    WEBBOX_PORT,
    SmaWebboxBadResponseException,
    SmaWebboxConnectionException,
    SmaWebboxTimeoutException,
    WebboxClientProtocol,
    WebboxClientInstance,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setup component."""

    # Initiate a configflow from a configuration.yaml entry if any.
    if DOMAIN in config:
        _LOGGER.info("Setting up %s component from configuration.yaml", DOMAIN)
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config[DOMAIN],
            )
        )

    return True


async def async_setup_api(hass: HomeAssistant) -> asyncio.DatagramProtocol:
    """Setup api (udp connection) proxy."""

    try:
        api = hass.data[DOMAIN][SMA_WEBBOX_API]
    except KeyError:
        # Create UDP client proxy
        on_connected = hass.loop.create_future()
        _, api = await hass.loop.create_datagram_endpoint(
            lambda: WebboxClientProtocol(on_connected),
            local_addr=("0.0.0.0", WEBBOX_PORT),
            reuse_port=True,
        )

        # Wait for socket ready signal
        try:
            await asyncio.wait_for(
                on_connected, timeout=10
            )
        except TimeoutError:
            _LOGGER.error(
                "Unable to setup UDP client for port %d", WEBBOX_PORT)

        # Initialize domain data structure
        hass.data[DOMAIN] = {SMA_WEBBOX_API: api}
        _LOGGER.info("%s API created", DOMAIN)

        # Close asyncio protocol on shutdown
        async def async_close_api(event):  # pylint: disable=unused-argument
            """Close the transport/protocol."""
            api.close()

        # TODO: close API upon component removal ?  pylint: disable=fixme
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_close_api)

    return api


async def async_setup_instance(
    hass: HomeAssistant, ip_address: str, udp_port: int
) -> WebboxClientInstance:

    api = await async_setup_api(hass)

    """Open a connection to the webbox and build device model."""
    instance = WebboxClientInstance(
        hass.loop,
        api,
        (ip_address, udp_port)
    )
    # Build webbox model (fetch device tree)
    await instance.create_webbox_model()

    return instance


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sma webbox from a config entry."""
    # Setup connection
    try:
        instance = await async_setup_instance(
            hass, entry.data[CONF_IP_ADDRESS], entry.data[CONF_PORT]
        )
    except (OSError, SmaWebboxConnectionException) as exc:
        raise ConfigEntryNotReady from exc

    # Define the coordinator update callback
    async def async_update_data():
        """Update SMA webbox sensors."""
        try:
            await instance.fetch_webbox_data()
        except (
            SmaWebboxBadResponseException,
            SmaWebboxTimeoutException,
        ) as exc:
            raise UpdateFailed(exc) from exc

    # TODO: Move scan_interval to options ?  pylint: disable=fixme
    interval = timedelta(
        seconds=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sma_webbox_coordinator",
        update_method=async_update_data,
        update_interval=interval,
    )

    # Try to fetch initial data, bail out otherwise
    await coordinator.async_config_entry_first_refresh()

    # Expose data required by coordinated entities
    hass.data[DOMAIN].setdefault(SMA_WEBBOX_ENTRIES, {})
    hass.data[DOMAIN][SMA_WEBBOX_ENTRIES][entry.entry_id] = {
        SMA_WEBBOX_INSTANCE: instance,
        SMA_WEBBOX_COORDINATOR: coordinator,
    }

    _LOGGER.info(
        "SMA Webbox instance created (%s:%d)",
        entry.data[CONF_IP_ADDRESS],
        entry.data[CONF_PORT],
    )

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform.SENSOR]
    )
    if unload_ok:
        hass.data[DOMAIN][SMA_WEBBOX_ENTRIES].pop(entry.entry_id)

        _LOGGER.info(
            "SMA Webbox instance unloaded(%s:%d)",
            entry.data[CONF_IP_ADDRESS],
            entry.data[CONF_PORT],
        )

    return unload_ok
