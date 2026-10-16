"""Binary sensors for the Source Server Query integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ServerInfo, SourceQueryConfigEntry
from .entity import SourceQueryEntity

# Coordinator is used to centralize the data updates.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SourceQueryBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a binary sensor read from the A2S_INFO reply."""

    value_fn: Callable[[ServerInfo], bool]


BINARY_SENSORS: tuple[SourceQueryBinarySensorEntityDescription, ...] = (
    SourceQueryBinarySensorEntityDescription(
        key="password_protected",
        translation_key="password_protected",
        value_fn=lambda info: info.password_protected,
    ),
    SourceQueryBinarySensorEntityDescription(
        key="vac",
        translation_key="vac",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda info: info.vac_enabled,
    ),
)

ONLINE_SENSOR = BinarySensorEntityDescription(
    key="online",
    translation_key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SourceQueryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors for a server."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SourceQueryOnlineSensor(coordinator, ONLINE_SENSOR),
            *(
                SourceQueryBinarySensor(coordinator, description)
                for description in BINARY_SENSORS
            ),
        ]
    )


class SourceQueryBinarySensor(SourceQueryEntity, BinarySensorEntity):
    """A flag from the server's A2S_INFO reply."""

    entity_description: SourceQueryBinarySensorEntityDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the flag."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data.info)


class SourceQueryOnlineSensor(SourceQueryEntity, BinarySensorEntity):
    """On while the server answers queries; never unavailable."""

    @property
    @override
    def available(self) -> bool:
        """Stay available so "offline" reads as off, not unavailable."""
        return True

    @property
    @override
    def is_on(self) -> bool:
        """Return whether the last poll got a reply."""
        return self.coordinator.last_update_success
