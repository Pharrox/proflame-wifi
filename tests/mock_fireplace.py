import json

from websockets import WebSocketServerProtocol

from proflame_wifi import ApiAttrs, ApiControl, PilotMode, OperatingMode, Temperature, TemperatureUnit


class MockFireplace:
    DEFAULTS = {
        ApiAttrs.AUXILIARY: 0,
        ApiAttrs.BURNER_STATUS: 32678,
        ApiAttrs.CURRENT_TEMPERATURE: Temperature.fahrenheit(68),
        ApiAttrs.FAN_SPEED: 6,
        ApiAttrs.FIRMWARE_REVISION: 55302,
        ApiAttrs.FLAME_HEIGHT: 6,
        ApiAttrs.FREE_HEAP: 19060,
        ApiAttrs.LIGHT_BRIGHTNESS: 6,
        ApiAttrs.MIN_FREE_HEAP: 30060,
        ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL,
        ApiAttrs.PILOT_MODE: PilotMode.CONTINUOUS,
        ApiAttrs.REMOTE_CONTROL: 0,
        ApiAttrs.SPLIT_FLOW: 0,
        ApiAttrs.TARGET_TEMPERATURE: Temperature.fahrenheit(77),
        ApiAttrs.TEMPERATURE_UNIT: TemperatureUnit.FAHRENHEIT,
        ApiAttrs.WIFI_SIGNAL_STR: 50
    }


    def __init__(self, **kwargs):
        self._state = {**MockFireplace.DEFAULTS}
        self._state.update({**(kwargs or {})})

    async def serve(self, websocket: WebSocketServerProtocol, *args) -> None:

        async for message in websocket:
            if message == ApiControl.CONN_SYN:
                await websocket.send(ApiControl.CONN_ACK)
                for field in sorted(self._state.keys()):
                    value = self._state[field]
                    if isinstance(value, int):
                        await websocket.send(json.dumps({field: value}))
                    elif isinstance(value, Temperature):
                        unit = self._state.get(ApiAttrs.TEMPERATURE_UNIT, None)
                        if unit == TemperatureUnit.CELSIUS:
                            await websocket.send(json.dumps({field: int(value.to_celcius() * 10)}))
                        if unit == TemperatureUnit.FAHRENHEIT:
                            await websocket.send(json.dumps({field: int(value.to_fahrenheit() * 10)}))
            elif message == ApiControl.PING:
                await websocket.send(ApiControl.PONG)
            elif message == json.dumps({'ignore': 1}):
                continue
            else:
                await websocket.send(message)
