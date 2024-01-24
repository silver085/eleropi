"""Config flow for Simple Integration integration."""
import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, core, exceptions

from .const import DOMAIN  # pylint:disable=unused-import
from .eleroapi import  EleroApiError, EleroClient, NoDeviceAvailable
_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({"name": str,})



class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Simple Integration."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    eleroApi: EleroClient

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        try:
            self.eleroApi = EleroClient(username="ha_user@local.dns" , password="ha_user")
            await self.eleroApi.update()
        except NoDeviceAvailable as e:
            errors["base"] = "No device available"
            _LOGGER.exception("Unexpected exception")
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
             )


        if not user_input:
           return self.async_show_menu(
            step_id="user",
            menu_options={
                "start_discovery": "Start Blinds discovery",
                "confirm": "Confirm configuration"
            }
        )
        else:
            _LOGGER.debug(f"{user_input}")

    async def async_step_start_discovery(self, user_input: dict[str, Any] | None = None):
        _LOGGER.debug(f"{user_input}")
        await self.eleroApi.start_discovery()
        return self.async_show_menu(
            step_id="user",
            menu_options={
                "stop_discovery": "Stop Blinds discovery"
            }
         )

    async def async_step_stop_discovery(self, user_input: dict[str, Any] | None = None):
        await self.eleroApi.stop_discovery()
        return self.async_show_menu(
            step_id="user",
            menu_options={
                "start_discovery": "Start Blinds discovery",
                "confirm": "Confirm configuration"
            }
        )

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None):
        await self.eleroApi.stop_discovery()
        await self.eleroApi.update()

        blinds_map = await self.eleroApi.get_blinds()

        return self.async_create_entry(title=f"{len(blinds_map)} elero blinds.", data={"blinds_map" : blinds_map})