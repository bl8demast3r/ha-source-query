"""The Source Server Query integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SourceQueryConfigEntry, SourceQueryCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SourceQueryConfigEntry) -> bool:
    """Set up a server from a config entry."""
    coordinator = SourceQueryCoordinator(hass, entry)
    # Game servers are routinely offline (restarts, map changes, only run on
    # weekends). Don't block setup on the first poll the way
    # async_config_entry_first_refresh would: set up anyway so the Online
    # sensor can report "off" and the rest go unavailable until it answers.
    await coordinator.async_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SourceQueryConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
