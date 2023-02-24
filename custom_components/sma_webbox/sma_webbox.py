"""SMA webbox client protocol implementation."""

import asyncio
import json
import logging
import time
from asyncio import DatagramTransport, Future
from asyncio.events import AbstractEventLoop
from typing import Tuple

WEBBOX_PORT = 34268
WEBBOX_TIMEOUT = 5

WEBBOX_RPC_INTERVAL = 1  # seconds (manual says 30s between two 'queries' ...)

# - RPC API constants ---------------------------------------------------------
WEBBOX_MSG_GETPLANTOVERVIEW = "GetPlantOverview"
WEBBOX_MSG_GETDEVICES = "GetDevices"
WEBBOX_MSG_GETPROCESSDATACHANNELS = "GetProcessDataChannels"
WEBBOX_MSG_GETPROCESSDATA = "GetProcessData"

WEBBOX_REQ_VERSION = "version"
WEBBOX_REQ_PROC = "proc"
WEBBOX_REQ_ID = "id"
WEBBOX_REQ_FORMAT = "format"
WEBBOX_REQ_PARAMS = "params"

WEBBOX_REP_ERROR = "error"
WEBBOX_REP_OVERVIEW = "overview"
WEBBOX_REP_RESULT = "result"
WEBBOX_REP_CHILDREN = "children"
WEBBOX_REP_DEVICES = "devices"
WEBBOX_REP_DEVICE_KEY = "key"
WEBBOX_REP_DEVICE_NAME = "name"
WEBBOX_REP_CHANNELS = "channels"
WEBBOX_REP_VALUE_META = "meta"
WEBBOX_REP_VALUE_NAME = "name"
WEBBOX_REP_VALUE_VALUE = "value"
WEBBOX_REP_VALUE_UNIT = "unit"

WEBBOX_CHANNEL_VALUES = "channel_values"

WEBBOX_UNIT_AMPERE = "A"
WEBBOX_UNIT_VOLT = "V"
WEBBOX_UNIT_HERTZ = "Hz"
WEBBOX_UNIT_WATT = "W"
WEBBOX_UNIT_KILO_WATT_HOUR = "kWh"
WEBBOX_UNIT_HOURS = "h"
WEBBOX_UNIT_OHMS = "Ohm"
WEBBOX_UNIT_WATTS_PER_SQUARE_METER = "W/m^2"
WEBBOX_UNIT_TEMP_CELSIUS = "°C"
WEBBOX_UNIT_TEMP_FAHRENHEIT = "°F"
WEBBOX_UNIT_TEMP_KELVIN = "°K"
WEBBOX_UNIT_METERS_PER_SECOND = "m/s"

_LOGGER = logging.getLogger(__name__)


# - Utility functions ---------------------------------------------------------
def update_channel_values(
    current_channel_values: dict, new_channel_values: Tuple[dict]
) -> None:
    """Transform (meta, name, value, unit) input list in\
    {meta: (name, value, unit)} dict and update channel state value."""
    for channel_value in new_channel_values:
        key = channel_value.pop(WEBBOX_REP_VALUE_META)
        try:
            current_channel_values[key][
                WEBBOX_REP_VALUE_VALUE
            ] = channel_value[WEBBOX_REP_VALUE_VALUE]
        except KeyError:
            current_channel_values[key] = channel_value


# - Main class exceptions -----------------------------------------------------
class SmaWebboxException(Exception):
    """Base exception of the sma_webbox library."""


class SmaWebboxBadResponseException(SmaWebboxException):
    """An error or incorrect response id was returned by the device."""


class SmaWebboxTimeoutException(SmaWebboxException):
    """An timeout occurred in the connection with the device."""


class SmaWebboxConnectionException(SmaWebboxException):
    """An error occurred in the connection with the device."""


