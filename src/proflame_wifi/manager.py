"""
High level API for interacting with Proflame fireplaces.
"""
from logging import Logger, getLogger
from typing import Any, Callable, NoReturn, Self

from .client import ClientStatus, ProflameClient
from .const import (
    ADJUSTABLE_MODES,
    MAX_FAN_SPEED,
    MAX_FLAME_HEIGHT,
    MAX_LIGHT_BRIGHTNESS,
    MAX_TEMPERATURE,
    MIN_FAN_SPEED,
    MIN_FLAME_HEIGHT,
    MIN_LIGHT_BRIGHTNESS,
    MIN_TEMPERATURE,
    ApiAttrs,
    OperatingMode,
    PilotMode,
    Preset,
    Temperature,
    TemperatureUnit,
)
from .strings import INVALID_TEMPERATURE, UNKNOWN_TEMPERATURE_UNIT
from .temperature import Temperature
from .util import constrain

_LOGGER = getLogger(__name__)


class ProflameManager:
    """High level API for interacting with Proflame fireplaces."""

    def __init__(self,
        host: str,
        port: int | None = None,
        logger: Logger | None = None,
        ping_interval: int | None = None,
        callbacks: list[Callable[[Self, str, int], NoReturn]] | None = None
    ) -> None:
        """
        Create a new instance of the ProflamManager class.

        :param host: The DNS name or IP address of the fireplace.
        :type host: str
        :param port: The port that the fireplace API listens on.
        :type port: int or None
        :param logger: A python logger to use for generated messages.
        :type: logger: Logger or None
        :param ping_interval: The frequency (in seconds) at which keepalive
            messages should be sent to the fireplace.
        :type ping_interval: int or None
        :param callbacks: A list of callback functions which should be invoked
            any time a new state update is received from the fireplace.
        :type callbacks: list[Callable[[ProflameManager, str, int], NoReturn]]
            or None
        """

        self._logger: Logger = logger or _LOGGER
        self._stored_fan_speed = MAX_FAN_SPEED
        self._stored_flame = MAX_FLAME_HEIGHT
        self._stored_light_brightness = MAX_LIGHT_BRIGHTNESS
        self._stored_mode = OperatingMode.MANUAL
        self._stored_mode_adjustable = OperatingMode.MANUAL
        self._callbacks: list[Callable[[ProflameManager, str, int], NoReturn]] = []

        self._client = ProflameClient(
            host=host,
            port=port,
            logger=self._logger,
            ping_interval=ping_interval,
            callbacks=[self._handle_state_change],
        )

        list(map(self.register_callback, callbacks or []))

    @property
    def current_temperature(self) -> Temperature | None:
        """
        Get the current temperature reported by the unit. By default this will
        be the temperature reported to the fireplace by the Proflame remote's
        thermostat.

        Can be None if the fireplace has yet to report its recorded
        temperature.
        
        :return: The current room temperature reported to the fireplace.
        :rtype: Temperature | None
        """
        temperature = self.get_state(ApiAttrs.CURRENT_TEMPERATURE)
        if temperature:
            temperature = temperature / 10
            if self.temperature_unit == TemperatureUnit.CELSIUS:
                return Temperature.celcius(temperature)
            elif self.temperature_unit == TemperatureUnit.FAHRENHEIT:
                return Temperature.fahrenheit(temperature)
            else:
                self._logger.warning(UNKNOWN_TEMPERATURE_UNIT)
        return None

    @property
    def fan_speed(self) -> int | None:
        """
        Get the current state of the fireplace fan.

        Could be None if the fireplace has yet to report the state of the fan.
        
        :return: The current fan speed reported by the fireplace.
        :rtype: int | None
        """
        if self.operating_mode in [None, OperatingMode.OFF]:
            return 0
        return self.get_state(ApiAttrs.FAN_SPEED) or 0

    @property
    def flame_height(self) -> int | None:
        """
        Get the current flame height of the fireplace.

        Could be None if the fireplace has yet to report the state of the
        flame.
        
        :return: The current fan speed reported by the fireplace.
        :rtype: int
        """
        if self.operating_mode in [None, OperatingMode.OFF]:
            return 0
        return self.get_state(ApiAttrs.FLAME_HEIGHT)
    
    @property
    def full_state(self) -> dict[str, int]:
        """
        Retrieve a full copy of all the attributes reported by the fireplace.

        The fields in the returned object will vary depending on what the
        fireplace has reported.

        :return: A snapshot of the current fireplace state.
        :rtype: dict[str, int]
        """
        return self._client.full_state

    @property
    def light_brightness(self) -> int | None:
        """
        Get the current brightness of the primary light.

        Could be None if the fireplace has yet to report the state of the
        primary light.
        
        :return: The current brightness of the primary light.
        :rtype: int | None
        """
        if self.operating_mode in [None, OperatingMode.OFF]:
            return 0
        return self.get_state(ApiAttrs.LIGHT_BRIGHTNESS)

    @property
    def operating_mode(self) -> OperatingMode | None:
        """
        Get the current main operating mode of the fireplace.

        Possible operating modes include:

        * OFF - The main power to the fireplace and all supported accessories
          is switched off.
        * MANUAL - The fireplace is maintaining a flame height as specified by
          the user.
        * THERMOSTAT - The fireplace will try to maintain a specific
          temperature by switching the flame off and on at the desired height.
        * SMART - The fireplace will try to maintain a specific temperature by
          dynamically adjusting the height of the flame.

        Could be None if the fireplace has yet to report its current operating
        mode.

        :return: The current operating mode of the fireplace.
        :rtype: OperatingMode
        """

        return self.get_state(ApiAttrs.OPERATING_MODE)

    @property
    def pilot_mode(self) -> PilotMode | None:
        """
        Get the current pilot mode of the fireplace.

        Possible pilot modes include:

        * INTERMITENT - The pilot is lit any time the fireplace needs to be
          turned on.
        * CONTINUOUS - The pilot is always kept lit in a low power state.

        Could be None if the fireplace has yet to report its current pilot
        mode.

        :return: The pilot mode of the fireplace.
        :rtype: PilotMode
        """
        return self.get_state(ApiAttrs.PILOT_MODE)

    @property
    def preset(self) -> Preset | None:
        """
        Gets a more generalized summary of the current state of the fireplace.

        This is primarily intended for home automation systems where some of
        the raw behavior reported by the fireplace API might not reflect the
        practical state of the fireplace.

        The return values of this attribute are very similar to those returned
        by `operating_mode`. The main difference is that if the fireplace is 
        in manual mode with the flame turned off then the current fireplace
        state is reported as off (other accessories such as light or fan could
        be on).

        Could be None if the fireplace has yet to reportits current operating
        mode.

        :return: A preset which represents the current state of the fireplace
            specifically (without accessories factored in).
        :rtype: Preset
        """
        cur_mode = self.operating_mode
        if cur_mode == OperatingMode.OFF:
            return Preset.OFF
        if cur_mode == OperatingMode.MANUAL and self.flame_height == 0:
            return Preset.OFF
        if cur_mode == OperatingMode.MANUAL:
            return Preset.MANUAL
        if cur_mode == OperatingMode.THERMOSTAT:
            return Preset.THERMOSTAT
        if cur_mode == OperatingMode.SMART:
            return Preset.SMART

    @property
    def status(self) -> ClientStatus:
        """
        Get the current status of the fireplace API connection.

        :return: The current statis of the fireplace client.
        :rtype: ClientStatus
        """
        return self._client.status

    @property
    def target_temperature(self) -> Temperature | None:
        """
        Get the currently configured temperature the device is trying to
        maintain.

        Requires an active thermostat (typically the Proflam remote) to be
        actively reporting a room temperature to the fireplace.

        Only applies if the current operating mode is either THEMOSTAT of
        SMART, otherwise this will be None. Could also be None if the fireplace
        has yet to report its current target temperature.

        :return: The current temperature the fireplace is trying to maintain
            or None if the current fireplace mode does not support mainatining
            a target temperature.
        :rtype: Temperature | None
        """
        temperature = self.get_state(ApiAttrs.TARGET_TEMPERATURE)
        if self.preset in [Preset.MANUAL, Preset.OFF]:
            return None
        if temperature:
            temperature = temperature / 10
            if self.temperature_unit == TemperatureUnit.CELSIUS:
                return Temperature.celcius(temperature)
            elif self.temperature_unit == TemperatureUnit.FAHRENHEIT:
                return Temperature.fahrenheit(temperature)
            elif MIN_TEMPERATURE.to_celcius() <= temperature <= MAX_TEMPERATURE.to_celcius():
                return Temperature.celcius(temperature)
            elif MIN_TEMPERATURE.to_fahrenheit() <= temperature <= MAX_TEMPERATURE.to_fahrenheit():
                return Temperature.fahrenheit(temperature)
            else:
                self._logger.warning(INVALID_TEMPERATURE, temperature)
        return None

    @property
    def temperature_unit(self) -> TemperatureUnit | None:
        """
        Get the temperature unit the device is configured to use.

        Could be None if the fireplace has yet to report its current
        temperature unit.

        :return: The current temperature unit used by the fireplace.
        :rtype: TemperatureUnit | None
        """
        return self.get_state(ApiAttrs.TEMPERATURE_UNIT)
    
    @property
    def uri(self) -> str:
        """
        Get the formatted URI for the fireplace websocket.

        :return: The fireplace websocket URI.
        :rtype: str
        """
        return self._client.uri
    
    def _handle_state_change(self, client: ProflameClient, key: str, value: int) -> None:
        """
        Callback function for state change events reported by the internal
        client.

        Runs housekeeping tasks related to the manager and invokes all user
        registered callback functions.

        :param client: The ProflameClient object that reported the state
            update.
        :type client: ProflameClient
        :param key: The fireplace state attribute that received an update.
        :type key: str
        :param value: The new value of for the given fireplace attribute.
        :type value: int
        """

        self._track_state(key, value)
        for callback in self._callbacks:
            callback(self, key, value)

    def _track_state(self, key: str, value: int) -> None:
        """
        Track specific state changes to provide enhanced functionality.

        Primarily used for restoring previous states when switching between
        modes and more advanced functionality must be overridden.

        Provides the ability to return to a previous state at a later time.

        :param key: The fireplace state attribute that received an update.
        :type key: str
        :param value: The new value of for the given fireplace attribute.
        :type value: int
        """
        if key == ApiAttrs.FAN_SPEED and value > 0:
            self._stored_fan_speed = value
        if key == ApiAttrs.FLAME_HEIGHT and value > 0:
            self._stored_flame = value
        if key == ApiAttrs.LIGHT_BRIGHTNESS and value > 0:
            self._stored_light_brightness = value
        if key == ApiAttrs.OPERATING_MODE and value > 0:
            if not (value == OperatingMode.MANUAL and self.flame_height == 0):
                self._stored_mode = value
            if value in ADJUSTABLE_MODES and self.flame_height != 0:
                self._stored_mode_adjustable = value

    async def connect(self) -> None:
        """
        Open a connection to the fireplace.
        """
        await self._client.connect()

    async def disconnect(self) -> None:
        """
        Close the connection to the fireplace.
        """
        await self._client.disconnect()

    def is_on(self) -> bool | None:
        """
        Return true if the fireplace is on.

        Could be None if the fireplace has not reported enough information to
        determine its current state.

        :return: True if the fireplace is on, False if the fireplace is off,
            or None if the current state of the fireplace is unknown.
        :rtype: bool or None
        """
        mode = self.operating_mode
        return None if mode is None else bool(mode)
    
    def get_state(self, attribute: str) -> int | None:
        """
        Get the state of a specific attribute by its name.

        :param attribute: The name of the fireplace attribute to retrieve.
        :type attribute: str
        :return: The value of the requested attribute or None if the requested
            attribute has not been reported by the fireplace.
        :rtype: int or None
        """
        return self._client.get_state(attribute)

    def register_callback(self, callback: Callable[[Self, str, int], NoReturn]) -> None:
        """
        Register a callback that will be invoked when a state change is
        reported by the fireplace.

        :param callback: The function to invoke whenever a state change is
            reported by the fireplace.
        :type callback: Callable[[ProflameManager, str, int], NoReturn]
        """
        self._callbacks.append(callback)

    async def set_fan_speed(self, speed: int, wait: bool = False, wait_timeout: float = 3) -> int | bool | None:
        """
        Set the desired speed of the fireplace fan.
        
        :param speed: The new fireplace fan speed to set.
        :type speed: int
        :param wait: Whether to wait for the fireplace to confirm a change to
            the state of the fan.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the state of the fan.
        :type wait_timeout: float
        :return: The new state of the fan as reported by the fireplace (if wait
            is set to True), False if a timeout was encountered while waiting
            for the fireplace to confirm the state update, or None if the
            update was made without waiting for confirmation from the
            fireplace.
        :rtype: int or bool or None
        """
        constrained = constrain(speed, MIN_FAN_SPEED, MAX_FAN_SPEED)
        return await self.set_state(ApiAttrs.FAN_SPEED, constrained, wait, wait_timeout)

    async def set_flame_height(self, height: int, wait: bool = False, wait_timeout: float = 3) -> int | bool | None:
        """
        Set the desired height of the fireplace flame.
        
        Only applies when the fireplace is in a mode where the flame height is
        user adjustable.
        
        :param height: The new fireplace flame height to set.
        :type height: int
        :param wait: Whether to wait for the fireplace to confirm a change to
            the state of the flame.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the state of the flame.
        :type wait_timeout: float
        :return: The new state of the flame as reported by the fireplace (if
            wait is set to True), False if a timeout was encountered while
            waiting for the fireplace to confirm the state update, or None if
            the update was made without waiting for confirmation from the
            fireplace.
        :rtype: int or bool or None
        """
        constrained = constrain(height, MIN_FLAME_HEIGHT, MAX_FLAME_HEIGHT)
        result = await self.set_state(ApiAttrs.FLAME_HEIGHT, constrained, wait, wait_timeout)
        if constrained > 0 and self.operating_mode not in ADJUSTABLE_MODES:
            await self.set_operating_mode(self._stored_mode_adjustable, wait, wait_timeout)
        return result

    async def set_light_brightness(self, brightness: int, wait: bool = False, wait_timeout: float = 3) -> int | bool | None:
        """
        Set the desired brightness of the fireplace primary light.
        
        :param brightness: The new fireplace light brightness to set.
        :type brightness: int
        :param wait: Whether to wait for the fireplace to confirm a change to
            the state of the light.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the state of the light.
        :type wait_timeout: float
        :return: The new state of the light as reported by the fireplace (if
            wait is set to True), False if a timeout was encountered while
            waiting for the fireplace to confirm the state update, or None if
            the update was made without waiting for confirmation from the
            fireplace.
        :rtype: int or bool or None
        """
        constrained = constrain(brightness, MIN_LIGHT_BRIGHTNESS, MAX_LIGHT_BRIGHTNESS)
        return await self.set_state(ApiAttrs.LIGHT_BRIGHTNESS, constrained, wait, wait_timeout)

    async def set_operating_mode(self, mode: OperatingMode, wait: bool = False, wait_timeout: float = 3) -> OperatingMode | bool | None:
        """
        Set the primary operating mode of the fireplace unit as a whole.
        
        :param mode: The new fireplace operating mode to set.
        :type mode: OperatingMode
        :param wait: Whether to wait for the fireplace to confirm a change to
            the state of the unit.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the state of the unit.
        :type wait_timeout: float
        :return: The new state of the unit as reported by the fireplace (if
            wait is set to True), False if a timeout was encountered while
            waiting for the fireplace to confirm the state update, or None if
            the update was made without waiting for confirmation from the
            fireplace.
        :rtype: int or bool or None
        """
        return await self.set_state(ApiAttrs.OPERATING_MODE, mode, wait, wait_timeout)

    async def set_pilot_mode(self, mode: PilotMode, wait: bool = False, wait_timeout: float = 3) -> PilotMode | bool | None:
        """
        Set the operating behavior of the fireplace pilor light.
        
        :param mode: The new pilot mode to set.
        :type mode: PilotMode
        :param wait: Whether to wait for the fireplace to confirm a change to
            the state of the pilot.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the state of the pilot.
        :type wait_timeout: float
        :return: The new state of the pilot as reported by the fireplace (if
            wait is set to True), False if a timeout was encountered while
            waiting for the fireplace to confirm the state update, or None if
            the update was made without waiting for confirmation from the
            fireplace.
        :rtype: int or bool or None
        """
        return await self.set_state(ApiAttrs.PILOT_MODE, mode, wait, wait_timeout)

    async def set_preset(self, preset: Preset, wait: bool = False, wait_timeout: float = 3) -> None:
        """
        Set the fireplace state to a general desired state.

        This is primarily intended for home automation systems and provides a
        warpper for functionality that makes transitioning between states
        easier.

        It provides the basic functionality of operating modes while targeting
        the fireplace specifically, without affecting any connected
        accessories.

        For example, when switching to an off state with accessories running
        this will turn off the flame while leaving accessories running. When
        switching back to an on state the flame values will be retored to what
        was in use before getting turned off.
        
        :param preset: The name of the preset mode to switch to.
        :type preset: Preset
        :param wait: Whether to wait for the fireplace to confirm changes made
            to its state.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back updates to its state. If multiple updates
            need to made made to satisfy the preset each update will wait this
            duration.
        :type wait_timeout: float
        """
        if preset == Preset.OFF:
            if self.operating_mode != OperatingMode.OFF:
                await self.set_flame_height(0, wait, wait_timeout)
                await self.set_operating_mode(OperatingMode.MANUAL, wait, wait_timeout)
        if preset == Preset.MANUAL:
            if self.flame_height == 0:
                await self.set_flame_height(self._stored_flame, wait, wait_timeout)
            await self.set_operating_mode(OperatingMode.MANUAL, wait, wait_timeout)
        if preset == Preset.THERMOSTAT:
            if self.flame_height == 0:
                await self.set_flame_height(self._stored_flame, wait, wait_timeout)
            await self.set_operating_mode(OperatingMode.THERMOSTAT, wait, wait_timeout)
        if preset == Preset.SMART:
            await self.set_operating_mode(OperatingMode.SMART, wait, wait_timeout)
    
    async def set_state(self, attribute: str, value: int, wait: bool = False, wait_timeout: float = 3) -> int | bool | None:
        """
        Set the state of a specific attribute by its name.

        :param attribute: The name of the fireplace attribute to set.
        :type attribute: str
        :param value: The new value to set for the specifies attribute.
        :type value: int
        :return: The new state of the attribute as reported by the fireplace
            (if wait is set to True), False if a timeout was encountered while
            waiting for the fireplace to confirm the state update, or None if
            the update was made without waiting for confirmation from the
            fireplace.
        :rtype: int or bool or None
        """
        return await self._client.set_state(attribute, value, wait, wait_timeout)

    async def set_target_temperature(self, temperature: Temperature, wait: bool = False, wait_timeout: float = 3) -> Temperature | bool | None:
        """
        Set the desired temperature for themostat based modes.

        :param temperature: The new temperature that the fireplace should try
            to maintain.
        :type temperature: Temperature
        :param wait: Whether to wait for the fireplace to confirm a change to
            the target temperature.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the state of the target
            temperature.
        :type wait_timeout: float
        :return: The new target temperature as reported by the fireplace (if
            wait is set to True), False if a timeout was encountered while
            waiting for the fireplace to confirm the state update, or None if
            the update was made without waiting for confirmation from the
            fireplace.
        :rtype: Temperature or bool or None
        """
        if self.temperature_unit == TemperatureUnit.CELSIUS:
            requested = temperature.to_celcius()
            min_temp = MIN_TEMPERATURE.to_celcius()
            max_temp = MAX_TEMPERATURE.to_celcius()
            constrained = constrain(requested, min_temp, max_temp)
            result = await self.set_state(ApiAttrs.TARGET_TEMPERATURE, int(constrained * 10), wait, wait_timeout)
            return Temperature.celcius(result / 10) if isinstance(result, int) else result
        if self.temperature_unit == TemperatureUnit.FAHRENHEIT:
            requested = temperature.to_fahrenheit()
            min_temp = MIN_TEMPERATURE.to_fahrenheit()
            max_temp = MAX_TEMPERATURE.to_fahrenheit()
            constrained = constrain(requested, min_temp, max_temp)
            result = await self.set_state(ApiAttrs.TARGET_TEMPERATURE, int(constrained * 10), wait, wait_timeout)
            return Temperature.fahrenheit(result / 10) if isinstance(result, int) else result

    async def turn_off(self, wait: bool = False, wait_timeout: float = 3) -> None:
        """
        Turn off the main power of the fireplace unit.

        :param wait: Whether to wait for the fireplace to confirm a change to
            the requested change.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the requested change.
        :type wait_timeout: float
        """
        await self.set_operating_mode(OperatingMode.OFF, wait, wait_timeout)

    async def turn_off_fan(self, wait: bool = False, wait_timeout: float = 3) -> None:
        """
        Set the speed of the fan to 0

        :param wait: Whether to wait for the fireplace to confirm a change to
            the requested change.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the requested change.
        :type wait_timeout: float
        """
        await self.set_fan_speed(0, wait, wait_timeout)

    async def turn_off_light(self, wait: bool = False, wait_timeout: float = 3) -> None:
        """
        Set the brightness of the primary light to 0.

        :param wait: Whether to wait for the fireplace to confirm a change to
            the requested change.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the requested change.
        :type wait_timeout: float
        """
        await self.set_light_brightness(0, wait, wait_timeout)

    async def turn_on(self, wait: bool = False, wait_timeout: float = 3) -> None:
        """
        Turn on the main power of the fireplace unit.

        :param wait: Whether to wait for the fireplace to confirm a change to
            the requested change.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the requested change.
        :type wait_timeout: float
        """
        await self.set_operating_mode(self._stored_mode, wait, wait_timeout)

    async def turn_on_fan(self, wait: bool = False, wait_timeout: float = 3) -> None:
        """
        Set the speed of the fan to the last known active speed.

        :param wait: Whether to wait for the fireplace to confirm a change to
            the requested change.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the requested change.
        :type wait_timeout: float
        """
        await self.set_fan_speed(self._stored_fan_speed, wait, wait_timeout)

    async def turn_on_light(self, wait: bool = False, wait_timeout: float = 3) -> None:
        """
        Set the brightness of the primary light to last known active
        brightness.

        :param wait: Whether to wait for the fireplace to confirm a change to
            the requested change.
        :type wait: bool
        :param wait_timeout: The duration (in seconds) to wait for the
            fireplace to report back an update on the requested change.
        :type wait_timeout: float
        """
        await self.set_light_brightness(self._stored_light_brightness, wait, wait_timeout)
    
    async def wait_for_active(self) -> None:
        """
        Wait for the fireplace connection to become active.
        """
        await self._client.wait_for_active()

    async def wait_for_state_available(self, field) -> int:
        """
        Wait until a specified state key is available from the API.

        On connection the fireplace will send multiple messages after a
        connection becomes active to report the state of all supported
        functionality.

        :param field: The attribute that you want to wait to become available
            from the fireplace.
        :type wait: str
        """
        return await self._client.wait_for_state_available(field)
