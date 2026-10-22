"""Constants for the Levac Propane (AirStatement) integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "levac_propane"

# API Endpoints & Headers
DEFAULT_API_ENDPOINT = "https://api-airstatement.datanovacloudapps.com/api"
DEFAULT_APP_KEY = "NDgzODA5ZGUtZGY4NC00YjU3LTg5MmQtYjI4MjNkNmJlZGQ5"
DEFAULT_TENANT_ID = "027A2C02-6F84-40DD-BD58-AD5E4C2E800A"
DEFAULT_ORIGIN = "https://levac-airstatement.datanovacloudapps.com"

# Configuration keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TENANT_ID = "tenant_id"
CONF_API_ENDPOINT = "api_endpoint"

# Default values
DEFAULT_SCAN_INTERVAL_MINUTES = 60
MIN_SCAN_INTERVAL_MINUTES = 15

# Attributes
ATTR_TANK_ID = "tank_id"
ATTR_SHIP_ACCOUNT_ID = "ship_account_id"
ATTR_SHIP_TYPE = "ship_type"
ATTR_MAX_CAPACITY = "max_capacity_liters"
ATTR_CURRENT_LITERS = "current_liters"
ATTR_UNIT_PRICE = "unit_price"
ATTR_PRODUCT_DESC = "product_description"
ATTR_ORDER_PENDING = "order_pending"
ATTR_ORDER_QTY = "order_quantity_liters"
ATTR_ORDER_DATE = "order_trip_date"
ATTR_LAST_SYNC = "last_sync"
