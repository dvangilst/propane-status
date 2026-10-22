"""Sensor platform for Levac Propane (AirStatement) integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CURRENT_LITERS,
    ATTR_LAST_DELIVERY_DATE,
    ATTR_LAST_DELIVERY_LITERS,
    ATTR_LAST_READING,
    ATTR_LAST_SYNC,
    ATTR_LAST_YEAR_TOTAL_LITERS,
    ATTR_MAX_CAPACITY,
    ATTR_MONITOR_ID,
    ATTR_ORDER_DATE,
    ATTR_ORDER_PENDING,
    ATTR_ORDER_QTY,
    ATTR_PRODUCT_DESC,
    ATTR_SHIP_ACCOUNT_ID,
    ATTR_SHIP_TYPE,
    ATTR_TANK_ID,
    ATTR_UNIT_PRICE,
    DEFAULT_ORIGIN,
    DOMAIN,
)
from .coordinator import LevacDataUpdateCoordinator


def _parse_iso_datetime(dt_str: str | None) -> datetime | None:
    """Safely parse ISO datetime string, setting UTC timezone if missing."""
    if not dt_str or dt_str.startswith("1899") or dt_str.startswith("0001"):
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            # Assume local/UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class LevacSensorEntityDescription(SensorEntityDescription):
    """Describes a Levac Propane sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any] = lambda tank: None
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] = lambda tank: {}


SENSOR_DESCRIPTIONS: tuple[LevacSensorEntityDescription, ...] = (
    LevacSensorEntityDescription(
        key="level",
        name="Tank Level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        value_fn=lambda tank: tank.get("current_percentage"),
        attr_fn=lambda tank: {
            ATTR_TANK_ID: tank.get("tank_id"),
            ATTR_SHIP_ACCOUNT_ID: tank.get("ship_account_id"),
            ATTR_MONITOR_ID: tank.get("monitor_id"),
            ATTR_SHIP_TYPE: tank.get("ship_type"),
            ATTR_PRODUCT_DESC: tank.get("product_desc"),
            ATTR_MAX_CAPACITY: tank.get("max_capacity_liters"),
            ATTR_CURRENT_LITERS: tank.get("current_liters"),
            ATTR_UNIT_PRICE: tank.get("unit_price"),
            ATTR_LAST_READING: tank.get("last_reading"),
            ATTR_LAST_DELIVERY_DATE: tank.get("last_delivery_date"),
            ATTR_LAST_DELIVERY_LITERS: tank.get("last_delivery_liters"),
            ATTR_LAST_YEAR_TOTAL_LITERS: tank.get("last_year_total_liters"),
            ATTR_LAST_SYNC: tank.get("last_sync"),
        },
    ),
    LevacSensorEntityDescription(
        key="volume",
        name="Propane Volume",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=getattr(SensorDeviceClass, "VOLUME_STORAGE", getattr(SensorDeviceClass, "VOLUME", None)),
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-cylinder",
        value_fn=lambda tank: tank.get("current_liters"),
        attr_fn=lambda tank: {
            ATTR_MAX_CAPACITY: tank.get("max_capacity_liters"),
            ATTR_CURRENT_LITERS: tank.get("current_liters"),
        },
    ),
    LevacSensorEntityDescription(
        key="last_reading",
        name="Last Reading",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-check-outline",
        value_fn=lambda tank: _parse_iso_datetime(tank.get("last_reading")),
    ),
    LevacSensorEntityDescription(
        key="capacity",
        name="Tank Capacity",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=getattr(SensorDeviceClass, "VOLUME_STORAGE", getattr(SensorDeviceClass, "VOLUME", None)),
        icon="mdi:propane-tank",
        value_fn=lambda tank: tank.get("max_capacity_liters"),
        entity_registry_enabled_default=False,
    ),
    LevacSensorEntityDescription(
        key="unit_price",
        name="Unit Price",
        native_unit_of_measurement="$/L",
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:currency-usd",
        value_fn=lambda tank: tank.get("unit_price"),
        entity_registry_enabled_default=False,
    ),
    LevacSensorEntityDescription(
        key="last_delivery",
        name="Last Delivery",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        icon="mdi:truck-check",
        value_fn=lambda tank: tank.get("last_delivery_liters"),
        attr_fn=lambda tank: {
            ATTR_LAST_DELIVERY_DATE: tank.get("last_delivery_date"),
            ATTR_LAST_DELIVERY_LITERS: tank.get("last_delivery_liters"),
        },
        entity_registry_enabled_default=False,
    ),
    LevacSensorEntityDescription(
        key="pending_order",
        name="Pending Delivery",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        icon="mdi:truck-delivery",
        value_fn=lambda tank: tank.get("order_qty") if tank.get("order_pending") else 0,
        attr_fn=lambda tank: {
            ATTR_ORDER_PENDING: tank.get("order_pending", False),
            ATTR_ORDER_QTY: tank.get("order_qty"),
            ATTR_ORDER_DATE: tank.get("order_date"),
        },
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Levac Propane sensor entities based on a config entry."""
    coordinator: LevacDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[LevacPropaneSensor] = []

    for tank_id in coordinator.data:
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                LevacPropaneSensor(
                    coordinator=coordinator,
                    tank_id=tank_id,
                    description=description,
                    entry=entry,
                )
            )

    async_add_entities(entities)


class LevacPropaneSensor(CoordinatorEntity[LevacDataUpdateCoordinator], SensorEntity):
    """Representation of a Levac Propane Sensor."""

    entity_description: LevacSensorEntityDescription

    def __init__(
        self,
        coordinator: LevacDataUpdateCoordinator,
        tank_id: str,
        description: LevacSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._tank_id = tank_id
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_{tank_id}_{description.key}"

        tank_data = self.tank_data
        ship_account_id = tank_data.get("ship_account_id", tank_id)
        self._attr_name = f"Propane Tank {ship_account_id} {description.name}"

        # Assign device info with hardware monitor serial number
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, tank_id)},
            name=f"Propane Tank {ship_account_id}",
            manufacturer="Levac Propane / DataNova",
            model=f"{tank_data.get('product_desc', 'PROPANE')} Tank",
            serial_number=tank_data.get("monitor_id"),
            suggested_area=tank_data.get("address"),
            configuration_url=DEFAULT_ORIGIN,
        )

    @property
    def tank_data(self) -> dict[str, Any]:
        """Return the current data for this specific tank."""
        return self.coordinator.data.get(self._tank_id, {})

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.tank_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return self.entity_description.attr_fn(self.tank_data)

    @property
    def icon(self) -> str | None:
        """Return dynamic icon for tank level if applicable."""
        if self.entity_description.key == "level":
            val = self.native_value
            if val is not None:
                try:
                    pct = float(val)
                    if pct <= 15:
                        return "mdi:gauge-empty"
                    if pct <= 35:
                        return "mdi:gauge-low"
                    if pct >= 75:
                        return "mdi:gauge-full"
                except (ValueError, TypeError):
                    pass
        return self.entity_description.icon
