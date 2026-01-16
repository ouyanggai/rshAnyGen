"""Stdio Transport Implementation"""

import asyncio
import json
from typing import Optional
from .abc import MCPTransport


class StdioTransport(MCPTransport):
    """stdio 传输实现（本地进程通信）"""

    def __init__(self, command: str, args: list, env: dict = None):
        self.command = command
        self.args = args
        self.env = env or {}
        self.process: Optional[asyncio.subprocess.Process] = None

    async def connect(self) -> bool:
        """启动子进程"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**self.env}
            )
            return self.process.returncode is None
        except Exception:
            return False

    async def disconnect(self) -> bool:
        """终止子进程"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
        return True

    async def send_request(self, method: str, params: dict) -> dict:
        """通过 stdin/stdout 发送 JSON-RPC"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }

        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        response_line = await self.process.stdout.readline()
        return json.loads(response_line.decode())

    def is_connected(self) -> bool:
        """检查进程是否运行"""
        return self.process and self.process.returncode is None
