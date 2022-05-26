# HA-sma
SMA Sunny Webbox integration for Home Assistant

![webbox](https://user-images.githubusercontent.com/40644331/149579494-a5604e3b-8070-4c93-9a84-002c93e80e79.png)

**Note**: Tested against Sunny WebBox-20 running FW 01.05.08.R (using a Bluetooth connection with the inverter) 

## Highlights of what it does offer

- Poll Sunny Webbox using rpc [API v1.4](https://github.com/jpcornil-git/HA-sma/blob/main/Sunny-Webbox-remote-procedure-call-User-manual-v1.4.pdf)
- Create HA sensors for all reported channels and sources, e.g. in my setup:
   - Webbox summary ('My Plant') - 5 sensors
   - Inverter - 9 sensors
- **Config Flow** support (UI configuration) in addition to legacy configuration.yaml.

## Installation

### Using [HACS](https://hacs.xyz/)

1. Add https://github.com/jpcornil-git/HA-sma to your [custom repositories](https://hacs.xyz/docs/faq/custom_repositories/)

### Update custom_components folder

1. Clone or download all files from this repository 
2. Move custom_components/sma_webbox to your <ha_configuration_folder>, e.g. /home/homeassistant/.homeassistant/custom_components/sma_webbox
3. Restart HA and clear browser cache (or restart a browser); latter is required for new config_flow to show up
4. Add sma_webbox component using either:
   - **config flow** (Configuration->Integrations->Add integration, search for sma) 
   - **configuration.yaml** see configuration example below.
5. Created entities will be visible in the **Integrations** tab and aggregated per device in the **Devices** tab.
6. Enable desired sensor entities via the **Devices** (structured view) or **Entities** tab (flat view).

#### Example entry for `configuration.yaml`:

```yaml
# Example configuration.yaml
sma_webbox:
  ip_address: 192.168.1.109
  port: 34268
  scan_interval: 30
```
***Note***: Typically, only **ip_address** will be mentionned as illustrated below; I suppose that all devices are using UDP port default (34268) and a scan interval under 30s is probably meaningless as the webbox is not updating faster.
```yaml
# Example configuration.yaml
sma_webbox:
  ip_address: 192.168.1.109

```

## sma_webbox.py

This script implements the main object used by HomeAssistant but can also be used as an independent script to:
- test interoperability with a given webbox before addition to homeassistant
- display data fetched from webbox in a terminal
- extend capabilities/debug issues outside of HomeAssistant

**Note**: Tested with/developped for python3.9 (mandated by HomeAssistant from 2022.1)

```bash
python3 custom_components/sma_webbox/sma_webbox.py <webbox ip_address>
```
