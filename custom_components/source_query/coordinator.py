"""Data update coordinator for the Source Server Query integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import override

import a2s

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_PLAYER_LIST,
    DEFAULT_PLAYER_LIST,
    DEFAULT_SCAN_INTERVAL,
    QUERY_TIMEOUT,
)

type SourceQueryConfigEntry = ConfigEntry[SourceQueryCoordinator]

type ServerInfo = a2s.SourceInfo[str] | a2s.GoldSrcInfo[str]

# Errors python-a2s raises when a server is down, unreachable or sends garbage.
# Timeouts are TimeoutError; DNS failures and ICMP port-unreachable are OSError.
QUERY_ERRORS = (TimeoutError, OSError, a2s.BrokenMessageError)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceQueryData:
    """One poll's worth of server data."""

    info: ServerInfo
    # None when the player list is disabled or its query failed.
    players: list[a2s.Player[str]] | None


async def async_query_info(host: str, port: int) -> ServerInfo:
    """Send A2S_INFO to a server and return the parsed reply."""
    return await a2s.ainfo((host, port), timeout=QUERY_TIMEOUT)


class SourceQueryCoordinator(DataUpdateCoordinator[SourceQueryData]):
    """Polls one server with A2S_INFO and, optionally, A2S_PLAYER."""

    config_entry: SourceQueryConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: SourceQueryConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=config_entry.title,
            update_interval=timedelta(
                seconds=config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            ),
        )
        self.host: str = config_entry.data[CONF_HOST]
        self.port: int = config_entry.data[CONF_PORT]
        self.fetch_players: bool = config_entry.options.get(
            CONF_PLAYER_LIST, DEFAULT_PLAYER_LIST
        )

    @override
    async def _async_update_data(self) -> SourceQueryData:
        """Query the server."""
        try:
            info = await async_query_info(self.host, self.port)
        except QUERY_ERRORS as err:
            raise UpdateFailed(
                f"No reply from {self.host}:{self.port}: {err!r}"
            ) from err

        players = None
        if self.fetch_players:
            # A failed player query shouldn't mark a responding server offline.
            try:
                players = await a2s.aplayers(
                    (self.host, self.port), timeout=QUERY_TIMEOUT
                )
            except QUERY_ERRORS as err:
                _LOGGER.debug(
                    "Player query to %s:%s failed: %r", self.host, self.port, err
                )

        return SourceQueryData(info=info, players=players)
