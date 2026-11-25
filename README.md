# AVAMET Home Assistant Integration

This custom component for Home Assistant integrates real-time weather data and camera images from [AVAMET](https://www.avamet.org) (Associació Valenciana de Meteorologia).

[![Open Marketplace Repository on My HA][marketplace-badge]][marketplace-link]
[![Add Integration to My HA][integration-badge]][integration-link]

[marketplace-badge]: https://my.home-assistant.io/badges/marketplace_repository.svg
[marketplace-link]: https://my.home-assistant.io/redirect/marketplace_repository/?owner=ArnyminerZ&repository=ha-avamet&category=integration
[integration-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
[integration-link]: https://my.home-assistant.io/redirect/config_flow_start/?domain=avamet

## Features

- **Weather Entity**: Provides temperature, humidity, pressure, and wind speed from the station.
- **Camera Entity**: Optionally adds a camera if the configured AVAMET station has a webcam.

## Installation

### Marketplace (Recommended)

Starting with Home Assistant **2026.11**, HACS is called the **Marketplace**. This integration is available through it.

1. Click the **Open Marketplace Repository on My HA** badge above, or open the Marketplace in your Home Assistant instance.
2. Click on the 3 dots in the top right corner and select **Custom repositories**.
3. Add this repository's URL with the category "Integration".
4. Click "Download" to install the integration.
5. Restart your Home Assistant.
6. Click the **Add Integration to My HA** badge above, or navigate to **Settings > Devices & Services > Add Integration**, search for "AVAMET" and set it up.

> **Home Assistant earlier than 2026.11:** the Marketplace was previously named [HACS](https://hacs.xyz/). The steps are the same; just open HACS instead of the Marketplace (the repository badge above links to the HACS repository page via My Home Assistant on those versions).

### Manual

1. Download the repository files.
2. Copy the `custom_components/avamet` directory into your Home Assistant's `config/custom_components/` directory.
3. Restart Home Assistant.
4. Set up the integration from **Settings > Devices & Services > Add Integration**.

## Configuration

During setup, you will be asked to enter the **Station ID** for the location you want to monitor. 

You can find the ID by navigating to the AVAMET site. The ID looks something like `c24m072e02`.
