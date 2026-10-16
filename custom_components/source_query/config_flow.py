"""Config flow for the Source Server Query integration."""

import logging
from typing import Any, override

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_PLAYER_LIST,
    DEFAULT_PLAYER_LIST,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import QUERY_ERRORS, SourceQueryConfigEntry, async_query_info

_LOGGER = logging.getLogger(__name__)

PORT_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
)


class SourceQueryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a server by host and query port."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the server address and check that it answers."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])

            await self.async_set_unique_id(f"{host.lower()}:{port}")
            self._abort_if_unique_id_configured()

            try:
                info = await async_query_info(host, port)
            except QUERY_ERRORS:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error querying %s:%s", host, port)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info.server_name or f"{host}:{port}",
                    data={CONF_HOST: host, CONF_PORT: port},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): TextSelector(),
                        vol.Required(CONF_PORT, default=DEFAULT_PORT): PORT_SELECTOR,
                    }
                ),
                user_input,
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    @override
    def async_get_options_flow(
        config_entry: SourceQueryConfigEntry,
    ) -> SourceQueryOptionsFlow:
        """Return the options flow."""
        return SourceQueryOptionsFlow()


class SourceQueryOptionsFlow(OptionsFlowWithReload):
    """Polling interval and player list toggle."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            user_input[CONF_SCAN_INTERVAL] = int(user_input[CONF_SCAN_INTERVAL])
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_SCAN_INTERVAL): NumberSelector(
                            NumberSelectorConfig(
                                min=MIN_SCAN_INTERVAL,
                                max=MAX_SCAN_INTERVAL,
                                step=1,
                                mode=NumberSelectorMode.BOX,
                                unit_of_measurement="s",
                            )
                        ),
                        vol.Required(CONF_PLAYER_LIST): BooleanSelector(),
                    }
                ),
                {
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_PLAYER_LIST: DEFAULT_PLAYER_LIST,
                    **self.config_entry.options,
                },
            ),
        )
