from datetime import datetime, timezone

import pytest

from tests.conftest import EVENTS, HPA, METRICS, PODS, pod
from view import age_seconds, events_view, hpa_view, parse_cpu, parse_mem, pods_view

NOW = datetime(2026, 11, 9, 6, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("q,esperado", [
    ("250m", 250.0), ("1", 1000.0), ("0.5", 500.0), ("12345678n", 12.345678), ("500u", 0.5), (None, 0.0),
])
def test_parse_cpu(q, esperado):
    assert parse_cpu(q) == pytest.approx(esperado)


@pytest.mark.parametrize("q,esperado", [
    ("128Mi", 128.0), ("65536Ki", 64.0), ("1Gi", 1024.0), ("1048576", 1.0), (None, 0.0),
])
def test_parse_mem(q, esperado):
    assert parse_mem(q) == pytest.approx(esperado)


def test_age():
    assert age_seconds("2026-11-09T06:00:00Z", NOW) == 600
    assert age_seconds(None, NOW) is None


def test_pods_view_estado_y_metricas():
    rows = {r["name"]: r for r in pods_view(PODS, METRICS, NOW)}
    a, b = rows["backend-a"], rows["backend-b"]
    assert a["status"] == "Running" and a["ready"] is True
    assert a["cpu_m"] == 12.3 and a["mem_mi"] == 64.0 and a["age_s"] == 600
    assert b["status"] == "CrashLoopBackOff" and b["ready"] is False and b["restarts"] == 4
    assert b["cpu_m"] is None            # sin métricas para ese pod
    assert b["node"] == "w2"


def test_pods_view_ordenado_por_app_y_nombre():
    nombres = [r["name"] for r in pods_view(PODS, None, NOW)]
    assert nombres == ["backend-a", "backend-b", "postgres-0"]


def test_terminating():
    p = {"items": [pod("x", "backend", deleting=True)]}
    assert pods_view(p, None, NOW)[0]["status"] == "Terminating"


def test_hpa_view():
    h = hpa_view(HPA)
    assert h == {"name": "backend", "min": 2, "max": 8, "current": 3, "desired": 4,
                 "cpu_current": 81, "cpu_target": 60}
    assert hpa_view(None) is None


def test_hpa_sin_metricas_actuales():
    h = dict(HPA, status={"currentReplicas": 2, "desiredReplicas": 2})
    assert hpa_view(h)["cpu_current"] is None


def test_events_orden_y_limite():
    ev = events_view(EVENTS, limit=1)
    assert len(ev) == 1 and ev[0]["reason"] == "SuccessfulRescale"
    assert ev[0]["object"] == "HorizontalPodAutoscaler/backend"
    assert events_view(None) == []
