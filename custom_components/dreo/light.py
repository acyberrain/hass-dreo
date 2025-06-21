"""Support for Dreo ceiling fan lights."""
from __future__ import annotations
import logging
from typing import Any
import math

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.util.color_util import hs_to_rgb, rgb_to_hs

from .haimports import *
from .pydreo import PyDreo, PyDreoCeilingFan
from .pydreo.constant import DreoDeviceType
from .dreobasedevice import DreoBaseDeviceHA
from .const import DOMAIN, PYDREO_MANAGER

_LOGGER = logging.getLogger(LOGGER)

# Define color temperature range for Dreo fans (in Kelvin)
# This is a typical range, adjust if your fan is different.
DREO_FAN_LIGHT_MIN_KELVIN = 2700
DREO_FAN_LIGHT_MAX_KELVIN = 5700

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dreo light platform."""
    _LOGGER.info("Starting Dreo Light Platform")
    pydreo_manager: PyDreo = hass.data[DOMAIN][PYDREO_MANAGER]
    light_entities = []

    for pydreo_device in pydreo_manager.devices:
        if isinstance(pydreo_device, PyDreoCeilingFan):
            # Main Light
            if pydreo_device.is_feature_supported("light_on"):
                light_entities.append(DreoFanLight(pydreo_device))
            # RGB Light Ring
            if pydreo_device.is_feature_supported("atmon"):
                light_entities.append(DreoFanRGBLight(pydreo_device))

    async_add_entities(light_entities)

class DreoFanLight(DreoBaseDeviceHA, LightEntity):
    """Representation of a Dreo Fan's main light."""

    def __init__(self, pyDreoDevice: PyDreoCeilingFan):
        super().__init__(pyDreoDevice)
        self.device = pyDreoDevice
        self._attr_name = f"{super().name} Light"
        self._attr_unique_id = f"{super().unique_id}-light"
        self._attr_supported_color_modes = {ColorMode.COLOR_TEMP, ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.COLOR_TEMP
        self._attr_min_color_temp_kelvin = DREO_FAN_LIGHT_MIN_KELVIN
        self._attr_max_color_temp_kelvin = DREO_FAN_LIGHT_MAX_KELVIN
        self._attr_supported_features = LightEntityFeature.TRANSITION

    @property
    def is_on(self) -> bool:
        return self.device.light_on

    @property
    def brightness(self) -> int | None:
        if self.device.brightness is None:
            return None
        return int(self.device.brightness * 2.55)

    @property
    def color_temp_kelvin(self) -> int | None:
        if self.device.color_temp is None:
            return None
        # Dreo uses a 0-100 scale. We map this to the Kelvin range.
        return int(self.device.color_temp / 100 * (self.max_color_temp_kelvin - self.min_color_temp_kelvin) + self.min_color_temp_kelvin)

    def turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            self.device.brightness = round(kwargs[ATTR_BRIGHTNESS] / 2.55)
        
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            normalized_value = (kelvin - self.min_color_temp_kelvin) / (self.max_color_temp_kelvin - self.min
