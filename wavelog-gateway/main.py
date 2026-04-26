import aiohttp
import asyncio
import sys
from typing import Any, Awaitable, Callable, Dict, Optional

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings

from rigctl.rigctl import RigctlAsync
from logger.logger import logger as get_logger

logger = get_logger(__name__)


class Settings(BaseSettings):
    RIGCTL_ADDRESS: str
    RIGCTL_PORT: int
    WAVELOG_API_KEY: str
    WAVELOG_STATION_ID: str
    WAVELOG_URL: str

    @field_validator("WAVELOG_URL")
    @classmethod
    def ensure_trailing_slash(cls, v: str) -> str:
        """Automatically add a trailing slash to the URL if it's missing."""
        return v if v.endswith("/") else f"{v}/"


try:
    settings = Settings()
except ValidationError as e:
    logger.error(f"Configuration validation failed:\n{e}")
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
        data = {
            "key": settings.WAVELOG_API_KEY,
            "radio": settings.WAVELOG_STATION_ID,
            **kwargs,
        }

        try:
            async with session.post(
                url=settings.WAVELOG_URL + "api/radio",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=data,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status != 200:
                    logger.warning(
                        f"Wavelog API error {response.status}: {await response.text()}"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Failed to send data to Wavelog: {e}")

    return _call


async def main_process() -> None:
    rig = RigctlAsync(settings.RIGCTL_ADDRESS, settings.RIGCTL_PORT)

    try:
        logger.info(f"Connecting to {settings.RIGCTL_ADDRESS}:{settings.RIGCTL_PORT}")
        await rig.connect()
        connection_test = await rig.test_connection()
        if not connection_test:
            raise ConnectionError
        logger.info(f"Connected to {settings.RIGCTL_ADDRESS}:{settings.RIGCTL_PORT}")
    except (ConnectionRefusedError, ConnectionError, TimeoutError, RuntimeError):
        logger.warning(
            f"Connection to {settings.RIGCTL_ADDRESS}:{settings.RIGCTL_PORT} failed"
        )
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

        try:
            while True:
                try:
                    f_val = await rig.get_frequency()
                    m_val = await rig.get_mode()
                    p_val = await rig.get_rfpower(f_val, m_val)

                    frequency.value = f_val
                    mode.value = m_val
                    power.value = p_val

                except (RuntimeError, TimeoutError) as err:
                    logger.warning(f"Polling error: {err}")
                    sys.exit(1)
                await asyncio.sleep(1)
        finally:
            await rig.close()


asyncio.run(main_process())
