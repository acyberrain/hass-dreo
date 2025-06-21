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
# Corrected import path and function names
from homeassistant.util.color import (
    color_hs_to_RGB,
    color_RGB_to_hs,
)


from .haimports import *
from .pydreo import PyDreo, PyDreoCeilingFan
from .pydreo.constant import DreoDeviceType
from .dreobasedevice import DreoBaseDeviceHA
from .const import DOMAIN, PYDREO_MANAGER

_LOGGER = logging.getLogger(LOGGER)

# Define color temperature range for Dreo fans (in Kelvin)
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
            normalized_value = (kelvin - self.min_color_temp_kelvin) / (self.max_color_temp_kelvin - self.min_color_temp_kelvin)
            self.device.color_temp = round(normalized_value * 100)
            
        if not self.is_on:
            self.device.light_on = True

    def turn_off(self, **kwargs: Any) -> None:
        self.device.light_on = False

class DreoFanRGBLight(DreoBaseDeviceHA, LightEntity):
    """Representation of a Dreo Fan's RGB light ring."""

    def __init__(self, pyDreoDevice: PyDreoCeilingFan):
        super().__init__(pyDreoDevice)
        self.device = pyDreoDevice
        self._attr_name = f"{super().name} Light Ring"
        self._attr_unique_id = f"{super().unique_id}-rgb-light"
        self._attr_supported_color_modes = {ColorMode.HS}
        self._attr_color_mode = ColorMode.HS

    @property
    def is_on(self) -> bool:
        return self.device.atmon

    @property
    def brightness(self) -> int | None:
        if self.device.atmbri is None:
            return None
        # Dreo atmosphere brightness is 1-5, mapping to 1-255
        return int((self.device.atmbri / 5.0) * 255)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        if self.device.atmcolor is None:
            return None
        
        color_int = self.device.atmcolor
        blue = color_int & 255
        green = (color_int >> 8) & 255
        red = (color_int >> 16) & 255
        # Corrected function call
        return color_RGB_to_hs(red, green, blue)

    def turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            # Map 1-255 to 1-5
            self.device.atmbri = max(1, round(kwargs[ATTR_BRIGHTNESS] / 255 * 5))

        if ATTR_HS_COLOR in kwargs:
            hs = kwargs[ATTR_HS_COLOR]
            # Corrected function call
            r, g, b = color_hs_to_RGB(*hs)
            # Reconstruct the integer value. Assuming RGB.
            color_int = (r << 16) + (g << 8) + b
            self.device.atmcolor = color_int

        if not self.is_on:
            self.device.atmon = True

    def turn_off(self, **kwargs: Any) -> None:
        self.device.atmon = False
