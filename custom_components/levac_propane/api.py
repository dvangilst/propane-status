"""API Client for Levac Propane / DataNova AirStatement."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any

import aiohttp

from .const import (
    DEFAULT_API_ENDPOINT,
    DEFAULT_APP_KEY,
    DEFAULT_ORIGIN,
    DEFAULT_TENANT_ID,
    LOGGER,
)

_LOGGER = logging.getLogger(__name__)


class LevacApiError(Exception):
    """Base exception for Levac Propane API errors."""


class LevacAuthError(LevacApiError):
    """Authentication failed."""


class LevacConnectionError(LevacApiError):
    """Connection or communication error."""


class LevacApiClient:
    """Client for communicating with the AirStatement API."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        tenant_id: str = DEFAULT_TENANT_ID,
        api_endpoint: str = DEFAULT_API_ENDPOINT,
        app_key: str = DEFAULT_APP_KEY,
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session = session
        self._tenant_id = tenant_id
        self._api_endpoint = api_endpoint.rstrip("/")
        self._app_key = app_key
        self._token: str | None = None
        self._token_expiration: datetime | None = None

    def _default_headers(self) -> dict[str, str]:
        """Return base headers required by the AirStatement API."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "appkey": self._app_key,
            "Origin": DEFAULT_ORIGIN,
            "Referer": f"{DEFAULT_ORIGIN}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def is_token_valid(self) -> bool:
        """Check if cached token exists and has not expired."""
        if not self._token or not self._token_expiration:
            return False
        # Buffer of 60 seconds before expiration
        return datetime.now(timezone.utc) < self._token_expiration

    async def async_login(self, force: bool = False) -> str:
        """Authenticate with the portal and retrieve a JWT bearer token."""
        if not force and self.is_token_valid():
            return self._token  # type: ignore[return-value]

        login_url = f"{self._api_endpoint}/authenticate/login"
        payload = {
            "username": self._username,
            "password": self._password,
            "tenantid": self._tenant_id,
        }

        headers = self._default_headers()
        # Drop authorization header during login
        headers.pop("Authorization", None)

        try:
            async with self._session.post(
                login_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status in (401, 403):
                    error_text = await response.text()
                    _LOGGER.error("Authentication failed: HTTP %s: %s", response.status, error_text)
                    raise LevacAuthError("Invalid username or password.")

                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Login endpoint returned HTTP %s: %s", response.status, error_text)
                    raise LevacApiError(f"Login failed with status {response.status}: {error_text}")

                data = await response.json()
                token = data.get("token")
                if not token:
                    raise LevacAuthError("No authentication token in response.")

                self._token = token
                exp_str = data.get("expiration")
                if exp_str:
                    try:
                        # Parsing ISO 8601 expiration datetime
                        self._token_expiration = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                    except ValueError:
                        self._token_expiration = None

                _LOGGER.debug("Successfully authenticated with AirStatement API.")
                return token

        except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as err:
            _LOGGER.error("Connection error while connecting to AirStatement API: %s", err)
            raise LevacConnectionError(f"Connection error: {err}") from err
        except LevacApiError:
            raise
        except Exception as err:
            _LOGGER.exception("Unexpected error during login: %s", err)
            raise LevacApiError(f"Unexpected error: {err}") from err

    async def async_get_tanks(self) -> list[dict[str, Any]]:
        """Fetch tank data from the portal."""
        await self.async_login()

        url = f"{self._api_endpoint}/deliveries/tanks"
        headers = self._default_headers()

        try:
            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status in (401, 403):
                    # Try re-authenticating once
                    _LOGGER.debug("Token expired or rejected. Attempting re-login.")
                    await self.async_login(force=True)
                    headers = self._default_headers()
                    async with self._session.get(
                        url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
                    ) as retry_response:
                        if retry_response.status != 200:
                            raise LevacAuthError("Re-authentication failed to authorize tanks endpoint.")
                        return await retry_response.json()

                if response.status != 200:
                    error_text = await response.text()
                    raise LevacApiError(f"Failed to fetch tanks: HTTP {response.status}: {error_text}")

                return await response.json()

        except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as err:
            raise LevacConnectionError(f"Connection error while fetching tanks: {err}") from err
        except LevacApiError:
            raise
        except Exception as err:
            raise LevacApiError(f"Unexpected error fetching tanks: {err}") from err

    async def async_get_delivery_history(self) -> list[dict[str, Any]]:
        """Fetch delivery history."""
        await self.async_login()

        url = f"{self._api_endpoint}/deliveries/history"
        headers = self._default_headers()

        try:
            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as err:
            _LOGGER.warning("Could not fetch delivery history: %s", err)
            return []
