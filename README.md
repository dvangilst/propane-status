# Levac Propane (AirStatement) - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/dvangilst/propane-status?color=blue)](https://github.com/dvangilst/propane-status/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A custom Home Assistant integration that periodically connects to the [Levac Propane AirStatement customer portal](https://levac-airstatement.datanovacloudapps.com), retrieves real-time tank gauge levels, calculates propane volume in liters, and stores history in Home Assistant so you can monitor your fuel level and track consumption over time.

---

## Features

- ⚡ **Direct REST API**: Directly queries the AirStatement cloud API (`https://api-airstatement.datanovacloudapps.com/api`) with JWT authentication—no brittle web scraping or headless browsers needed.
- 📊 **Rich Tank Sensors**:
  - **Tank Level (%)**: Real-time gauge percentage with `state_class: measurement` and dynamic icons (`gauge-empty`, `gauge-low`, `gauge-full`).
  - **Propane Volume (L)**: Estimated liters remaining (calculated taking into account the standard 80% maximum fill capacity for expansion).
  - **Tank Capacity (L)**: Total water capacity of the tank.
  - **Unit Price ($/L)**: Current fuel unit price.
  - **Pending Delivery (L)**: Quantity and scheduled delivery date when an order has been placed.
- 🕒 **Customizable Polling**: Configurable update interval (default: 60 minutes) with Options Flow support (change polling frequency anytime without re-adding the integration).
- 📈 **Long-Term Consumption Tracking**: Built-in compatibility with Home Assistant Long-Term Statistics (LTS), Utility Meters, and Derivative sensors to calculate daily/weekly burn rate.
- 🏷️ **Device Registry**: Automatically groups all sensors for a tank under a single device named after your delivery account number.

---

## Testing Your Credentials Before Installing

You can verify your portal login and inspect your tank data directly from your terminal using the included test script:

```bash
python test_client.py
```

It will prompt you for your portal email and password (passwords are masked), authenticate with the API, and display a formatted summary of all tanks, levels, and capacities.

---

## Installation

### Method 1: Via HACS (Recommended)

1. Ensure [HACS (Home Assistant Community Store)](https://hacs.xyz/) is installed.
2. In Home Assistant, open **HACS** > **Integrations**.
3. Click the three dots in the top-right corner and select **Custom repositories**.
4. Add the repository URL:
   - **Repository**: `https://github.com/dvangilst/propane-status`
   - **Type**: `Integration`
5. Click **Add**, find **Levac Propane (AirStatement)**, and click **Download**.
6. Restart Home Assistant.

### Method 2: Manual Installation

1. Download the latest release (or clone this repository).
2. Copy the `custom_components/levac_propane` directory into your Home Assistant configuration directory under `custom_components/`:
   ```
   <config_dir>/
   └── custom_components/
       └── levac_propane/
           ├── __init__.py
           ├── manifest.json
           ├── const.py
           ├── api.py
           ├── coordinator.py
           ├── config_flow.py
           ├── sensor.py
           ├── strings.json
           └── translations/
               └── en.json
   ```
3. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, navigate to **Settings** > **Devices & Services**.
2. Click **Add Integration** in the bottom-right corner.
3. Search for **Levac Propane (AirStatement)**.
4. Enter your credentials:
   - **Email / Username**: The email address you use to log in to `levac-airstatement.datanovacloudapps.com`.
   - **Password**: Your portal password.
   - **Update Interval (minutes)**: How often to poll for new readings (default: `60` minutes).
5. Click **Submit**. Your tanks will automatically be discovered and added as devices!

---

## Tracking Consumption Over Time

Because all sensors report `state_class: measurement`, Home Assistant will automatically store hourly, daily, and monthly statistics in its long-term database.

### 1. Daily / Monthly Consumption (Utility Meter)

To measure how many liters of propane you consume each day, week, or month:

1. Go to **Settings** > **Devices & Services** > **Helpers**.
2. Click **Create Helper** > **Utility Meter**.
3. Configure:
   - **Name**: `Daily Propane Consumption`
   - **Input sensor**: Select your `sensor.propane_tank_<id>_propane_volume`
   - **Meter reset cycle**: `Daily` (or `Monthly`)
   - **Net consumption**: Checked (or create a consumption template sensor if deliveries increase the total).

### 2. Burn Rate (Derivative Sensor)

To track the burn rate in liters per day:

```yaml
# Add to configuration.yaml
sensor:
  - platform: derivative
    source: sensor.propane_tank_12345_propane_volume
    name: Propane Consumption Rate
    unit_time: d # per day
    unit: L/d
    time_window: "24:00:00"
```

---

## Dashboard Examples

### Gauge Card (Matching Levac's Web Portal)

Add a standard Gauge Card to your Lovelace dashboard with Levac's color thresholds (Red: 0–15%, Yellow: 15–40%, Green: 40–80%):

```yaml
type: gauge
entity: sensor.propane_tank_12345_tank_level
name: Propane Tank Level
min: 0
max: 100
needle: true
severity:
  red: 0
  yellow: 15
  green: 40
```

### Tank Volume & Level Card

```yaml
type: entities
title: Propane Tank Status
entities:
  - entity: sensor.propane_tank_12345_tank_level
    name: Tank Level
  - entity: sensor.propane_tank_12345_propane_volume
    name: Estimated Liters
  - entity: sensor.propane_tank_12345_unit_price
    name: Unit Price
  - entity: sensor.propane_tank_12345_pending_delivery
    name: Scheduled Delivery
```

### History Graph (Track Level Over Time)

```yaml
type: history-graph
title: Propane Level History
hours_to_show: 168 # 7 days
entities:
  - entity: sensor.propane_tank_12345_tank_level
  - entity: sensor.propane_tank_12345_propane_volume
```

---

## Technical Details

- **Cloud Platform**: DataNova AirStatement (`api-airstatement.datanovacloudapps.com`)
- **Tenant ID**: `027A2C02-6F84-40DD-BD58-AD5E4C2E800A` (Levac Propane)
- **Authentication**: JWT Bearer token via `/authenticate/login`
- **Data Source**: `/deliveries/tanks`

---

## License

This project is licensed under the [MIT License](LICENSE).
