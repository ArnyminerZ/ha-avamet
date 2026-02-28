# AVAMET Home Assistant Integration

This custom component for Home Assistant integrates real-time weather data and camera images from [AVAMET](https://www.avamet.org) (Associació Valenciana de Meteorologia).

## Features

- **Weather Entity**: Provides temperature, humidity, pressure, and wind speed from the station.
- **Camera Entity**: Optionally adds a camera if the configured AVAMET station has a webcam.

## Installation

### HACS (Recommended)

This integration is completely compatible with [HACS](https://hacs.xyz/).

1. Open HACS in your Home Assistant instance.
2. Click on the 3 dots in the top right corner and select **Custom repositories**.
3. Add this repository's URL with the category "Integration".
4. Click "Download" to install the integration.
5. Restart your Home Assistant.
6. Navigate to **Settings > Devices & Services > Add Integration**.
7. Search for "AVAMET" and set it up.

### Manual

1. Download the repository files.
2. Copy the `custom_components/avamet` directory into your Home Assistant's `config/custom_components/` directory.
3. Restart Home Assistant.
4. Set up the integration from **Settings > Devices & Services > Add Integration**.

## Configuration

During setup, you will be asked to enter the **Station ID** for the location you want to monitor. 

You can find the ID by navigating to the AVAMET site. The ID looks something like `c24m072e02`.
