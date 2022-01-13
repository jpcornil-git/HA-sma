# HA-sma
SMA Sunny Webbox integration for Home Assistant

Tested against Sunny WebBox-20 (using a Bluetooth connection with the inverter) running FW 01.05.08.R 

## Highlights of what it does offer

- Poll Sunny Webbox using rpc [API v1.4](https://github.com/jpcornil-git/HA-sma/Sunny-Webbox-remote-procedure-call-User-manual-v1.4.pdf) 
- Create HA sensors for all reported channels and sources, e.g. in my case:
   - Webbox summary ('My Plant') - 5 sensors
   - Inverter - 9 sensors
- **Config Flow** support (UI configuration) in addition to legacy configuration.yaml.

## Installation

### Using [HACS](https://hacs.xyz/)

1. Add https://github.com/jpcornil-git/HA-sma to your [custom repositories](https://hacs.xyz/docs/faq/custom_repositories/)

### Update custom_components folder

1. Clone or download all files from this repository 
2. Move custom_components/sma to your <ha_configuration_folder>, e.g. /home/homeassistant/.homeassistant/custom_components/sma
3. Restart HA and clear browser cache (or restart a browser); latter is required for new config_flow to show up
4. Add sma component using:
   - **config flow** (Configuration->Integrations->Add integration) 
   - **configuration.yaml** see configuration example below.
5. Created entities will be visible in the **Integrations** tab and aggregated per device in the **Devices** tab.
6. Enable desired sensor entities via the **Devices** (structured view) or **Entities** tab (flat view).

## Example entry for `configuration.yaml`:

```yaml
# Example configuration.yaml
sma:
  ip_address: 192.168.1.109
  port: 34268
  scan_interval: 30
```
***Note***: Typically, only **ip_address** will be mentionned as illustrated below; I suppose that all devices are using UDP port default (34268) and a scan interval under 30s is probably meaningless as the webbox is not updating faster.
```yaml
# Example configuration.yaml
sma:
  ip_address: 192.168.1.109

```
