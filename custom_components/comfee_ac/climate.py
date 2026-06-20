"""Climate platform for Comfee AC."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from msmart.device import AirConditioner

from .const import DOMAIN
from .coordinator import ComfeeCoordinator, HVAC_TO_MODE, MODE_TO_HVAC, enum_name

PRESET_ECO = "eco"
PRESET_TURBO = "turbo"
PRESET_SLEEP = "sleep"
PRESET_FREEZE_PROTECTION = "freeze_protection"
PRESET_NONE = "none"

FAN_NAME_TO_VALUE = {
    "auto": AirConditioner.FanSpeed.AUTO,
    "silent": AirConditioner.FanSpeed.SILENT,
    "low": AirConditioner.FanSpeed.LOW,
    "medium": AirConditioner.FanSpeed.MEDIUM,
    "high": AirConditioner.FanSpeed.HIGH,
    "max": AirConditioner.FanSpeed.MAX,
}

SWING_NAME_TO_VALUE = {
    "off": AirConditioner.SwingMode.OFF,
    "vertical": AirConditioner.SwingMode.VERTICAL,
    "horizontal": AirConditioner.SwingMode.HORIZONTAL,
    "both": AirConditioner.SwingMode.BOTH,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities."""
    coordinator: ComfeeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComfeeClimate(coordinator)])


class ComfeeClimate(CoordinatorEntity[ComfeeCoordinator], ClimateEntity):
    """Comfee AC climate entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator: ComfeeCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(entry.data.get("device_id", entry.entry_id)))},
            "name": entry.data.get(CONF_NAME),
            "manufacturer": "Comfee/Midea",
            "model": "Air Conditioner",
        }

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return supported features."""
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and bool(self.coordinator.data.values.get("online"))

    @property
    def current_temperature(self) -> float | None:
        """Return current room temperature."""
        return self.coordinator.data.values.get("indoor_temperature")

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return self.coordinator.data.values.get("target_temperature")

    @property
    def min_temp(self) -> float:
        """Return minimum target temperature."""
        device = self.coordinator.device
        return device.min_target_temperature if device else 16

    @property
    def max_temp(self) -> float:
        """Return maximum target temperature."""
        device = self.coordinator.device
        return device.max_target_temperature if device else 30

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if not self.coordinator.data.values.get("power"):
            return HVACMode.OFF
        return MODE_TO_HVAC.get(
            self.coordinator.data.values.get("mode"),
            HVACMode.COOL,
        )

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return supported HVAC modes."""
        modes = {HVACMode.OFF}
        device = self.coordinator.device
        if device:
            modes.update(MODE_TO_HVAC.get(mode, HVACMode.COOL) for mode in device.supported_operation_modes)
        else:
            modes.update([HVACMode.AUTO, HVACMode.COOL, HVACMode.DRY, HVACMode.HEAT, HVACMode.FAN_ONLY])
        return list(modes)

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode."""
        return enum_name(self.coordinator.data.values.get("fan_speed"))

    @property
    def fan_modes(self) -> list[str]:
        """Return supported fan modes."""
        device = self.coordinator.device
        speeds = device.supported_fan_speeds if device else FAN_NAME_TO_VALUE.values()
        return [enum_name(speed) for speed in speeds if enum_name(speed)]

    @property
    def swing_mode(self) -> str | None:
        """Return current swing mode."""
        return enum_name(self.coordinator.data.values.get("swing_mode"))

    @property
    def swing_modes(self) -> list[str]:
        """Return supported swing modes."""
        device = self.coordinator.device
        modes = device.supported_swing_modes if device else SWING_NAME_TO_VALUE.values()
        return [enum_name(mode) for mode in modes if enum_name(mode)]

    @property
    def preset_mode(self) -> str | None:
        """Return active preset mode."""
        values = self.coordinator.data.values
        for preset in self.preset_modes:
            if preset == PRESET_NONE:
                continue
            if values.get(preset):
                return preset
        return PRESET_NONE

    @property
    def preset_modes(self) -> list[str]:
        """Return supported preset modes."""
        device = self.coordinator.device
        if not device:
            return [PRESET_NONE, PRESET_ECO, PRESET_TURBO, PRESET_SLEEP, PRESET_FREEZE_PROTECTION]

        presets = [PRESET_NONE, PRESET_SLEEP]
        if device.supports_eco:
            presets.append(PRESET_ECO)
        if device.supports_turbo:
            presets.append(PRESET_TURBO)
        if device.supports_freeze_protection:
            presets.append(PRESET_FREEZE_PROTECTION)
        return presets

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        values = self.coordinator.data.values
        return {
            "display_on": values.get("display_on"),
            "filter_alert": values.get("filter_alert"),
            "error_code": values.get("error_code"),
            "outdoor_temperature": values.get("outdoor_temperature"),
            "indoor_humidity": values.get("indoor_humidity"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        changes: dict[str, Any] = {}
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            changes["target_temperature"] = float(temperature)
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.async_set_hvac_mode(hvac_mode)
        if changes:
            await self.coordinator.async_apply(**changes)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_apply(power_state=False)
            return

        changes = {"power_state": True}
        if hvac_mode in HVAC_TO_MODE:
            changes["operational_mode"] = HVAC_TO_MODE[hvac_mode]
        await self.coordinator.async_apply(**changes)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        await self.coordinator.async_apply(fan_speed=FAN_NAME_TO_VALUE[fan_mode])

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing mode."""
        await self.coordinator.async_apply(swing_mode=SWING_NAME_TO_VALUE[swing_mode])

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        changes = {
            "eco": False,
            "turbo": False,
            "sleep": False,
            "freeze_protection": False,
        }
        if preset_mode != PRESET_NONE:
            changes[preset_mode] = True
        await self.coordinator.async_apply(**changes)

    async def async_turn_on(self) -> None:
        """Turn on the AC."""
        await self.coordinator.async_apply(power_state=True)

    async def async_turn_off(self) -> None:
        """Turn off the AC."""
        await self.coordinator.async_apply(power_state=False)
