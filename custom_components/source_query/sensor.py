"""Sensors for the Source Server Query integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import ServerInfo, SourceQueryConfigEntry
from .entity import SourceQueryEntity

# Coordinator is used to centralize the data updates.
PARALLEL_UPDATES = 0

ATTR_PLAYER_LIST = "player_list"


@dataclass(frozen=True, kw_only=True)
class SourceQuerySensorEntityDescription(SensorEntityDescription):
    """Describes a sensor read from the A2S_INFO reply."""

    value_fn: Callable[[ServerInfo], StateType]


SENSORS: tuple[SourceQuerySensorEntityDescription, ...] = (
    SourceQuerySensorEntityDescription(
        key="server_name",
        translation_key="server_name",
        value_fn=lambda info: info.server_name,
    ),
    SourceQuerySensorEntityDescription(
        key="map",
        translation_key="map",
        value_fn=lambda info: info.map_name,
    ),
    SourceQuerySensorEntityDescription(
        key="game",
        translation_key="game",
        value_fn=lambda info: info.game,
    ),
    SourceQuerySensorEntityDescription(
        key="max_players",
        translation_key="max_players",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda info: info.max_players,
    ),
    SourceQuerySensorEntityDescription(
        key="bots",
        translation_key="bots",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda info: info.bot_count,
    ),
    SourceQuerySensorEntityDescription(
        key="latency",
        translation_key="latency",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda info: round(info.ping * 1000, 1),
    ),
    SourceQuerySensorEntityDescription(
        key="version",
        translation_key="version",
        entity_category=EntityCategory.DIAGNOSTIC,
        # GoldSrc (legacy) replies have no version field.
        value_fn=lambda info: getattr(info, "version", None),
    ),
    SourceQuerySensorEntityDescription(
        key="tags",
        translation_key="tags",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        # sv_tags can exceed the 255-character state limit; truncate.
        value_fn=lambda info: (getattr(info, "keywords", None) or "")[:255] or None,
    ),
)

PLAYERS_SENSOR = SourceQuerySensorEntityDescription(
    key="players",
    translation_key="players",
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda info: info.player_count,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SourceQueryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for a server."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SourceQueryPlayersSensor(coordinator, PLAYERS_SENSOR),
            *(SourceQuerySensor(coordinator, description) for description in SENSORS),
        ]
    )


class SourceQuerySensor(SourceQueryEntity, SensorEntity):
    """A value from the server's A2S_INFO reply."""

    entity_description: SourceQuerySensorEntityDescription

    @property
    @override
    def native_value(self) -> StateType:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data.info)


class SourceQueryPlayersSensor(SourceQuerySensor):
    """Player count, with the current player list as an attribute.

    The list is a live view only: it is excluded from the recorder, so
    player names never end up in Home Assistant's history database.
    """

    _unrecorded_attributes = frozenset({ATTR_PLAYER_LIST})

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the players connected right now."""
        if self.coordinator.data is None or self.coordinator.data.players is None:
            return None
        return {
            ATTR_PLAYER_LIST: [
                {
                    "name": player.name,
                    "score": player.score,
                    "duration": int(player.duration),
                }
                for player in self.coordinator.data.players
            ]
        }
