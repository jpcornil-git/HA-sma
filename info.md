[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

[SMA Webbox Custom Component](https://github.com/jpcornil-git/HA-sma)

SMA Sunny Webbox integration for Home Assistant

Tested against Sunny WebBox-20 (using a Bluetooth connection with the inverter) running FW 01.05.08.R 

## Highlights of what it does offer

- Poll Sunny Webbox using rpc [API v1.4](https://github.com/jpcornil-git/HA-sma/blob/main/Sunny-Webbox-remote-procedure-call-User-manual-v1.4.pdf)
- Create HA sensors for all reported channels and sources, e.g. in my setup:
   - Webbox summary ('My Plant') - 5 sensors
   - Inverter - 9 sensors
- **Config Flow** support (UI configuration) in addition to legacy configuration.yaml.

## Useful links

- [Repository](https://github.com/jpcornil-git/HA-sma)
