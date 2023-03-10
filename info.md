[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

[SMA Webbox Custom Component](https://github.com/jpcornil-git/HA-sma)

SMA Sunny Webbox integration for Home Assistant

Tested against:
- Sunny WebBox-20 running FW 01.05.08.R (using a Bluetooth connection with the inverter)
- Sunny WebBox-G1 running FW 01.52 (using RS-485 connection with the inverter)

## Highlights of what it does offer

- Poll Sunny Webbox using rpc [API v1.4](https://github.com/jpcornil-git/HA-sma/blob/main/Sunny-Webbox-remote-procedure-call-User-manual-v1.4.pdf)
- Create HA sensors for all reported channels and sources, e.g.:
   - WebBox-20
      - Webbox summary ('My Plant') - 5 sensors
      - Inverter - 9 sensors
   - WebBox-G1
      - Webbox summary ('My Plant') - 5 sensors
      - Inverter - 18 sensors
      - Weather - 6 sensors
- **Config Flow** support (UI configuration) in addition to legacy configuration.yaml.

## Useful links

- [Repository](https://github.com/jpcornil-git/HA-sma)
