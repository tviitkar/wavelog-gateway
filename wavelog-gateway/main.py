import aiohttp
import asyncio
import os
import sys
from typing import Any, Awaitable, Callable, Dict, Optional

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
    def __init__(
        self,
        name: str,
        shared_state: Dict[str, Any],
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        self._value: Optional[str] = None
        self._old_value: Optional[str] = None
        self.name = name
        self.shared_state = shared_state
        self.callback = callback

    @property
    def value(self) -> Optional[str]:
        return self._value

    @value.setter
    def value(self, value: Optional[str]) -> None:
        if value != self._old_value:
            self._value, self._old_value, self.shared_state[self.name] = (
                value,
                value,
                value,
            )
            asyncio.create_task(self.on_change())

    async def on_change(self) -> None:
        logger.info(f"{self.name} changed to {self._value}")
        await self.callback(**self.shared_state)


def wavelog_api_radio(session: aiohttp.ClientSession) -> Callable[..., Awaitable[None]]:
    async def _call(**kwargs: Any) -> None:
        data = {"key": WAVELOG_API_KEY, "radio": WAVELOG_STATION_ID, **kwargs}

        try:
            async with session.post(
                url=WAVELOG_URL + "api/radio",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=data,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status != 200:
                    logger.warning(f"Wavelog API error {response.status}: {await response.text()}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Failed to send data to Wavelog: {e}")

    return _call


async def main_process() -> None:
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

    shared_state: Dict[str, Optional[str]] = {
        "frequency": None,
        "mode": None,
        "power": None,
    }

    async with aiohttp.ClientSession() as session:
        api_callback = wavelog_api_radio(session)

        frequency = VariableWatcher("frequency", shared_state, callback=api_callback)
        mode = VariableWatcher("mode", shared_state, callback=api_callback)
        power = VariableWatcher("power", shared_state, callback=api_callback)

        while True:
            try:
                # Capture values locally to satisfy type requirements for get_rfpower
                f_val = await rig.get_frequency()
                m_val = await rig.get_mode()
                frequency.value = f_val
                mode.value = m_val
                power.value = await rig.get_rfpower(f_val, m_val)
            except (RuntimeError, TimeoutError) as err:
                logger.warning(f"{err}")
                sys.exit(1)
            await asyncio.sleep(1)


asyncio.run(main_process())
