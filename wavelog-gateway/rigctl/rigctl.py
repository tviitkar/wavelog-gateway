import asyncio
import re


class RigctlAsync:
    def __init__(self, hostname: str, port: int):
        self.hostname, self.port = hostname, port
        self.reader, self.writer = None, None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(
            self.hostname, self.port
        )

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def send_command(self, command: str):
        if not self.writer:
            raise ConnectionError("Not connected to rigctld.")

        try:
            self.writer.write(f"{command}\n".encode())
            await self.writer.drain()

            data = await asyncio.wait_for(self.reader.read(1024), timeout=5)
            response = data.decode().strip()

            if "RPT" in response:
                match = re.search(r"RPRT (-?\d+)", response)
                if match and match.group(1) != "0":
                    raise RuntimeError(f"rigctld error {match.group(1)} on: {command}")

            return response
        except asyncio.TimeoutError:
            raise TimeoutError(f"rigctld timed out on command: {command}")

    async def test_connection(self):
        return await self.send_command("f")

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
