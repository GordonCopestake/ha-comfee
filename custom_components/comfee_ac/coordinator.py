"""Coordinator for Comfee AC devices."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from msmart.base_device import Device
from msmart.cloud import CloudError
from msmart.const import DeviceType
from msmart.device import AirConditioner
from msmart.discover import Discover
from msmart.lan import AuthenticationError

from .const import (
    CONF_DEVICE_ID,
    CONF_KEY,
    CONF_PORT,
    CONF_REGION,
    CONF_TOKEN,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


MODE_TO_HVAC = {
    AirConditioner.OperationalMode.AUTO: HVACMode.AUTO,
    AirConditioner.OperationalMode.COOL: HVACMode.COOL,
    AirConditioner.OperationalMode.DRY: HVACMode.DRY,
    AirConditioner.OperationalMode.HEAT: HVACMode.HEAT,
    AirConditioner.OperationalMode.FAN_ONLY: HVACMode.FAN_ONLY,
    AirConditioner.OperationalMode.SMART_DRY: HVACMode.DRY,
}

HVAC_TO_MODE = {
    HVACMode.AUTO: AirConditioner.OperationalMode.AUTO,
    HVACMode.COOL: AirConditioner.OperationalMode.COOL,
    HVACMode.DRY: AirConditioner.OperationalMode.DRY,
    HVACMode.HEAT: AirConditioner.OperationalMode.HEAT,
    HVACMode.FAN_ONLY: AirConditioner.OperationalMode.FAN_ONLY,
}


@dataclass(frozen=True)
class DeviceState:
    """Last known AC state."""

    values: dict[str, Any]


def enum_name(value: Any) -> str | None:
    """Return a stable lowercase enum name for Home Assistant UI values."""
    if value is None:
        return None
    if hasattr(value, "name"):
        return value.name.lower()
    return str(value).lower()


class ComfeeCoordinator(DataUpdateCoordinator[DeviceState]):
    """Manage one Comfee/Midea-compatible air conditioner."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.config_entry = entry
        self.device: AirConditioner | None = None
        self._capabilities_loaded = False

    async def _async_update_data(self) -> DeviceState:
        """Fetch state from the device."""
        try:
            device = await self._async_get_device()
            await device.refresh()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed("Authentication with AC failed") from err
        except CloudError as err:
            raise ConfigEntryAuthFailed("Cloud authentication failed") from err
        except TimeoutError as err:
            raise UpdateFailed(f"Timed out refreshing AC: {err}") from err
        except OSError as err:
            raise ConfigEntryNotReady(f"Could not reach AC: {err}") from err

        if not device.online:
            raise UpdateFailed("AC did not respond to refresh")

        return DeviceState(device.to_dict())

    async def _async_get_device(self) -> AirConditioner:
        """Return an authenticated device object."""
        if self.device is not None:
            return self.device

        data = self.config_entry.data
        host = data[CONF_HOST]
        port = data.get(CONF_PORT, DEFAULT_PORT)

        if data.get(CONF_DEVICE_ID) and data.get(CONF_TOKEN) and data.get(CONF_KEY):
            device = Device.construct(
                type=DeviceType.AIR_CONDITIONER,
                ip=host,
                port=port,
                device_id=int(data[CONF_DEVICE_ID]),
            )
            if not isinstance(device, AirConditioner):
                raise ConfigEntryNotReady("Configured device is not an air conditioner")
            await device.authenticate(bytes.fromhex(data[CONF_TOKEN]), bytes.fromhex(data[CONF_KEY]))
            self.device = device
            return await self._async_load_capabilities(device)

        device = await Discover.discover_single(
            host,
            region=data.get(CONF_REGION, "US"),
            account=data.get(CONF_USERNAME),
            password=data.get(CONF_PASSWORD),
            discovery_packets=1,
        )
        if device is None:
            raise ConfigEntryNotReady("AC was not found during discovery")
        if not isinstance(device, AirConditioner):
            raise ConfigEntryNotReady("Discovered device is not an air conditioner")

        self.device = device
        return await self._async_load_capabilities(device)

    async def _async_load_capabilities(self, device: AirConditioner) -> AirConditioner:
        """Load capabilities once for richer Home Assistant controls."""
        if self._capabilities_loaded:
            return device

        await device.get_capabilities()
        self._capabilities_loaded = True
        return device

    async def async_apply(self, **changes: Any) -> None:
        """Apply changes to the AC and refresh Home Assistant state."""
        device = await self._async_get_device()

        for attr, value in changes.items():
            setattr(device, attr, value)

        try:
            await device.apply()
            await self.async_request_refresh()
        except AuthenticationError as err:
            raise HomeAssistantError("Authentication with AC failed") from err
        except TimeoutError as err:
            raise HomeAssistantError("Timed out applying AC state") from err
        except OSError as err:
            raise HomeAssistantError(f"Could not reach AC: {err}") from err

    async def async_set_display(self, enabled: bool) -> None:
        """Set the AC display by toggling it when needed."""
        device = await self._async_get_device()
        await device.refresh()
        if device.display_on != enabled:
            await device.toggle_display()
        await self.async_request_refresh()
