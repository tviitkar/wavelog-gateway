import aiohttp
import asyncio
import os
import sys

from rigctl.rigctl import RigctlTelnet
from logger.logger import logger

logger = logger(__name__)

RIGCTL_ADDRESS = os.getenv("RIGCTL_ADDRESS")
RIGCTL_PORT = os.getenv("RIGCTL_PORT")
WAVELOG_API_KEY = os.getenv("WAVELOG_API_KEY")
WAVELOG_STATION_ID = os.getenv("WAVELOG_STATION_ID")
WAVELOG_URL = os.getenv("WAVELOG_URL")


class VariableWatcher:
    def __init__(self, name, shared_state, callback=None):
        self._value, self._old_value = None, None
        self.name = name
        self.shared_state = shared_state
        self.callback = callback

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if value != self._old_value:
            self._value, self._old_value, self.shared_state[self.name] = (
                value,
                value,
                value,
            )
            asyncio.create_task(self.on_change())

    async def on_change(self):
        logger.info(f"{self.name} changed to {self._value}")
        if self.callback:
            await self.callback(**self.shared_state)


async def radio_api_call(**kwargs):
    data = {"key": WAVELOG_API_KEY, "radio": WAVELOG_STATION_ID, **kwargs}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=WAVELOG_URL + "api/radio",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=data,
        ) as response:
            if response.status != 200:
                logger.warning(f"{await response.json()}")


async def main_process():
    rig = RigctlTelnet(RIGCTL_ADDRESS, RIGCTL_PORT)

    try:
        logger.info(f"Connecting to {RIGCTL_ADDRESS}:{RIGCTL_PORT}")
        await rig.connect()
        connection_test = await rig.test_connection()
        if not connection_test:
            raise ConnectionError
        logger.info(f"Connected to {RIGCTL_ADDRESS}:{RIGCTL_PORT}")
    except (ConnectionRefusedError, ConnectionError, TimeoutError, RuntimeError):
        logger.warning(f"Connection to {RIGCTL_ADDRESS}:{RIGCTL_PORT} failed")
        sys.exit(1)

    shared_state = {"frequency": None, "mode": None, "power": None}

    frequency = VariableWatcher("frequency", shared_state, callback=radio_api_call)
    mode = VariableWatcher("mode", shared_state, callback=radio_api_call)
    power = VariableWatcher("power", shared_state, callback=radio_api_call)

    while True:
        try:
            frequency.value = await rig.get_frequency()
            mode.value = await rig.get_mode()
            power.value = await rig.get_rfpower(frequency.value, mode.value)
        except (RuntimeError, TimeoutError) as err:
            logger.warning(f"{err}")
            sys.exit(1)
        await asyncio.sleep(1)


asyncio.run(main_process())
