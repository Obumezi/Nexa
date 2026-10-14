from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests


BASE_URL = (
    "https://ne-cc084a3067bf4a9bbe7c0a4bc5e5ffee."
    "ecs.us-east-1.on.aws"
)


def post_json(path: str, payload: dict) -> dict:
    url = f"{BASE_URL}{path}"

    print(f"\nPOST {url}")

    response = requests.post(
        url,
        json=payload,
        timeout=30,
    )

    print(f"Status: {response.status_code}")

    if not response.ok:
        print(response.text)
        response.raise_for_status()

    data = response.json()
    print(data)

    return data


def seed_presence() -> None:
    post_json(
        "/api/v1/presence",
        {
            "occupant_name": "Obumneme",
            "status": "home",
            "note": "Home and available.",
        },
    )


def seed_visitor() -> None:
    now = datetime.now(UTC)

    expected_start = now + timedelta(hours=2)
    expected_end = now + timedelta(hours=3)

    post_json(
        "/api/v1/visitors",
        {
            "name": "Ada Okafor",
            "purpose": "Family visit",
            "expected_start": expected_start.isoformat(),
            "expected_end": expected_end.isoformat(),
            "notes": "Expected through the front entrance.",
        },
    )


def seed_delivery() -> None:
    expected_at = datetime.now(UTC) + timedelta(hours=4)

    post_json(
        "/api/v1/deliveries",
        {
            "description": "MacBook Pro",
            "carrier": "DHL",
            "tracking_reference": "NEXA-DEMO-DHL-001",
            "expected_at": expected_at.isoformat(),
            "delivery_location": "Front door",
            "notes": "Demo delivery for the Nexa hackathon.",
        },
    )


def main() -> None:
    print("=" * 60)
    print("NEXA LIVE DEMO DATA SEED")
    print("=" * 60)

    print("\nSeeding presence...")
    seed_presence()

    print("\nSeeding visitor...")
    seed_visitor()

    print("\nSeeding delivery...")
    seed_delivery()

    print("\n" + "=" * 60)
    print("LIVE DEMO DATA SEEDED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()