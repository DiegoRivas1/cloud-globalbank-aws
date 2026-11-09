"""Generador de carga en lazo abierto: emite `rps` peticiones por segundo sin esperar respuestas."""
import asyncio
import time

import aiohttp

MODES = ("whoami", "cuenta", "work", "transfer")


def build_request(mode, ms=50):
    if mode == "whoami":
        return "GET", "/api/whoami", None
    if mode == "cuenta":
        return "GET", "/api/cuenta", None
    if mode == "work":
        return "GET", f"/api/work?ms={int(ms)}", None
    if mode == "transfer":
        return "POST", "/api/transfer", {"destino": "loadgen", "monto": 0.01}
    raise ValueError(f"modo desconocido: {mode}")


class LoadGenerator:
    def __init__(self, target, stats, tick=0.1, max_inflight=200):
        self.target = target.rstrip("/")
        self.stats = stats
        self.tick = tick
        self.max_inflight = max_inflight
        self.params = None
        self.started_at = None
        self._task = None

    @property
    def running(self):
        return self._task is not None and not self._task.done()

    async def start(self, mode, rps, duration, ms=50):
        if self.running:
            raise RuntimeError("ya hay una prueba en curso")
        build_request(mode, ms)  # valida el modo
        self.stats.reset()
        self.params = {"mode": mode, "rps": rps, "duration": duration, "ms": ms}
        self.started_at = time.monotonic()
        self._task = asyncio.create_task(self._run(mode, rps, duration, ms))

    async def stop(self):
        if self.running:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self, mode, rps, duration, ms):
        loop = asyncio.get_running_loop()
        t0 = last = loop.time()
        due = 0.0
        pending = set()
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(
                timeout=timeout, connector=aiohttp.TCPConnector(limit=0)
            ) as session:
                while loop.time() - t0 < duration:
                    await asyncio.sleep(self.tick)
                    now = loop.time()
                    due += (now - last) * rps
                    last = now
                    n = int(due)
                    due -= n
                    for _ in range(n):
                        if len(pending) >= self.max_inflight:
                            self.stats.dropped += 1
                            continue
                        t = asyncio.create_task(self._one(session, mode, ms))
                        pending.add(t)
                        t.add_done_callback(pending.discard)
                if pending:
                    await asyncio.wait(pending, timeout=10)
        finally:
            for t in list(pending):
                t.cancel()

    async def _one(self, session, mode, ms):
        method, path, body = build_request(mode, ms)
        t = time.perf_counter()
        ok, pod = False, None
        try:
            async with session.request(method, self.target + path, json=body) as r:
                data = await r.json(content_type=None)
                ok = r.status < 400
                if isinstance(data, dict):
                    pod = data.get("pod")
        except asyncio.CancelledError:
            raise
        except Exception:
            ok = False
        self.stats.record(time.perf_counter() - t, ok, pod)
