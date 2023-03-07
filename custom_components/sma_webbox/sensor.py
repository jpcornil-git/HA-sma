"""Sensor platform for SMA Webbox integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
    UnitOfTemperature,
    UnitOfIrradiance,
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, SMA_WEBBOX_COORDINATOR, SMA_WEBBOX_PROTOCOL
from .sma_webbox import (
    WEBBOX_CHANNEL_VALUES,
    WEBBOX_REP_DEVICE_NAME,
    WEBBOX_REP_DEVICES,
    WEBBOX_REP_OVERVIEW,
    WEBBOX_REP_VALUE_UNIT,
    WEBBOX_REP_VALUE_VALUE,
    WEBBOX_UNIT_AMPERE,
    WEBBOX_UNIT_HERTZ,
    WEBBOX_UNIT_HOURS,
    WEBBOX_UNIT_KILO_WATT_HOUR,
    WEBBOX_UNIT_OHMS,
    WEBBOX_UNIT_VOLT,
    WEBBOX_UNIT_WATT,
    WEBBOX_UNIT_TEMP_CELSIUS,
    WEBBOX_UNIT_TEMP_KELVIN,
    WEBBOX_UNIT_TEMP_FAHRENHEIT,
    WEBBOX_UNIT_WATTS_PER_SQUARE_METER,
    WEBBOX_UNIT_METERS_PER_SECOND,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMA Webbox sensors."""
    sma_webbox = hass.data[DOMAIN][config_entry.entry_id]

    protocol = sma_webbox[SMA_WEBBOX_PROTOCOL]
    coordinator = sma_webbox[SMA_WEBBOX_COORDINATOR]

    _LOGGER.info(
        "Creating sensors for %s:%d %s integration",
        protocol.addr[0],
        protocol.addr[1],
        DOMAIN,
    )

    entities = []

    device_id = 0
    # Create DeviceInfo for webbox 'plant'
    device_info = DeviceInfo(
        configuration_url=f"http://{protocol.addr[0]}",
        identifiers={(DOMAIN, config_entry.entry_id)},
        manufacturer="SMA",
        model="Webbox",
        name=f"{DOMAIN}[{device_id}]:My Plant",
    )

    # Add sensors from PlantOverview
    for name, data_dict in protocol.data[WEBBOX_REP_OVERVIEW].items():
        entities.append(
            SMAWebboxSensor(
                f"{DOMAIN}_{device_id}_{name}",
                data_dict,
                coordinator,
                config_entry.unique_id,
                device_info,
            )
        )

    # Add sensors from device list
    # TODO: Handle hierarchy ('children' nodes) pylint: disable=fixme
    for device in protocol.data[WEBBOX_REP_DEVICES]:
        device_id += 1
        # Create DeviceInfo for each webbox device
        device_info = DeviceInfo(
            configuration_url=f"http://{protocol.addr[0]}",
            identifiers={(DOMAIN, device[WEBBOX_REP_DEVICE_NAME])},
            manufacturer="SMA",
            model="Webbox",
            name=f"{DOMAIN}[{device_id}]:{device[WEBBOX_REP_DEVICE_NAME]}",
            via_device=(DOMAIN, config_entry.entry_id),
        )
        for name, data_dict in device[WEBBOX_CHANNEL_VALUES].items():
            entities.append(
                SMAWebboxSensor(
                    f"{DOMAIN}_{device_id}_{name}",
                    data_dict,
                    coordinator,
                    config_entry.unique_id,
                    device_info,
                )
            )

    async_add_entities(entities)


class SMAWebboxSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SMA Webbox sensor."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        name: str,
        data: dict,
        coordinator: DataUpdateCoordinator,
        config_entry_unique_id: str,
        device_info: DeviceInfo,
    ) -> None:
        """Attach sensor to coordinator so we are scheduled on updates."""
        super().__init__(coordinator)

        # Keep a reference to sensor data (updated by ordinator)
        self._data = data
        self._name = name
        self._unique_id = f"{config_entry_unique_id}-{name}"
        self._device_info = device_info

        if WEBBOX_REP_VALUE_UNIT in self._data:
            self.set_sensor_attributes(self._data[WEBBOX_REP_VALUE_UNIT])

    def set_sensor_attributes(self, unit) -> None:
        """Define HA sensor attributes based on webbox units."""
        if unit == WEBBOX_UNIT_AMPERE:
            self._attr_unit_of_measurement = UnitOfElectricCurrent.AMPERE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.CURRENT
        elif unit == WEBBOX_UNIT_VOLT:
            self._attr_unit_of_measurement = UnitOfElectricPotential.VOLT
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.VOLTAGE
        elif unit == WEBBOX_UNIT_HERTZ:
            self._attr_unit_of_measurement = UnitOfFrequency.HERTZ
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.FREQUENCY
        elif unit == WEBBOX_UNIT_WATT:
            self._attr_unit_of_measurement = UnitOfPower.WATT
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.POWER
        elif unit == WEBBOX_UNIT_KILO_WATT_HOUR:
            self._attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_device_class = SensorDeviceClass.ENERGY
        elif unit == WEBBOX_UNIT_HOURS:
            self._attr_unit_of_measurement = UnitOfTime.HOURS
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_device_class = SensorDeviceClass.DURATION
        elif unit == WEBBOX_UNIT_TEMP_CELSIUS:
            self._attr_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif unit == WEBBOX_UNIT_TEMP_KELVIN:
            self._attr_unit_of_measurement = UnitOfTemperature.KELVIN
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif unit == WEBBOX_UNIT_TEMP_FAHRENHEIT:
            self._attr_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif unit == WEBBOX_UNIT_WATTS_PER_SQUARE_METER:
            self._attr_unit_of_measurement = UnitOfIrradiance.WATTS_PER_SQUARE_METER
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.IRRADIANCE
        elif unit == WEBBOX_UNIT_METERS_PER_SECOND:
            self._attr_unit_of_measurement = UnitOfSpeed.METERS_PER_SECOND
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.WIND_SPEED
        elif unit == WEBBOX_UNIT_OHMS:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return sensor's device info."""
        return self._device_info

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        value = self._data[WEBBOX_REP_VALUE_VALUE]
        try:
            if WEBBOX_REP_VALUE_UNIT in self._data:
                value = float(value)
        except ValueError:
            value = None

        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit the value is expressed in."""
        return self._attr_unit_of_measurement

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this sensor."""
        return self._unique_id

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Sensor should be manually enabled after first registration."""
        return False