# - Main class implementation -------------------------------------------------
class WebboxClientProtocol:  # pylint: disable=too-many-instance-attributes
    """Webbox RPC Client implementation."""

    def __init__(self, loop: AbstractEventLoop, addr: Tuple[str, int]) -> None:
        """Instance parameter initialisation."""
        self._loop: AbstractEventLoop = loop
        self._addr: Tuple[str, int] = addr

        self._transport: DatagramTransport = None
        self._request_id: int = 0
        self._last_access_time: float = 0
        self._data_cache: dict = {}

        # Synchronization objects
        self._on_received: Future = None
        self._on_connected: Future = self._loop.create_future()

    @property
    def addr(self) -> Tuple[str, int]:
        """Return IP address."""
        return self._addr

    @property
    def data(self) -> dict:
        """Return webbox data cache."""
        return self._data_cache

    @property
    def transport(self) -> dict:
        """Return instance's DatagramTransport object."""
        return self._transport

    @property
    def on_connected(self) -> Future:
        """Return Future to await on while waiting for an UDP socket."""
        return self._on_connected

    @property
    def is_connected(self) -> bool:
        """Return True aslong as connection is alive."""
        return self._on_connected.done() if self._on_connected else False

    # - Base and Datagram protocols methods -----------------------------------
    def connection_made(self, transport: DatagramTransport) -> None:
        """Store transport object and release _on_connected future."""
        _LOGGER.info("UDP protocol created")
        self._transport = transport
        self._on_connected.set_result(True)

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Return Webbox response to rpc caller using future."""
        if self._addr[0] == addr[0]:
            data = json.loads(data.decode('iso-8859-1').replace("\0", ""))
            if not self._on_received.cancelled():
                self._on_received.set_result(data)

    def error_received(self, exc: Exception) -> None:
        """Close connection upon unexpected errors."""
        _LOGGER.warning("Error received: {%s}, closing", exc)
        self._transport.close()

    def connection_lost(
        self, exc: Exception
    ) -> None:  # pylint: disable=unused-argument
        """Destroy _onconnected future to reset is_connected."""
        _LOGGER.info("UDP protocol closed")
        self._on_connected = None

    # - SMA Webbox RPC API ----------------------------------------------------
    async def get_plant_overview(self) -> dict:
        """Define wrapper for get_plant_overview procedure."""
        return await self._rpc(
            self._build_rpc_request(WEBBOX_MSG_GETPLANTOVERVIEW)
        )

    async def get_devices(self) -> dict:
        """Define wrapper for get_devices procedure."""
        return await self._rpc(self._build_rpc_request(WEBBOX_MSG_GETDEVICES))

    async def get_process_data_channels(self, key: str) -> dict:
        """Define wrapper for get_process_data_channels procedure."""
        return await self._rpc(
            self._build_rpc_request(
                WEBBOX_MSG_GETPROCESSDATACHANNELS, device=key
            )
        )

    async def get_process_data(
        self, key: str, channels: Tuple[str, ...]
    ) -> dict:
        """Define wrapper for get_process_data procedure."""
        devices = [{WEBBOX_REP_DEVICE_KEY: key, WEBBOX_REP_CHANNELS: channels}]
        return await self._rpc(
            self._build_rpc_request(WEBBOX_MSG_GETPROCESSDATA, devices=devices)
        )

    # - RPC implementation-----------------------------------------------------
    def _build_rpc_request(self, name: str, **params: dict) -> Tuple[int, str]:
        """Construct UDP payload for RPC request."""
        self._request_id += 1

        request = {
            WEBBOX_REQ_VERSION: "1.0",
            WEBBOX_REQ_PROC: name,
            WEBBOX_REQ_FORMAT: "JSON",
            WEBBOX_REQ_ID: f"{self._request_id}",
        }
        if params:
            request[WEBBOX_REQ_PARAMS] = params

        return (
            self._request_id,
            "".join(
                i + "\0" for i in json.dumps(request, separators=(",", ":"))
            ),
        )

    async def _rpc(self, request: Tuple[int, str]) -> dict:
        """Send RPC request and wait for/return response."""
        # Wait for a minimum time between two rpc requests
        await asyncio.sleep(
            max(
                0, WEBBOX_RPC_INTERVAL - (time.time() - self._last_access_time)
            )
        )
        self._last_access_time = time.time()

        request_id, payload = request

        # Send RPC/UDP request to SMA Webbox
        _LOGGER.debug(payload)
        self._transport.sendto(payload.encode(), self._addr)

        # Wait for response from SMA Webbox
        self._on_received = self._loop.create_future()
        try:
            response = await asyncio.wait_for(
                self._on_received, timeout=WEBBOX_TIMEOUT
            )
            _LOGGER.debug(response)
        except asyncio.TimeoutError:
            _LOGGER.warning("RPC request timed out")
            self._on_received.cancel()
            raise SmaWebboxTimeoutException("RPC request timed out") from None

        # Raise exception upon errored response or id mismatch
        if WEBBOX_REP_ERROR in response:
            error_msg = f"Error response: {response[WEBBOX_REP_ERROR]}"
            _LOGGER.warning(error_msg)
            raise SmaWebboxBadResponseException(error_msg)

        if int(response[WEBBOX_REQ_ID]) != request_id:
            error_msg = (
                f"Unexpected id (expected {request_id}"
                f"got {response[WEBBOX_REQ_ID]})"
            )
            _LOGGER.warning(error_msg)
            raise SmaWebboxBadResponseException(error_msg)

        return response[WEBBOX_REP_RESULT]

    # - Webbox data model -----------------------------------------------------
    # self._data_cache = {
    #   'overview': {
    #     <sensor id> : {                * 'meta'
    #       'name': <sensor name>,
    #       'value': <sensor value>,
    #       'unit': <value unit>,
    #     }
    #     ...
    #   }
    #   'totalDevicesReturned': <# of devices>
    #   'devices': [
    #     { 'key': <key>,
    #       'name': <name>',
    #       'channels': <channel list>',
    #       'channel_values': {
    #         <sensor id> : {
    #           'name': <sensor name>,
    #           'value': <sensor value>,
    #           'unit': <value unit>,
    #         },
    #         ...
    #       }
    #       'children': <device list> },
    #     ...
    #   ]
    # }

    async def add_device_channels(self, devices: Tuple[dict]) -> None:
        """Add channel properties for each device."""
        for device in devices:
            response = await self.get_process_data_channels(
                device[WEBBOX_REP_DEVICE_KEY]
            )
            device[WEBBOX_REP_CHANNELS] = response[
                device[WEBBOX_REP_DEVICE_KEY]
            ]
            device[WEBBOX_CHANNEL_VALUES] = {}
            # TODO: test using fake webbox model ?  pylint: disable=fixme
            if WEBBOX_REP_CHILDREN in device:
                await self.add_device_channels(device[WEBBOX_REP_CHILDREN])

    async def create_webbox_model(self) -> None:
        """Create SMA Webox data model."""
        try:
            self._data_cache[WEBBOX_REP_OVERVIEW] = {}
            # Fetch device tree
            response = await self.get_devices()
            # Add channel info to response[WEBBOX_REP_DEVICES] key
            await self.add_device_channels(response[WEBBOX_REP_DEVICES])
            # Add device data to model
            self._data_cache = {**self._data_cache, **response}
        except Exception as ex:
            # Error while building webbox model
            self._transport.close()
            raise SmaWebboxConnectionException(
                f"Unable to create SMA Webbox model from device at"
                f"{self._addr[0]}:{self._addr[1]} ({ex})"
            ) from ex

    async def fetch_device_data(self, devices: Tuple[dict]) -> None:
        """Update data for each device."""
        for device in devices:
            # Fetch data for all sensors of a device
            response = await self.get_process_data(
                device[WEBBOX_REP_DEVICE_KEY], device[WEBBOX_REP_CHANNELS]
            )
            update_channel_values(
                device[WEBBOX_CHANNEL_VALUES],
                response[WEBBOX_REP_DEVICES][0][WEBBOX_REP_CHANNELS],
            )

            # TODO: test using fake webbox model ?  pylint: disable=fixme
            if WEBBOX_REP_CHILDREN in device:
                await self.fetch_device_data(device[WEBBOX_REP_CHILDREN])

    async def fetch_webbox_data(self) -> None:
        """Update SMA Webbox data."""
        # Fetch plant sensor data
        response = await self.get_plant_overview()
        update_channel_values(
            self._data_cache[WEBBOX_REP_OVERVIEW], response[WEBBOX_REP_OVERVIEW]
        )
        # Fetch all sensor data for all devices
        await self.fetch_device_data(self._data_cache[WEBBOX_REP_DEVICES])


# - Main section --------------------------------------------------------------


if __name__ == "__main__":
    # SMA Webbox example code.
    import argparse
    import sys

    def print_row(key: str, items: dict, prefix: str = "") -> None:
        """Display entry row."""
        if WEBBOX_REP_VALUE_UNIT not in items:
            items[WEBBOX_REP_VALUE_UNIT] = ""
        _LOGGER.info(
            "%s%-10s%-30s%-10s%-5s",
            prefix,
            key,
            items[WEBBOX_REP_VALUE_NAME],
            items[WEBBOX_REP_VALUE_VALUE],
            items[WEBBOX_REP_VALUE_UNIT],
        )

    def print_webbox_info(data: dict) -> None:
        """Display webbox model data table."""
        _LOGGER.info("-- Overview (%s)", time.ctime(time.time()))
        _LOGGER.info(
            "%-10s%-30s%-10s%-5s",
            WEBBOX_REP_VALUE_META,
            WEBBOX_REP_VALUE_NAME,
            WEBBOX_REP_VALUE_VALUE,
            WEBBOX_REP_VALUE_UNIT,
        )
        for key, items in data[WEBBOX_REP_OVERVIEW].items():
            print_row(key, items)

        for device in data[WEBBOX_REP_DEVICES]:
            _LOGGER.info("Devices")
            _LOGGER.info(
                " Key:%s, Name:%s",
                device[WEBBOX_REP_DEVICE_KEY],
                device[WEBBOX_REP_VALUE_NAME],
            )
            for key, items in device[WEBBOX_CHANNEL_VALUES].items():
                print_row(key, items, prefix="  ")

    async def main(url: str) -> None:
        """Connect to webbox and display sensor values forever."""
        _LOGGER.info("Starting SMA Webbox component")

        loop = asyncio.get_running_loop()

        try:
            # Create an UDP socket listening on port WEBBOX_PORT
            # and from any interface
            _, protocol = await loop.create_datagram_endpoint(
                lambda: WebboxClientProtocol(loop, (url, WEBBOX_PORT)),
                local_addr=("0.0.0.0", WEBBOX_PORT),
                reuse_port=True,
            )

            # Wait for socket ready signal
            await protocol.on_connected
            # Build webbox model (fetch device tree)
            await protocol.create_webbox_model()

            # Loop until connection lost or user
            while protocol.is_connected:
                try:
                    await protocol.fetch_webbox_data()
                except SmaWebboxTimeoutException as ex:
                    _LOGGER.warning(ex)
                except SmaWebboxBadResponseException as ex:
                    _LOGGER.warning(ex)

                print_webbox_info(protocol.data)

                await asyncio.sleep(30)
        except SmaWebboxConnectionException as ex:
            _LOGGER.error("%s", ex)
        except OSError as ex:
            _LOGGER.error(
                "Unable to connect to %s:%d (%s)", url, WEBBOX_PORT, ex
            )

    # -------------------------------------------------------------------------
    # Parse command line
    parser = argparse.ArgumentParser(description="SMA webbox example.")
    parser.add_argument("url", type=str, help="SMA webbox url")
    parser.add_argument("-d", help="Debug loglevel", action="store_true")

    args = parser.parse_args()

    # Setup logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.DEBUG if args.d else logging.INFO
    )

    # Run main loop
    asyncio.run(main(url=args.url))
