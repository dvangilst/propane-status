"""DataUpdateCoordinator for Levac Propane integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LevacApiClient, LevacApiError, LevacAuthError, LevacConnectionError
from .const import DOMAIN, LOGGER

_LOGGER = logging.getLogger(__name__)


class LevacDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Class to manage fetching data from the AirStatement API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: LevacApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self._previous_tanks: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch tank data and parse into a structured dictionary."""
        try:
            raw_addresses = await self.client.async_get_tanks()
        except LevacAuthError as err:
            raise UpdateFailed(f"Authentication failure: {err}") from err
        except LevacConnectionError as err:
            raise UpdateFailed(f"Connection failed: {err}") from err
        except LevacApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error updating Levac propane data: {err}") from err

        parsed_tanks: dict[str, dict[str, Any]] = {}
        now_iso = datetime.now(timezone.utc).isoformat()

        if not isinstance(raw_addresses, list):
            _LOGGER.warning("Expected list from /deliveries/tanks, got %s", type(raw_addresses))
            return parsed_tanks

        for addr_idx, address in enumerate(raw_addresses):
            address_str = address.get("customerAddress") or address.get("addressLine1") or address.get("street") or f"Location {addr_idx + 1}"
            city = address.get("city") or ""
            full_address = f"{address_str}, {city}".strip(", ")
            customer_id = address.get("customerId") or address.get("id")
            customer_name = address.get("customerName") or ""

            pesh_pact = address.get("peshPact") or []
            for pact_idx, pact in enumerate(pesh_pact):
                tank_id = str(pact.get("id") or pact.get("shipAccountId") or f"{customer_id}_{addr_idx}_{pact_idx}")
                ship_account_id = str(pact.get("shipAccountId") or tank_id)
                monitor_id = pact.get("tankMonitorId")
                ship_type = pact.get("shipType")

                max_capacity = pact.get("maxCapacity") or 0.0
                try:
                    max_capacity = float(max_capacity)
                except (ValueError, TypeError):
                    max_capacity = 0.0

                product_info = pact.get("pEserv") or {}
                product_desc = product_info.get("productDesc") or "PROPANE"

                tank_sub = pact.get("tanks") or {}
                percentage_val = tank_sub.get("currentPercentage")
                current_percentage: float | None = None
                if percentage_val is not None:
                    try:
                        current_percentage = round(float(percentage_val), 1)
                    except (ValueError, TypeError):
                        current_percentage = None

                unit_price = tank_sub.get("unitPrice")
                try:
                    unit_price = float(unit_price) if unit_price is not None else None
                except (ValueError, TypeError):
                    unit_price = None

                last_measured_at = tank_sub.get("lastMesuredAt")

                # Liters currently in tank
                current_liters_val = pact.get("currentTotalLiters")
                current_liters: float | None = None
                if current_liters_val is not None and float(current_liters_val) > 0:
                    current_liters = round(float(current_liters_val), 1)
                elif current_percentage is not None and max_capacity > 0:
                    # Propane tanks are filled to 80% maximum capacity for safety/expansion
                    is_propane = "propane" in product_desc.lower()
                    divisor = 80.0 if is_propane else 100.0
                    current_liters = round(max_capacity * (current_percentage / divisor), 1)

                # Delivery history & totals
                last_delivery_date = pact.get("lastDeliveryDate")
                last_delivery_liters = pact.get("lastDeliveryLiters")
                last_year_total_liters = pact.get("lastYrTotalLiters")

                # Order request details
                order_req = pact.get("orderRequest") or {}
                order_pending = bool(order_req.get("reqStatus") or order_req.get("requestQty"))
                order_qty = order_req.get("requestQty")
                order_date = order_req.get("tripDate")

                parsed_tanks[tank_id] = {
                    "tank_id": tank_id,
                    "ship_account_id": ship_account_id,
                    "monitor_id": monitor_id,
                    "ship_type": ship_type,
                    "address": full_address,
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "product_desc": product_desc,
                    "max_capacity_liters": max_capacity,
                    "current_percentage": current_percentage,
                    "current_liters": current_liters,
                    "unit_price": unit_price,
                    "last_reading": last_measured_at,
                    "last_delivery_date": last_delivery_date,
                    "last_delivery_liters": last_delivery_liters,
                    "last_year_total_liters": last_year_total_liters,
                    "order_pending": order_pending,
                    "order_qty": order_qty,
                    "order_date": order_date,
                    "last_sync": now_iso,
                    "raw_pact": pact,
                }

        self._previous_tanks = parsed_tanks
        return parsed_tanks
