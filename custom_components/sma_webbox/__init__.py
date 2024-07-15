"""SMA Webbox component entry point."""
import logging
from asyncio import DatagramProtocol, DatagramTransport
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

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SMA_WEBBOX_COORDINATOR,
    SMA_WEBBOX_PROTOCOL,
    SMA_WEBBOX_REMOVE_LISTENER,
)
from .sma_webbox import (
    SmaWebboxBadResponseException,
    SmaWebboxConnectionException,
    SmaWebboxTimeoutException,
    WebboxClientProtocol,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Initiate a configflow from a configuration.yaml entry if any."""
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


async def async_setup_connection(
    hass: HomeAssistant, ip_address: str, udp_port: int
) -> Tuple[DatagramTransport, DatagramProtocol]:
    """Open a connection to the webbox and build device model."""
    transport, protocol = await hass.loop.create_datagram_endpoint(
        lambda: WebboxClientProtocol(hass.loop, (ip_address, udp_port)),
        local_addr=("0.0.0.0", udp_port),
        reuse_port=True,
    )

    # Wait for socket ready signal
    await protocol.on_connected
    # Build webbox model (fetch device tree)
    await protocol.create_webbox_model()

    return (transport, protocol)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sma webbox from a config entry."""
    _LOGGER.info(
        "SMA Webbox instance created(%s:%d)",
        entry.data[CONF_IP_ADDRESS],
        entry.data[CONF_PORT],
    )

    # Setup connection
    try:
        transport, protocol = await async_setup_connection(
            hass, entry.data[CONF_IP_ADDRESS], entry.data[CONF_PORT]
        )
    except (OSError, SmaWebboxConnectionException) as exc:
        raise ConfigEntryNotReady from exc

    # Define the coordinator update callback
    async def async_update_data():
        """Update SMA webbox sensors."""
        try:
            await protocol.fetch_webbox_data()
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
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        transport.close()
        raise

    # Close asyncio protocol on shutdown
    async def async_close_session(event):  # pylint: disable=unused-argument
        """Close the protocol."""
        transport.close()

    remove_stop_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, async_close_session
    )

    # Expose data required by coordinated entities
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        SMA_WEBBOX_PROTOCOL: protocol,
        SMA_WEBBOX_COORDINATOR: coordinator,
        SMA_WEBBOX_REMOVE_LISTENER: remove_stop_listener,
    }

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform.SENSOR]
    )
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        data[SMA_WEBBOX_PROTOCOL].transport.close()
        data[SMA_WEBBOX_REMOVE_LISTENER]()

        _LOGGER.info(
            "SMA Webbox instance unloaded(%s:%d)",
            entry.data[CONF_IP_ADDRESS],
            entry.data[CONF_PORT],
        )

    return unload_ok
