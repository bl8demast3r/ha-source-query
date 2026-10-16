"""Tests for the config and options flows."""

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.source_query.const import CONF_PLAYER_LIST, DOMAIN
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import HOST, PORT


async def test_user_flow(hass: HomeAssistant, mock_a2s) -> None:
    """A reachable server is added under its own name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: f" {HOST} ", CONF_PORT: float(PORT)}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Server"
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: PORT}
    assert result["result"].unique_id == f"{HOST}:{PORT}"


async def test_user_flow_cannot_connect_then_recover(
    hass: HomeAssistant, mock_a2s
) -> None:
    """A timeout shows an error and the user can retry."""
    ainfo, _ = mock_a2s
    ainfo.side_effect = TimeoutError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    ainfo.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_unknown_error(hass: HomeAssistant, mock_a2s) -> None:
    """An unexpected exception is reported, not raised."""
    ainfo, _ = mock_a2s
    ainfo.side_effect = ValueError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT}
    )
    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_a2s, config_entry: MockConfigEntry
) -> None:
    """The same host and port can't be added twice, regardless of case."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST.upper(), CONF_PORT: PORT}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant, mock_a2s, config_entry: MockConfigEntry
) -> None:
    """Changing options reloads the entry with the new interval."""
    _, aplayers = mock_a2s
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    aplayers.reset_mock()
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 60.0, CONF_PLAYER_LIST: False}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_SCAN_INTERVAL: 60, CONF_PLAYER_LIST: False}
    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = config_entry.runtime_data
    assert coordinator.update_interval.total_seconds() == 60
    assert not coordinator.fetch_players
    # The reload polled again, without the player query.
    aplayers.assert_not_called()


async def test_options_flow_suggests_defaults(
    hass: HomeAssistant, mock_a2s: tuple[AsyncMock, AsyncMock], config_entry
) -> None:
    """A fresh entry's options form is prefilled with the defaults."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    suggested = {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
    }
    assert suggested == {CONF_SCAN_INTERVAL: 30, CONF_PLAYER_LIST: True}
