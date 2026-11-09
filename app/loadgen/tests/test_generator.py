from generator import LoadGenerator, build_request
from stats import Stats


def test_build_request():
    assert build_request("whoami") == ("GET", "/api/whoami", None)
    assert build_request("work", 80)[1] == "/api/work?ms=80"
    assert build_request("transfer")[0] == "POST"


async def test_emite_aproximadamente_rps(fake_backend):
    stats = Stats()
    gen = LoadGenerator(str(fake_backend.make_url("")), stats)
    await gen.start("whoami", rps=50, duration=1.0)
    await gen._task
    snap = stats.snapshot()
    assert 35 <= snap["total"] <= 60
    assert snap["errors"] == 0
    assert set(snap["pods"]) == {"pod-0", "pod-1"}  # reparto entre "pods"


async def test_cuenta_errores_http(fake_backend):
    fake_backend.state["fail"] = True
    stats = Stats()
    gen = LoadGenerator(str(fake_backend.make_url("")), stats)
    await gen.start("cuenta", rps=20, duration=0.5)
    await gen._task
    assert stats.errors > 0 and stats.ok == 0


async def test_backend_caido_cuenta_errores():
    stats = Stats()
    gen = LoadGenerator("http://127.0.0.1:1", stats)
    await gen.start("whoami", rps=20, duration=0.5)
    await gen._task
    assert stats.errors > 0


async def test_stop_cancela(fake_backend):
    gen = LoadGenerator(str(fake_backend.make_url("")), Stats())
    await gen.start("whoami", rps=10, duration=30)
    assert gen.running
    await gen.stop()
    assert not gen.running


async def test_no_permite_dos_pruebas(fake_backend):
    gen = LoadGenerator(str(fake_backend.make_url("")), Stats())
    await gen.start("whoami", rps=10, duration=30)
    try:
        await gen.start("whoami", rps=10, duration=30)
        assert False, "debió fallar"
    except RuntimeError:
        pass
    await gen.stop()


async def test_satura_y_descarta(fake_backend):
    stats = Stats()
    gen = LoadGenerator(str(fake_backend.make_url("")), stats, max_inflight=1)
    await gen.start("whoami", rps=400, duration=0.5)
    await gen._task
    assert stats.dropped > 0
