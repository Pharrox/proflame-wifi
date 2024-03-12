import asyncio
import json
import unittest

from websockets.server import serve

from proflame_wifi.client import ClientStatus
from proflame_wifi.manager import ProflameManager
from proflame_wifi.const import (
    MAX_FAN_SPEED,
    MAX_FLAME_HEIGHT,
    MAX_LIGHT_BRIGHTNESS,
    MIN_FAN_SPEED,
    MIN_FLAME_HEIGHT,
    MIN_LIGHT_BRIGHTNESS,
    ApiAttrs,
    OperatingMode,
    PilotMode,
    Preset,
    TemperatureUnit
)
from proflame_wifi.strings import INVALID_TEMPERATURE, UNKNOWN_TEMPERATURE_UNIT
from proflame_wifi.temperature import Temperature

from .mock_fireplace import MockFireplace
from .util import fmt_log


class ManagerTest(unittest.IsolatedAsyncioTestCase):

    async def test_create(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
            self.assertEqual(client.uri, 'ws://127.0.0.1:3838')
            self.assertDictEqual(client.full_state, {})
    
    async def test_connection(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_active()
            self.assertEqual(client.status, ClientStatus.ACTIVE)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_current_temperature_c(self):
        server = MockFireplace(**{
            ApiAttrs.TEMPERATURE_UNIT: TemperatureUnit.CELSIUS,
            ApiAttrs.CURRENT_TEMPERATURE: Temperature.celcius(30),
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.current_temperature)
            await client.wait_for_state_available(ApiAttrs.CURRENT_TEMPERATURE)
            self.assertEqual(client.current_temperature, Temperature.celcius(30))
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_current_temperature_f(self):
        server = MockFireplace(**{
            ApiAttrs.TEMPERATURE_UNIT: TemperatureUnit.FAHRENHEIT,
            ApiAttrs.CURRENT_TEMPERATURE: Temperature.fahrenheit(70),
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.current_temperature)
            await client.wait_for_state_available(ApiAttrs.CURRENT_TEMPERATURE)
            self.assertEqual(client.current_temperature, Temperature.fahrenheit(70))
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_current_temperature_unknown_unit(self):
        server = MockFireplace(**{
            ApiAttrs.TEMPERATURE_UNIT: None,
            ApiAttrs.CURRENT_TEMPERATURE: 700,
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            msg = fmt_log(client._logger, 'WARNING', UNKNOWN_TEMPERATURE_UNIT)
            with self.assertLogs(client._logger, 'WARNING') as cm:
                await client.connect()
                self.assertEqual(client.status, ClientStatus.CONNECTED)
                self.assertIsNone(client.current_temperature)
                await client.wait_for_state_available(ApiAttrs.CURRENT_TEMPERATURE)
                self.assertIsNone(client.current_temperature)
                await client.disconnect()
                self.assertEqual(client.status, ClientStatus.DISCONNECTED)
                self.assertGreaterEqual(len(cm.output), 1)
                self.assertIn(msg, cm.output)
    
    async def test_get_fan_speed(self):
        server = MockFireplace(**{ApiAttrs.FAN_SPEED: MAX_FAN_SPEED})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.fan_speed, 0)
            await client.wait_for_state_available(ApiAttrs.FAN_SPEED)
            self.assertEqual(client.fan_speed, MAX_FAN_SPEED)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_fan_speed(self):
        server = MockFireplace(**{ApiAttrs.FAN_SPEED: MAX_FAN_SPEED})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.fan_speed, 0)
            await client.wait_for_state_available(ApiAttrs.FAN_SPEED)
            self.assertEqual(client.fan_speed, MAX_FAN_SPEED)
            await client.set_fan_speed(3, True)
            self.assertEqual(client.fan_speed, 3)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_fan_speed_underrun(self):
        server = MockFireplace(**{ApiAttrs.FAN_SPEED: 3})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.fan_speed, 0)
            await client.wait_for_state_available(ApiAttrs.FAN_SPEED)
            self.assertEqual(client.fan_speed, 3)
            await client.set_fan_speed(MAX_FAN_SPEED + 1, True)
            self.assertEqual(client.fan_speed, MAX_FAN_SPEED)
            await client.set_fan_speed(MIN_FAN_SPEED - 1, True)
            self.assertEqual(client.fan_speed, MIN_FAN_SPEED)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_flame_height(self):
        server = MockFireplace(**{ApiAttrs.FLAME_HEIGHT: MAX_FLAME_HEIGHT})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.flame_height, 0)
            await client.wait_for_state_available(ApiAttrs.FLAME_HEIGHT)
            self.assertEqual(client.flame_height, MAX_FLAME_HEIGHT)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_flame_height(self):
        server = MockFireplace(**{ApiAttrs.FLAME_HEIGHT: MAX_FLAME_HEIGHT})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.flame_height, 0)
            await client.wait_for_state_available(ApiAttrs.FLAME_HEIGHT)
            self.assertEqual(client.flame_height, MAX_FLAME_HEIGHT)
            await client.set_flame_height(3, True)
            self.assertEqual(client.flame_height, 3)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_flame_height_bounds(self):
        server = MockFireplace(**{ApiAttrs.FLAME_HEIGHT: 3})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.flame_height, 0)
            await client.wait_for_state_available(ApiAttrs.FLAME_HEIGHT)
            self.assertEqual(client.flame_height, 3)
            await client.set_flame_height(MAX_FLAME_HEIGHT + 1, True)
            self.assertEqual(client.flame_height, MAX_FLAME_HEIGHT)
            await client.set_flame_height(MIN_FLAME_HEIGHT - 1, True)
            self.assertEqual(client.flame_height, MIN_FLAME_HEIGHT)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_flame_height_mode_takeover(self):
        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.THERMOSTAT,
            ApiAttrs.FLAME_HEIGHT: MAX_FLAME_HEIGHT,
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            await client.wait_for_state_available(ApiAttrs.FLAME_HEIGHT)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)
            self.assertEqual(client.flame_height, MAX_FLAME_HEIGHT)
            await client.set_operating_mode(OperatingMode.SMART, True)
            self.assertEqual(client.operating_mode, OperatingMode.SMART)
            await client.set_flame_height(3, True)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)
            self.assertEqual(client.flame_height, 3)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_light_brightness(self):
        server = MockFireplace(**{ApiAttrs.LIGHT_BRIGHTNESS: MAX_LIGHT_BRIGHTNESS})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.light_brightness, 0)
            await client.wait_for_state_available(ApiAttrs.LIGHT_BRIGHTNESS)
            self.assertEqual(client.light_brightness, MAX_LIGHT_BRIGHTNESS)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_light_brightness(self):
        server = MockFireplace(**{ApiAttrs.LIGHT_BRIGHTNESS: MAX_LIGHT_BRIGHTNESS})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.light_brightness, 0)
            await client.wait_for_state_available(ApiAttrs.LIGHT_BRIGHTNESS)
            self.assertEqual(client.light_brightness, MAX_LIGHT_BRIGHTNESS)
            await client.set_light_brightness(3, True)
            self.assertEqual(client.light_brightness, 3)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_light_brightness_bounds(self):
        server = MockFireplace(**{ApiAttrs.LIGHT_BRIGHTNESS: 3})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.light_brightness, 0)
            await client.wait_for_state_available(ApiAttrs.LIGHT_BRIGHTNESS)
            self.assertEqual(client.light_brightness, 3)
            await client.set_light_brightness(MAX_LIGHT_BRIGHTNESS + 1, True)
            self.assertEqual(client.light_brightness, MAX_LIGHT_BRIGHTNESS)
            await client.set_light_brightness(MIN_LIGHT_BRIGHTNESS - 1, True)
            self.assertEqual(client.light_brightness, MIN_LIGHT_BRIGHTNESS)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_operating_mode(self):
        server = MockFireplace(**{ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.operating_mode)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_operating_mode(self):
        server = MockFireplace(**{ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)

            await client.set_operating_mode(OperatingMode.OFF, True)
            self.assertEqual(client.operating_mode, OperatingMode.OFF)

            await client.set_operating_mode(OperatingMode.MANUAL, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)

            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)

            await client.set_operating_mode(OperatingMode.SMART, True)
            self.assertEqual(client.operating_mode, OperatingMode.SMART)

            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_pilot_mode(self):
        server = MockFireplace(**{ApiAttrs.PILOT_MODE: PilotMode.CONTINUOUS})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.pilot_mode)
            await client.wait_for_state_available(ApiAttrs.PILOT_MODE)
            self.assertEqual(client.pilot_mode, PilotMode.CONTINUOUS)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_pilot_mode(self):
        server = MockFireplace(**{ApiAttrs.PILOT_MODE: PilotMode.CONTINUOUS})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_state_available(ApiAttrs.PILOT_MODE)
            self.assertEqual(client.pilot_mode, PilotMode.CONTINUOUS)

            await client.set_pilot_mode(PilotMode.INTERMITENT, True)
            self.assertEqual(client.pilot_mode, PilotMode.INTERMITENT)

            await client.set_pilot_mode(PilotMode.CONTINUOUS, True)
            self.assertEqual(client.pilot_mode, PilotMode.CONTINUOUS)

            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_preset(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.preset)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            await client.wait_for_state_available(ApiAttrs.FLAME_HEIGHT)

            await client.set_operating_mode(OperatingMode.OFF, True)
            self.assertEqual(client.operating_mode, OperatingMode.OFF)
            self.assertEqual(client.preset, Preset.OFF)

            await client.set_operating_mode(OperatingMode.MANUAL, True)
            await client.set_flame_height(0, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 0)
            self.assertEqual(client.preset, Preset.OFF)

            await client.set_flame_height(6, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 6)
            self.assertEqual(client.preset, Preset.MANUAL)

            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)
            self.assertEqual(client.preset, Preset.THERMOSTAT)

            await client.set_operating_mode(OperatingMode.SMART, True)
            self.assertEqual(client.operating_mode, OperatingMode.SMART)
            self.assertEqual(client.preset, Preset.SMART)

            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_preset(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.preset)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            await client.wait_for_state_available(ApiAttrs.FLAME_HEIGHT)

            await client.set_operating_mode(OperatingMode.OFF, True)
            await client.set_preset(Preset.OFF, True)
            self.assertEqual(client.operating_mode, OperatingMode.OFF)
            self.assertEqual(client.preset, Preset.OFF)

            await client.set_operating_mode(OperatingMode.MANUAL, True)
            await client.set_flame_height(6, True)
            await client.set_preset(Preset.OFF, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 0)
            self.assertEqual(client.preset, Preset.OFF)

            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            await client.set_flame_height(6, True)
            await client.set_preset(Preset.OFF, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 0)
            self.assertEqual(client.preset, Preset.OFF)

            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            await client.set_flame_height(6, True)
            await client.set_preset(Preset.MANUAL, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 6)
            self.assertEqual(client.preset, Preset.MANUAL)

            await client.set_flame_height(6, True)
            await client.set_preset(Preset.THERMOSTAT, True)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)
            self.assertEqual(client.flame_height, 6)
            self.assertEqual(client.preset, Preset.THERMOSTAT)

            await client.set_preset(Preset.SMART, True)
            self.assertEqual(client.operating_mode, OperatingMode.SMART)
            self.assertEqual(client.flame_height, 6)
            self.assertEqual(client.preset, Preset.SMART)

            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_preset_flame_restore(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.preset)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            await client.wait_for_state_available(ApiAttrs.FLAME_HEIGHT)

            await client.set_operating_mode(OperatingMode.MANUAL, True)
            await client.set_flame_height(3, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 3)

            await client.set_preset(Preset.OFF, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 0)
            await client.set_preset(Preset.MANUAL, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 3)

            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            await client.set_flame_height(4, True)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)
            self.assertEqual(client.flame_height, 4)

            await client.set_preset(Preset.OFF, True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            self.assertEqual(client.flame_height, 0)
            await client.set_preset(Preset.THERMOSTAT, True)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)
            self.assertEqual(client.flame_height, 4)

            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_target_temperature_c(self):
        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL,
            ApiAttrs.TEMPERATURE_UNIT: TemperatureUnit.CELSIUS,
            ApiAttrs.TARGET_TEMPERATURE: Temperature.celcius(25),
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.target_temperature)
            await client.wait_for_state_available(ApiAttrs.TARGET_TEMPERATURE)
            self.assertIsNone(client.target_temperature)
            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            self.assertEqual(client.target_temperature, Temperature.celcius(25))
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_target_temperature_f(self):
        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL,
            ApiAttrs.TEMPERATURE_UNIT: TemperatureUnit.FAHRENHEIT,
            ApiAttrs.TARGET_TEMPERATURE: Temperature.fahrenheit(75),
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.target_temperature)
            await client.wait_for_state_available(ApiAttrs.TARGET_TEMPERATURE)
            self.assertIsNone(client.target_temperature)
            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            self.assertEqual(client.target_temperature, Temperature.fahrenheit(75))
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_target_temperature_inferred_c(self):
        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL,
            ApiAttrs.TEMPERATURE_UNIT: None,
            ApiAttrs.TARGET_TEMPERATURE: 250,
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.target_temperature)
            await client.wait_for_state_available(ApiAttrs.TARGET_TEMPERATURE)
            self.assertIsNone(client.target_temperature)
            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            self.assertEqual(client.target_temperature, Temperature.celcius(25))
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_target_temperature_inferred_f(self):
        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL,
            ApiAttrs.TEMPERATURE_UNIT: None,
            ApiAttrs.TARGET_TEMPERATURE: 750,
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.target_temperature)
            await client.wait_for_state_available(ApiAttrs.TARGET_TEMPERATURE)
            self.assertIsNone(client.target_temperature)
            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            self.assertEqual(client.target_temperature, Temperature.fahrenheit(75))
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_target_temperature_inferred_invalid(self):
        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL,
            ApiAttrs.TEMPERATURE_UNIT: None,
            ApiAttrs.TARGET_TEMPERATURE: 400,
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            msg = fmt_log(client._logger, 'WARNING', INVALID_TEMPERATURE, 40.0)
            with self.assertLogs(client._logger, 'WARNING') as cm:
                await client.connect()
                self.assertEqual(client.status, ClientStatus.CONNECTED)
                self.assertIsNone(client.target_temperature)
                await client.wait_for_state_available(ApiAttrs.TARGET_TEMPERATURE)
                self.assertIsNone(client.target_temperature)
                await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
                self.assertIsNone(client.target_temperature)
                await client.disconnect()
                self.assertEqual(client.status, ClientStatus.DISCONNECTED)
                self.assertGreaterEqual(len(cm.output), 1)
                self.assertIn(msg, cm.output)
    
    async def test_set_target_temperature_c(self):
        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.THERMOSTAT,
            ApiAttrs.TEMPERATURE_UNIT: TemperatureUnit.CELSIUS,
            ApiAttrs.TARGET_TEMPERATURE: Temperature.celcius(25),
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.target_temperature)
            await client.wait_for_state_available(ApiAttrs.TARGET_TEMPERATURE)
            self.assertEqual(client.target_temperature, Temperature.celcius(25))
            await client.set_target_temperature(Temperature.celcius(26), True)
            self.assertEqual(client.target_temperature, Temperature.celcius(26))
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_set_target_temperature_f(self):
        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.THERMOSTAT,
            ApiAttrs.TEMPERATURE_UNIT: TemperatureUnit.FAHRENHEIT,
            ApiAttrs.TARGET_TEMPERATURE: Temperature.fahrenheit(75),
        })
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.target_temperature)
            await client.wait_for_state_available(ApiAttrs.TARGET_TEMPERATURE)
            self.assertEqual(client.target_temperature, Temperature.fahrenheit(75))
            await client.set_target_temperature(Temperature.fahrenheit(78), True)
            self.assertEqual(client.target_temperature, Temperature.fahrenheit(78))
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_get_temperature_unit(self):
        server = MockFireplace(**{ApiAttrs.TEMPERATURE_UNIT: TemperatureUnit.CELSIUS})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.temperature_unit)
            await client.wait_for_state_available(ApiAttrs.TEMPERATURE_UNIT)
            self.assertEqual(client.temperature_unit, TemperatureUnit.CELSIUS)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_fireplace_is_on(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertIsNone(client.is_on())
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)

            await client.set_operating_mode(OperatingMode.OFF, True)
            self.assertFalse(client.is_on())

            await client.set_operating_mode(OperatingMode.MANUAL, True)
            self.assertTrue(client.is_on())

            await client.set_operating_mode(OperatingMode.THERMOSTAT, True)
            self.assertTrue(client.is_on())

            await client.set_operating_mode(OperatingMode.SMART, True)
            self.assertTrue(client.is_on())

            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_turn_off(self):
        server = MockFireplace(**{ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            await client.turn_off(True)
            self.assertEqual(client.operating_mode, OperatingMode.OFF)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_turn_on(self):
        server = MockFireplace(**{ApiAttrs.OPERATING_MODE: OperatingMode.OFF})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            self.assertEqual(client.operating_mode, OperatingMode.OFF)
            await client.turn_on(True)
            self.assertEqual(client.operating_mode, OperatingMode.MANUAL)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_turn_on_restore(self):
        server = MockFireplace(**{ApiAttrs.OPERATING_MODE: OperatingMode.THERMOSTAT})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)
            await client.turn_off(True)
            self.assertEqual(client.operating_mode, OperatingMode.OFF)
            await client.turn_on(True)
            self.assertEqual(client.operating_mode, OperatingMode.THERMOSTAT)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_callbacks(self):
        called = asyncio.Event()
        def handler(client: ProflameManager, field: str, value: int) -> None:
            if field == ApiAttrs.OPERATING_MODE and value == OperatingMode.MANUAL:
                called.set()

        server = MockFireplace(**{ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838, callbacks=[handler])
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            await asyncio.wait_for(called.wait(), timeout=3)
            self.assertTrue(called.is_set())
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_turn_off_fan(self):
        server = MockFireplace(**{ApiAttrs.FAN_SPEED: MAX_FAN_SPEED})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.fan_speed, 0)
            await client.wait_for_state_available(ApiAttrs.FAN_SPEED)
            self.assertEqual(client.fan_speed, MAX_FAN_SPEED)
            await client.turn_off_fan(True)
            self.assertEqual(client.fan_speed, 0)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_turn_off_light(self):
        server = MockFireplace(**{ApiAttrs.LIGHT_BRIGHTNESS: MAX_LIGHT_BRIGHTNESS})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.light_brightness, 0)
            await client.wait_for_state_available(ApiAttrs.LIGHT_BRIGHTNESS)
            self.assertEqual(client.light_brightness, MAX_LIGHT_BRIGHTNESS)
            await client.turn_off_light(True)
            self.assertEqual(client.light_brightness, 0)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_turn_on_fan(self):
        server = MockFireplace(**{ApiAttrs.FAN_SPEED: 5})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.fan_speed, 0)
            await client.wait_for_state_available(ApiAttrs.FAN_SPEED)
            self.assertEqual(client.fan_speed, 5)
            await client.turn_off_fan(True)
            self.assertEqual(client.fan_speed, 0)
            await client.turn_on_fan(True)
            self.assertEqual(client.fan_speed, 5)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_turn_on_light(self):
        server = MockFireplace(**{ApiAttrs.LIGHT_BRIGHTNESS: 5})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameManager('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            self.assertEqual(client.light_brightness, 0)
            await client.wait_for_state_available(ApiAttrs.LIGHT_BRIGHTNESS)
            self.assertEqual(client.light_brightness, 5)
            await client.turn_off_light(True)
            self.assertEqual(client.light_brightness, 0)
            await client.turn_on_light(True)
            self.assertEqual(client.light_brightness, 5)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)