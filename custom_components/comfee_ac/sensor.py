"""Sensor platform for Comfee AC."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ComfeeCoordinator, enum_name


@dataclass(frozen=True, kw_only=True)
class ComfeeSensorDescription(SensorEntityDescription):
    """Description for a Comfee sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS = [
    ComfeeSensorDescription(
        key="status",
        translation_key="status",
        value_fn=lambda values: "on" if values.get("power") else "off",
    ),
    ComfeeSensorDescription(
        key="indoor_temperature",
        translation_key="indoor_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda values: values.get("indoor_temperature"),
    ),
    ComfeeSensorDescription(
        key="target_temperature",
        translation_key="target_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda values: values.get("target_temperature"),
    ),
    ComfeeSensorDescription(
        key="indoor_humidity",
        translation_key="indoor_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda values: values.get("indoor_humidity"),
    ),
    ComfeeSensorDescription(
        key="mode",
        translation_key="mode",
        value_fn=lambda values: enum_name(values.get("mode")),
    ),
    ComfeeSensorDescription(
        key="fan_speed",
        translation_key="fan_speed",
        value_fn=lambda values: enum_name(values.get("fan_speed")),
    ),
    ComfeeSensorDescription(
        key="error_code",
        translation_key="error_code",
        value_fn=lambda values: values.get("error_code"),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: ComfeeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComfeeSensor(coordinator, description) for description in SENSORS])


class ComfeeSensor(CoordinatorEntity[ComfeeCoordinator], SensorEntity):
    """Comfee diagnostic sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ComfeeCoordinator, description: ComfeeSensorDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(entry.data.get("device_id", entry.entry_id)))},
            "name": entry.data.get(CONF_NAME),
            "manufacturer": "Comfee/Midea",
            "model": "Air Conditioner",
        }

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data.values)
