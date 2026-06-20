"""Constants for the Comfee AC integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "comfee_ac"

CONF_DEVICE_ID = "device_id"
CONF_KEY = "key"
CONF_PORT = "port"
CONF_REGION = "region"
CONF_TOKEN = "token"

DEFAULT_NAME = "Comfee AC"
DEFAULT_PORT = 6444
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

PLATFORMS = ["climate", "sensor"]
