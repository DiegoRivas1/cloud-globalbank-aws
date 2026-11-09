"""Estadísticas del generador de carga (lógica pura, sin red)."""
import math
import time
from collections import Counter, deque


def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    k = max(0, min(len(s) - 1, math.ceil(p / 100 * len(s)) - 1))
    return s[k]


class Stats:
    def __init__(self, window=120, clock=time.monotonic):
        self.window = window
        self.clock = clock
        self.reset()

    def reset(self):
        self.t0 = self.clock()
        self.total = 0
        self.ok = 0
        self.errors = 0
        self.dropped = 0  # peticiones que el propio generador no pudo emitir (saturación)
        self.pods = Counter()
        self.latencies = deque(maxlen=5000)
        self.buckets = {}

    def record(self, latency_s, ok, pod=None):
        sec = int(self.clock() - self.t0)
        b = self.buckets.setdefault(sec, {"n": 0, "err": 0, "lat": []})
        b["n"] += 1
        b["lat"].append(latency_s)
        self.total += 1
        if ok:
            self.ok += 1
            self.latencies.append(latency_s)
        else:
            self.errors += 1
            b["err"] += 1
        if pod:
            self.pods[pod] += 1
        for old in [k for k in self.buckets if k < sec - self.window]:
            del self.buckets[old]

    def snapshot(self):
        lat = list(self.latencies)

        def ms(v):
            return None if v is None else round(v * 1000, 1)

        timeline = [
            {"t": sec, "rps": b["n"], "errors": b["err"], "p95_ms": ms(percentile(b["lat"], 95))}
            for sec, b in sorted(self.buckets.items())
        ]
        return {
            "total": self.total,
            "ok": self.ok,
            "errors": self.errors,
            "dropped": self.dropped,
            "p50_ms": ms(percentile(lat, 50)),
            "p95_ms": ms(percentile(lat, 95)),
            "pods": dict(self.pods),
            "timeline": timeline,
        }
