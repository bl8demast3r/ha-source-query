"""Tests for the bundled brand icon."""

from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

BRAND_DIR = (
    Path(__file__).parent.parent / "custom_components" / "source_query" / "brand"
)


@pytest.mark.parametrize(
    ("image", "source"),
    [
        ("icon.png", "icon.png"),
        ("icon@2x.png", "icon@2x.png"),
        # HA falls back to the light icon for dark themes and logos.
        ("dark_icon.png", "icon.png"),
        ("logo.png", "icon.png"),
    ],
)
async def test_brand_icon_served(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, image: str, source: str
) -> None:
    """HA serves the bundled icon instead of fetching from the brands CDN."""
    assert await async_setup_component(hass, "brands", {})
    client = await hass_client()

    resp = await client.get(
        f"/api/brands/integration/source_query/{image}?placeholder=no"
    )

    assert resp.status == 200
    assert await resp.read() == (BRAND_DIR / source).read_bytes()
