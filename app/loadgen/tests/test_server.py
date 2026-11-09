import pytest

from generator import LoadGenerator
from server import create_app
from stats import Stats

TOKEN = "secreto"


@pytest.fixture
async def client(aiohttp_client, fake_backend):
    gen = LoadGenerator(str(fake_backend.make_url("")), Stats())
    c = await aiohttp_client(create_app(gen, TOKEN, max_rps=100, max_duration=10))
    yield c
    await gen.stop()


async def test_post_sin_token_401(client):
    r = await client.post("/start", json={"rps": 5, "duration": 1})
    assert r.status == 401


async def test_status_es_publico(client):
    r = await client.get("/status")
    assert r.status == 200 and (await r.json())["running"] is False


async def test_start_invalido_400(client):
    r = await client.post("/start", json={"rps": 9999, "duration": 1}, headers={"X-Token": TOKEN})
    assert r.status == 400


async def test_start_stop_y_409(client):
    h = {"X-Token": TOKEN}
    r = await client.post("/start", json={"rps": 5, "duration": 5}, headers=h)
    assert r.status == 202
    r = await client.post("/start", json={"rps": 5, "duration": 5}, headers=h)
    assert r.status == 409
    assert (await (await client.get("/status")).json())["running"] is True
    r = await client.post("/stop", headers=h)
    assert r.status == 200
    assert (await (await client.get("/status")).json())["running"] is False


def test_token_obligatorio():
    with pytest.raises(ValueError):
        create_app(LoadGenerator("http://x", Stats()), "")
