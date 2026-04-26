import aiohttp
import asyncio
import os
import sys

from rigctl.rigctl import RigctlAsync
from logger.logger import logger as get_logger

logger = get_logger(__name__)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        logger.error(f"Environment variable '{name}' is not set or is empty.")
        sys.exit(1)
    return value


RIGCTL_ADDRESS = get_required_env("RIGCTL_ADDRESS")
WAVELOG_API_KEY = get_required_env("WAVELOG_API_KEY")
WAVELOG_STATION_ID = get_required_env("WAVELOG_STATION_ID")
WAVELOG_URL: str = get_required_env("WAVELOG_URL")
if not WAVELOG_URL.endswith("/"):
    WAVELOG_URL += "/"

try:
    RIGCTL_PORT = int(get_required_env("RIGCTL_PORT"))
except ValueError:
    logger.error("Environment variable 'RIGCTL_PORT' must be a valid integer.")
    sys.exit(1)


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


def wavelog_api_radio(session):
    async def _call(**kwargs):
        data = {"key": WAVELOG_API_KEY, "radio": WAVELOG_STATION_ID, **kwargs}

        async with session.post(
            url=WAVELOG_URL + "api/radio",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=data,
        ) as response:
            if response.status != 200:
                logger.warning(f"{await response.json()}")

    return _call


async def main_process():
    rig = RigctlAsync(RIGCTL_ADDRESS, RIGCTL_PORT)

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

    async with aiohttp.ClientSession() as session:
        api_callback = wavelog_api_radio(session)

        frequency = VariableWatcher("frequency", shared_state, callback=api_callback)
        mode = VariableWatcher("mode", shared_state, callback=api_callback)
        power = VariableWatcher("power", shared_state, callback=api_callback)

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
