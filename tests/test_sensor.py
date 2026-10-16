"""Tests for the entities and polling behaviour."""

from datetime import timedelta

import a2s
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import make_info


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up the config entry."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Advance past one default polling interval."""
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_entities(hass: HomeAssistant, mock_a2s, config_entry) -> None:
    """Every A2S_INFO field lands in the right entity."""
    await setup_entry(hass, config_entry)

    expected = {
        "binary_sensor.test_server_online": STATE_ON,
        "binary_sensor.test_server_password_protected": STATE_OFF,
        "binary_sensor.test_server_vac_secured": STATE_ON,
        "sensor.test_server_players": "2",
        "sensor.test_server_max_players": "24",
        "sensor.test_server_bots": "0",
        "sensor.test_server_server_name": "Test Server",
        "sensor.test_server_map": "ctf_2fort",
        "sensor.test_server_game": "Team Fortress",
        "sensor.test_server_latency": "23.4",
        "sensor.test_server_version": "9543365",
    }
    for entity_id, state in expected.items():
        assert hass.states.get(entity_id).state == state, entity_id

    players = hass.states.get("sensor.test_server_players")
    assert players.attributes["player_list"] == [
        {"name": "alice", "score": 12, "duration": 754},
        {"name": "bob", "score": 3, "duration": 61},
    ]


async def test_tags_disabled_by_default(
    hass: HomeAssistant, mock_a2s, config_entry, entity_registry: er.EntityRegistry
) -> None:
    """Tags are registered but disabled until the user turns them on."""
    await setup_entry(hass, config_entry)

    assert hass.states.get("sensor.test_server_tags") is None
    entry = entity_registry.async_get("sensor.test_server_tags")
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.parametrize(
    "error",
    [TimeoutError(), ConnectionRefusedError(), a2s.BrokenMessageError("junk")],
)
async def test_server_goes_offline_and_returns(
    hass: HomeAssistant,
    mock_a2s,
    config_entry,
    freezer: FrozenDateTimeFactory,
    error: Exception,
) -> None:
    """Offline reads as Online=off; other entities go unavailable, then recover."""
    ainfo, _ = mock_a2s
    await setup_entry(hass, config_entry)

    ainfo.side_effect = error
    await poll(hass, freezer)
    assert hass.states.get("binary_sensor.test_server_online").state == STATE_OFF
    assert hass.states.get("sensor.test_server_players").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.test_server_map").state == STATE_UNAVAILABLE

    ainfo.side_effect = None
    ainfo.return_value = make_info(map_name="pl_badwater", player_count=5)
    await poll(hass, freezer)
    assert hass.states.get("binary_sensor.test_server_online").state == STATE_ON
    assert hass.states.get("sensor.test_server_players").state == "5"
    assert hass.states.get("sensor.test_server_map").state == "pl_badwater"


async def test_offline_at_startup(
    hass: HomeAssistant, mock_a2s, config_entry, freezer: FrozenDateTimeFactory
) -> None:
    """A server that's down when HA starts still sets up and reports offline."""
    ainfo, _ = mock_a2s
    ainfo.side_effect = TimeoutError
    await setup_entry(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("binary_sensor.test_server_online").state == STATE_OFF
    assert hass.states.get("sensor.test_server_players").state == STATE_UNAVAILABLE

    ainfo.side_effect = None
    await poll(hass, freezer)
    assert hass.states.get("binary_sensor.test_server_online").state == STATE_ON
    assert hass.states.get("sensor.test_server_players").state == "2"


async def test_player_query_failure_keeps_server_online(
    hass: HomeAssistant, mock_a2s, config_entry
) -> None:
    """If only A2S_PLAYER fails, the count stays and the list is dropped."""
    _, aplayers = mock_a2s
    aplayers.side_effect = TimeoutError
    await setup_entry(hass, config_entry)

    assert hass.states.get("binary_sensor.test_server_online").state == STATE_ON
    players = hass.states.get("sensor.test_server_players")
    assert players.state == "2"
    assert "player_list" not in players.attributes


async def test_player_list_disabled(hass: HomeAssistant, mock_a2s) -> None:
    """With the option off, A2S_PLAYER is never sent."""
    _, aplayers = mock_a2s
    entry = MockConfigEntry(
        domain="source_query",
        title="Test Server",
        data={"host": "10.0.0.5", "port": 27015},
        options={"scan_interval": 30, "player_list": False},
    )
    await setup_entry(hass, entry)

    aplayers.assert_not_called()
    assert "player_list" not in hass.states.get("sensor.test_server_players").attributes


async def test_tags_truncated(
    hass: HomeAssistant, mock_a2s, config_entry, entity_registry: er.EntityRegistry
) -> None:
    """Long sv_tags values are cut to the 255-character state limit."""
    ainfo, _ = mock_a2s
    ainfo.return_value = make_info(keywords="x" * 400)
    entity_registry.async_get_or_create(
        "sensor",
        "source_query",
        f"{config_entry.entry_id}_tags",
        suggested_object_id="test_server_tags",
        disabled_by=None,
    )
    await setup_entry(hass, config_entry)

    assert hass.states.get("sensor.test_server_tags").state == "x" * 255


async def test_player_list_not_recorded(
    recorder_mock: Recorder, hass: HomeAssistant, mock_a2s, config_entry
) -> None:
    """Player names are shown live but never written to the history database."""
    start = dt_util.utcnow()
    await setup_entry(hass, config_entry)
    assert "player_list" in hass.states.get("sensor.test_server_players").attributes

    await async_wait_recording_done(hass)
    history = await hass.async_add_executor_job(
        get_significant_states,
        hass,
        start,
        None,
        ["sensor.test_server_players"],
    )
    recorded = history["sensor.test_server_players"]
    assert recorded
    assert recorded[-1].state == "2"
    for state in recorded:
        assert "player_list" not in state.attributes
