#!/usr/bin/env python3
"""Standalone CLI test tool for Levac Propane (AirStatement) API.

Use this script to verify your credentials and inspect your tank data
before installing the custom component in Home Assistant.

Usage:
    python test_client.py
    python test_client.py --username user@example.com --password mysecret
"""

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request

API_ENDPOINT = "https://api-airstatement.datanovacloudapps.com/api"
APP_KEY = "NDgzODA5ZGUtZGY4NC00YjU3LTg5MmQtYjI4MjNkNmJlZGQ5"
TENANT_ID = "027A2C02-6F84-40DD-BD58-AD5E4C2E800A"
ORIGIN = "https://levac-airstatement.datanovacloudapps.com"


def main() -> None:
    """Run login and tank fetch test."""
    parser = argparse.ArgumentParser(description="Test Levac AirStatement API connectivity and view tank levels.")
    parser.add_argument("--username", "-u", help="AirStatement portal email/username")
    parser.add_argument("--password", "-p", help="AirStatement portal password")
    parser.add_argument("--raw", action="store_true", help="Print raw JSON responses")
    args = parser.parse_args()

    username = args.username
    password = args.password

    if not username:
        username = input("AirStatement Username (email): ").strip()
    if not password:
        password = getpass.getpass("AirStatement Password: ").strip()

    if not username or not password:
        print("Error: Username and password are required.", file=sys.stderr)
        sys.exit(1)

    print(f"\n1. Authenticating as {username}...")
    login_url = f"{API_ENDPOINT}/authenticate/login"
    login_headers = {
        "Content-Type": "application/json",
        "appkey": APP_KEY,
        "Origin": ORIGIN,
        "Referer": f"{ORIGIN}/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LevacTestClient/1.0",
    }
    login_payload = {
        "username": username,
        "password": password,
        "tenantid": TENANT_ID,
    }

    try:
        req = urllib.request.Request(
            login_url,
            data=json.dumps(login_payload).encode("utf-8"),
            headers=login_headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            login_res = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Authentication Failed (HTTP {e.code}):", file=sys.stderr)
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            print(json.dumps(err_data, indent=2), file=sys.stderr)
        except Exception:
            print(e.read().decode("utf-8"), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)

    token = login_res.get("token")
    if not token:
        print("Error: No bearer token received in login response.", file=sys.stderr)
        sys.exit(1)

    print(" Authentication successful!")
    print(f"Token expiration: {login_res.get('expiration', 'N/A')}")

    if args.raw:
        print("\n[Raw Login Response]")
        print(json.dumps(login_res, indent=2))

    print("\n2. Fetching Tank data (/deliveries/tanks)...")
    tanks_url = f"{API_ENDPOINT}/deliveries/tanks"
    auth_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "Origin": ORIGIN,
        "Referer": f"{ORIGIN}/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LevacTestClient/1.0",
    }

    try:
        req = urllib.request.Request(tanks_url, headers=auth_headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            tanks_res = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Failed to fetch tanks (HTTP {e.code}):", file=sys.stderr)
        print(e.read().decode("utf-8"), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching tanks: {e}", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        print("\n[Raw Tanks Response]")
        print(json.dumps(tanks_res, indent=2))

    print(" Tanks data retrieved successfully!\n")
    print("=" * 60)
    print("PROPANE TANK STATUS SUMMARY")
    print("=" * 60)

    if not isinstance(tanks_res, list) or len(tanks_res) == 0:
        print("No addresses or tanks found on this account.")
        return

    tank_count = 0
    for addr_idx, addr in enumerate(tanks_res):
        address_line = addr.get("addressLine1") or addr.get("street") or f"Location #{addr_idx + 1}"
        city = addr.get("city", "")
        customer_id = addr.get("customerId", "N/A")
        print(f"Address: {address_line}, {city} (Customer ID: {customer_id})")

        pacts = addr.get("peshPact") or []
        for pact in pacts:
            tank_count += 1
            tank_id = pact.get("id") or pact.get("shipAccountId")
            ship_account = pact.get("shipAccountId", "N/A")
            max_cap = pact.get("maxCapacity", 0.0)
            product_desc = (pact.get("pEserv") or {}).get("productDesc", "Propane")

            tank_info = pact.get("tanks") or {}
            percentage = tank_info.get("currentPercentage")
            unit_price = tank_info.get("unitPrice")

            # Liters
            current_liters = pact.get("currentTotalLiters")
            if current_liters is None or float(current_liters) <= 0:
                if percentage is not None and max_cap:
                    is_propane = "propane" in product_desc.lower()
                    divisor = 80.0 if is_propane else 100.0
                    current_liters = round(float(max_cap) * (float(percentage) / divisor), 1)

            order_req = pact.get("orderRequest") or {}
            order_pending = bool(order_req.get("reqStatus") or order_req.get("requestQty"))

            print(f"  └── Tank ID: {tank_id}")
            print(f"      • Ship Account ID: {ship_account}")
            print(f"      • Product:         {product_desc}")
            print(f"      • Gauge Level:     {percentage}%")
            print(f"      • Estimated Liters:{current_liters} L")
            print(f"      • Max Capacity:    {max_cap} L")
            if unit_price is not None:
                print(f"      • Unit Price:      ${unit_price} / L")
            if order_pending:
                print(f"      • Order Pending:   YES ({order_req.get('requestQty')} L on {order_req.get('tripDate')})")
            print()

    print(f"Total tanks found: {tank_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
