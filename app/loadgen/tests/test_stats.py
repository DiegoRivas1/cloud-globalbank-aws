from stats import Stats, percentile


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_percentile():
    assert percentile([], 95) is None
    assert percentile([1], 95) == 1
    assert percentile(list(range(1, 101)), 50) == 50
    assert percentile(list(range(1, 101)), 95) == 95


def test_record_y_pods():
    s = Stats(clock=FakeClock())
    s.record(0.01, True, "a")
    s.record(0.02, True, "a")
    s.record(0.03, False, "b")
    snap = s.snapshot()
    assert (snap["total"], snap["ok"], snap["errors"]) == (3, 2, 1)
    assert snap["pods"] == {"a": 2, "b": 1}


def test_timeline_por_segundo():
    clk = FakeClock()
    s = Stats(clock=clk)
    for _ in range(3):
        s.record(0.010, True)
    clk.t = 1.2
    s.record(0.100, False)
    tl = s.snapshot()["timeline"]
    assert [p["t"] for p in tl] == [0, 1]
    assert tl[0]["rps"] == 3 and tl[1]["errors"] == 1
    assert tl[1]["p95_ms"] == 100.0


def test_ventana_descarta_segundos_viejos():
    clk = FakeClock()
    s = Stats(window=5, clock=clk)
    s.record(0.01, True)
    clk.t = 20
    s.record(0.01, True)
    assert [p["t"] for p in s.snapshot()["timeline"]] == [20]


def test_reset():
    s = Stats(clock=FakeClock())
    s.record(0.01, True, "a")
    s.reset()
    assert s.snapshot()["total"] == 0
