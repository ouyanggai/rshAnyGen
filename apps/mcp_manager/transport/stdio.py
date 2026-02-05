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
        self._next_id = 1

    async def connect(self) -> bool:
        """启动子进程"""
        try:
            import os
            merged_env = {**os.environ, **self.env} if self.env else None
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=merged_env,
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
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("stdio transport not connected")

        req_id = self._next_id
        self._next_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }

        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # 兼容：如果子进程 stdout 被日志污染（应尽量避免），这里跳过非 JSON 行
        max_lines = 200
        for _ in range(max_lines):
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("MCP stdio server disconnected")
            raw = response_line.decode(errors="replace").strip()
            if not raw:
                continue
            try:
                resp = json.loads(raw)
            except Exception:
                continue
            # 尽量匹配请求 id；如果 server 未回传 id，也接受
            if resp.get("id") not in (None, req_id):
                continue
            return resp

        raise RuntimeError("MCP stdio server returned no valid JSON-RPC response")

    def is_connected(self) -> bool:
        """检查进程是否运行"""
        return self.process and self.process.returncode is None
