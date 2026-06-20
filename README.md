# Comfee AC Home Assistant Integration

Custom Home Assistant integration for a Comfee/Midea-compatible air conditioner
that speaks the `msmart-ng` LAN protocol on TCP port `6444`.

## Install

Copy `custom_components/comfee_ac` into your Home Assistant `custom_components`
directory, then restart Home Assistant.

Home Assistant will install the Python dependency from `manifest.json`:

```text
msmart-ng==2026.4.1
```

## Configure

Add the integration from **Settings > Devices & services > Add Integration** and
search for **Comfee AC**.

For your detected device:

```text
Host: 192.168.0.26
Port: 6444
```

The preferred setup is fully local with:

```text
Device ID
Token
Key
```

If those are not supplied, the config flow will try discovery and cloud-backed
authentication using the optional region/account/password fields.

## Entities

The integration creates:

- A climate entity for power, HVAC mode, target temperature, fan, swing, and presets.
- Sensors for status, indoor temperature, target temperature, mode, fan speed, humidity, and error code.
