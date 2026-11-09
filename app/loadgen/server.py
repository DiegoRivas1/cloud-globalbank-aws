"""API de control del generador de carga (la usa la página del dashboard)."""
import hmac
import os
import time

from aiohttp import web

from generator import MODES, LoadGenerator
from stats import Stats


def parse_start(data, max_rps, max_duration):
    if not isinstance(data, dict):
        raise ValueError("Cuerpo JSON inválido")
    mode = data.get("mode", "whoami")
    if mode not in MODES:
        raise ValueError(f"mode debe ser uno de {list(MODES)}")
    try:
        rps = float(data.get("rps"))
        duration = float(data.get("duration"))
        ms = int(data.get("ms", 50))
    except (TypeError, ValueError):
        raise ValueError("rps, duration y ms deben ser numéricos")
    if not 1 <= rps <= max_rps:
        raise ValueError(f"rps debe estar entre 1 y {max_rps}")
    if not 1 <= duration <= max_duration:
        raise ValueError(f"duration debe estar entre 1 y {max_duration} s")
    if not 1 <= ms <= 1000:
        raise ValueError("ms debe estar entre 1 y 1000")
    return mode, rps, duration, ms


def create_app(generator, token, max_rps=500, max_duration=300):
    if not token:
        raise ValueError("LOADGEN_TOKEN es obligatorio")

    @web.middleware
    async def auth(request, handler):
        if request.method == "POST":
            sent = request.headers.get("X-Token", "")
            if not hmac.compare_digest(sent.encode(), token.encode()):
                return web.json_response({"error": "token inválido"}, status=401)
        return await handler(request)

    routes = web.RouteTableDef()

    @routes.get("/healthz")
    async def healthz(_):
        return web.json_response({"status": "ok"})

    @routes.get("/status")
    async def status(_):
        elapsed = None
        if generator.params and generator.started_at:
            elapsed = round(time.monotonic() - generator.started_at, 1)
        return web.json_response({
            "running": generator.running,
            "params": generator.params,
            "elapsed": elapsed,
            "limits": {"max_rps": max_rps, "max_duration": max_duration},
            "stats": generator.stats.snapshot(),
        })

    @routes.post("/start")
    async def start(request):
        try:
            mode, rps, duration, ms = parse_start(
                await request.json(), max_rps, max_duration)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        try:
            await generator.start(mode, rps, duration, ms)
        except RuntimeError as e:
            return web.json_response({"error": str(e)}, status=409)
        return web.json_response(generator.params, status=202)

    @routes.post("/stop")
    async def stop(_):
        await generator.stop()
        return web.json_response({"running": False})

    app = web.Application(middlewares=[auth])
    app.add_routes(routes)
    return app


def main():
    target = os.environ.get("TARGET_URL", "http://backend-service:3000")
    gen = LoadGenerator(target, Stats(),
                        max_inflight=int(os.environ.get("MAX_INFLIGHT", "200")))
    app = create_app(
        gen, os.environ["LOADGEN_TOKEN"],
        max_rps=int(os.environ.get("MAX_RPS", "500")),
        max_duration=int(os.environ.get("MAX_DURATION", "300")),
    )
    web.run_app(app, port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
