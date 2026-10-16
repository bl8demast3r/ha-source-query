"""Fixtures for Source Server Query tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import a2s
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.source_query.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT

HOST = "game.example.com"
PORT = 27015


def make_info(**overrides) -> a2s.SourceInfo[str]:
    """Build an A2S_INFO reply like a real TF2 server sends."""
    fields = {
        "protocol": 17,
        "server_name": "Test Server",
        "map_name": "ctf_2fort",
        "folder": "tf",
        "game": "Team Fortress",
        "app_id": 440,
        "player_count": 2,
        "max_players": 24,
        "bot_count": 0,
        "server_type": "d",
        "platform": "l",
        "password_protected": False,
        "vac_enabled": True,
        "version": "9543365",
        "edf": 0x20,
        "ping": 0.0234,
        "keywords": "cp,increased_maxplayers",
    }
    fields.update(overrides)
    return a2s.SourceInfo(**fields)


PLAYERS = [
    a2s.Player(index=0, name="alice", score=12, duration=754.3),
    a2s.Player(index=0, name="bob", score=3, duration=61.9),
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> None:
    """Load the integration from custom_components."""
    # The recorder must be set up before hass, and enable_custom_integrations
    # pulls in hass, so resolve recorder_mock first when a test asks for it.
    if "recorder_mock" in request.fixturenames:
        request.getfixturevalue("recorder_mock")
    request.getfixturevalue("enable_custom_integrations")


@pytest.fixture
def mock_a2s() -> Generator[tuple[AsyncMock, AsyncMock]]:
    """Patch python-a2s's async queries."""
    with (
        patch("a2s.ainfo", AsyncMock(return_value=make_info())) as ainfo,
        patch("a2s.aplayers", AsyncMock(return_value=list(PLAYERS))) as aplayers,
    ):
        yield ainfo, aplayers


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured server."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Server",
        unique_id=f"{HOST}:{PORT}",
        data={CONF_HOST: HOST, CONF_PORT: PORT},
    )
