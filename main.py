import aiohttp
import asyncio
import os

from rigctl.rigctl import RigctlTelnet
from logger.logger import logger

logger = logger(__name__)


class VariableWatcher:
    def __init__(self, name, shared_state, callback=None):
        self.name = name
        self._value = None
        self._previous_value = None
        self.shared_state = shared_state
        self.callback = callback

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if new_value != self._previous_value:
            self._value = new_value
            self._previous_value = new_value
            self.shared_state[self.name] = new_value
            asyncio.create_task(self.on_change())

    async def on_change(self):
        logger.info(f"{self.name} changed to {self._value}")
        if self.callback:
            await self.callback(**self.shared_state)


async def radio_api_call(**kwargs):
    data = {
        "key": os.getenv("WAVELOG_API_KEY"),
        "radio": os.getenv("WAVELOG_STATION_ID"),
    }

    for key, value in kwargs.items():
        data[key] = value

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=os.getenv("WAVELOG_URL") + "api/radio",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=data,
        ) as response:
            if response.status != 200:
                logger.warning(f"{await response.json()}")


async def main_process():
    rig = RigctlTelnet(os.getenv("RIGCTL_ADDRESS"), os.getenv("RIGCTL_PORT"))

    try:
        await rig.connect()
        logger.info(
            f"Connected to {os.getenv('RIGCTL_ADDRESS')}:{os.getenv('RIGCTL_PORT')}"
        )
    except Exception:
        logger.warning(
            f"Connection to {os.getenv('RIGCTL_ADDRESS')}:{os.getenv('RIGCTL_PORT')} failed."
        )
        raise

    shared_state = {"frequency": None, "mode": None, "power": None}

    frequency = VariableWatcher("frequency", shared_state, callback=radio_api_call)
    mode = VariableWatcher("mode", shared_state, callback=radio_api_call)
    power = VariableWatcher("power", shared_state, callback=radio_api_call)

    while True:
        try:
            frequency.value = await rig.get_frequency()
            mode.value = await rig.get_mode()
            power.value = await rig.get_rfpower(frequency.value, mode.value)
        except Exception:
            logger.warning("Critical error, exiting.")
            raise
        await asyncio.sleep(1)


asyncio.run(main_process())
