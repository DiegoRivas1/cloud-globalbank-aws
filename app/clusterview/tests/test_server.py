import pytest

from kube import KubeClient
from server import create_app

TOKEN = "t0ken"


@pytest.fixture
async def client(aiohttp_client, fake_k8s):
    kube = KubeClient(base=str(fake_k8s.make_url("")), token_path="/no/existe")
    return await aiohttp_client(create_app(kube, "globalbank", TOKEN))


async def test_status_completo(client):
    r = await client.get("/status")
    d = await r.json()
    assert r.status == 200 and d["warnings"] == []
    assert [p["name"] for p in d["pods"]] == ["backend-a", "backend-b", "postgres-0"]
    assert {p["name"]: p["killable"] for p in d["pods"]} == {
        "backend-a": True, "backend-b": True, "postgres-0": False}
    assert d["hpa"]["desired"] == 4
    assert d["events"][0]["reason"] == "SuccessfulRescale"


async def test_status_sin_metrics_server_degrada(client, fake_k8s):
    fake_k8s.state["metrics_status"] = 503
    d = await (await client.get("/status")).json()
    assert len(d["warnings"]) == 1 and "métricas" in d["warnings"][0]
    assert d["pods"][0]["cpu_m"] is None and d["hpa"] is not None


async def test_kill_exige_token(client):
    r = await client.post("/kill", json={"pod": "backend-a"})
    assert r.status == 401


async def test_kill_pod_backend(client, fake_k8s):
    r = await client.post("/kill", json={"pod": "backend-a"}, headers={"X-Token": TOKEN})
    assert r.status == 200 and (await r.json())["deleted"] == "backend-a"
    assert fake_k8s.state["deleted"] == ["backend-a"]


async def test_kill_rechaza_pods_que_no_son_backend(client, fake_k8s):
    r = await client.post("/kill", json={"pod": "postgres-0"}, headers={"X-Token": TOKEN})
    assert r.status == 403 and fake_k8s.state["deleted"] == []


async def test_kill_pod_inexistente(client):
    r = await client.post("/kill", json={"pod": "no-existe"}, headers={"X-Token": TOKEN})
    assert r.status == 404


@pytest.mark.parametrize("body", [{}, {"pod": 5}, {"pod": "../etc"}, {"pod": "UPPER"}, [1]])
async def test_kill_nombre_invalido(client, body):
    r = await client.post("/kill", json=body, headers={"X-Token": TOKEN})
    assert r.status == 400


def test_token_obligatorio():
    with pytest.raises(ValueError):
        create_app(KubeClient(base="http://x"), "ns", "")
