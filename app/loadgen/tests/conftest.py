import pytest
from aiohttp import web


@pytest.fixture
async def fake_backend(aiohttp_server):
    """Backend falso que alterna entre dos 'pods' y permite forzar errores."""
    state = {"n": 0, "fail": False}

    async def handler(request):
        state["n"] += 1
        if state["fail"]:
            return web.json_response({"error": "x"}, status=500)
        return web.json_response({"pod": f"pod-{state['n'] % 2}"})

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    server = await aiohttp_server(app)
    server.state = state
    return server
