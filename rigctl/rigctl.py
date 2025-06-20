import telnetlib3
import asyncio
import re

class RigctlTelnet:
    def __init__(self, hostname: str, port: int):
        self.hostname = hostname
        self.port = port
        self.reader = None
        self.write = None

    async def connect(self):
        self.reader, self.writer = await telnetlib3.open_connection(
            self.hostname, self.port
        )

    async def close(self):
        self.writer.close()

    async def send_command(self, command: str):
        self.writer.write(command + "\n")
        await self.writer.drain()

        response = await asyncio.wait_for(self.reader.read(512), timeout=5)
        match = re.match(r"RPRT (-\d+)", response)
        if match:
            raise RuntimeError(f"rigctld returned error code {int(match.group(1))} for command '{command}'")
        return response.strip()

    async def get_frequency(self):
        return await self.send_command("f")

    async def get_mode(self):
        response = await self.send_command("m")
        return response.splitlines()[0]

    async def get_rfpower(self, freq, mode):
        rfpower = await self.send_command("l RFPOWER")
        return await self.convert_to_watts(rfpower, freq, mode)

    async def convert_to_watts(self, rfpower, freq, mode):
        milliwats = await self.send_command(f"2 {rfpower} {freq} {mode}")
        return str(round(int(milliwats) / 1000))
