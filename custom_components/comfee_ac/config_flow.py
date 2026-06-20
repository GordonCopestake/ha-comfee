"""Config flow for Comfee AC."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from msmart.cloud import CloudError
from msmart.device import AirConditioner
from msmart.discover import Discover
from msmart.lan import AuthenticationError

from .const import (
    CONF_DEVICE_ID,
    CONF_KEY,
    CONF_PORT,
    CONF_REGION,
    CONF_TOKEN,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ComfeeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Comfee AC config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            token = user_input.get(CONF_TOKEN, "").strip()
            key = user_input.get(CONF_KEY, "").strip()
            device_id = user_input.get(CONF_DEVICE_ID)

            try:
                if token and key and device_id:
                    data = {
                        CONF_NAME: user_input.get(CONF_NAME) or DEFAULT_NAME,
                        CONF_HOST: host,
                        CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                        CONF_DEVICE_ID: int(device_id),
                        CONF_TOKEN: token,
                        CONF_KEY: key,
                    }
                    return self.async_create_entry(title=data[CONF_NAME], data=data)

                device = await Discover.discover_single(
                    host,
                    region=user_input.get(CONF_REGION, "US"),
                    account=user_input.get(CONF_USERNAME) or None,
                    password=user_input.get(CONF_PASSWORD) or None,
                    discovery_packets=1,
                )
                if not isinstance(device, AirConditioner):
                    errors["base"] = "not_supported"
                else:
                    name = user_input.get(CONF_NAME) or device.name or DEFAULT_NAME
                    data = {
                        CONF_NAME: name,
                        CONF_HOST: host,
                        CONF_PORT: device.port,
                        CONF_DEVICE_ID: device.id,
                        CONF_TOKEN: device.token,
                        CONF_KEY: device.key,
                        CONF_REGION: user_input.get(CONF_REGION, "US"),
                    }
                    if user_input.get(CONF_USERNAME):
                        data[CONF_USERNAME] = user_input[CONF_USERNAME]
                    if user_input.get(CONF_PASSWORD):
                        data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
                    return self.async_create_entry(title=name, data=data)
            except (AuthenticationError, CloudError, ValueError):
                _LOGGER.exception("Failed to authenticate Comfee AC")
                errors["base"] = "auth"
            except OSError:
                _LOGGER.exception("Failed to connect to Comfee AC")
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.0.26"): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_DEVICE_ID): int,
                vol.Optional(CONF_TOKEN): str,
                vol.Optional(CONF_KEY): str,
                vol.Optional(CONF_REGION, default="US"): vol.In(["US", "DE", "KR"]),
                vol.Optional(CONF_USERNAME): str,
                vol.Optional(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
