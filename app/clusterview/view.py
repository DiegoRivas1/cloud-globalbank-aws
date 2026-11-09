"""Transforma las respuestas JSON de la API de Kubernetes en vistas simples (lógica pura)."""
from datetime import datetime, timezone

_MEM = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024,
        "K": 1000 / 1048576, "M": 1e6 / 1048576, "G": 1e9 / 1048576}


def parse_cpu(q):
    """'250m' -> 250.0 ; '1' -> 1000.0 ; '12345678n' -> 12.3 (milicores)."""
    if q is None:
        return 0.0
    s = str(q)
    for suf, div in (("n", 1e6), ("u", 1e3), ("m", 1.0)):
        if s.endswith(suf):
            return float(s[:-1]) / div
    return float(s) * 1000


def parse_mem(q):
    """'128Mi' -> 128.0 ; '131072Ki' -> 128.0 (MiB)."""
    if q is None:
        return 0.0
    s = str(q)
    for suf in ("Ki", "Mi", "Gi", "Ti", "K", "M", "G"):
        if s.endswith(suf):
            return float(s[:-len(suf)]) * _MEM[suf]
    return float(s) / 1048576


def _ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def age_seconds(created, now):
    if not created:
        return None
    return max(0, int((now - _ts(created)).total_seconds()))


def _status(pod):
    if pod["metadata"].get("deletionTimestamp"):
        return "Terminating"
    st = pod.get("status") or {}
    for c in st.get("containerStatuses") or []:
        waiting = (c.get("state") or {}).get("waiting")
        if waiting and waiting.get("reason"):
            return waiting["reason"]
    return st.get("phase", "Unknown")


def pods_view(pods, metrics, now):
    usage = {}
    for m in (metrics or {}).get("items", []):
        cpu = sum(parse_cpu(c["usage"].get("cpu")) for c in m.get("containers", []))
        mem = sum(parse_mem(c["usage"].get("memory")) for c in m.get("containers", []))
        usage[m["metadata"]["name"]] = (cpu, mem)

    out = []
    for p in pods.get("items", []):
        meta = p["metadata"]
        cs = (p.get("status") or {}).get("containerStatuses") or []
        cpu, mem = usage.get(meta["name"], (None, None))
        out.append({
            "name": meta["name"],
            "app": (meta.get("labels") or {}).get("app"),
            "node": (p.get("spec") or {}).get("nodeName"),
            "status": _status(p),
            "ready": bool(cs) and all(c.get("ready") for c in cs),
            "restarts": sum(c.get("restartCount", 0) for c in cs),
            "age_s": age_seconds(meta.get("creationTimestamp"), now),
            "cpu_m": None if cpu is None else round(cpu, 1),
            "mem_mi": None if mem is None else round(mem, 1),
        })
    return sorted(out, key=lambda x: (x["app"] or "", x["name"]))


def hpa_view(h):
    if not h:
        return None
    spec, st = h.get("spec") or {}, h.get("status") or {}
    target = current = None
    for m in spec.get("metrics") or []:
        if m.get("type") == "Resource" and m["resource"]["name"] == "cpu":
            target = m["resource"]["target"].get("averageUtilization")
    for m in st.get("currentMetrics") or []:
        if m.get("type") == "Resource" and m["resource"]["name"] == "cpu":
            current = m["resource"]["current"].get("averageUtilization")
    return {
        "name": h["metadata"]["name"],
        "min": spec.get("minReplicas", 1),
        "max": spec.get("maxReplicas"),
        "current": st.get("currentReplicas"),
        "desired": st.get("desiredReplicas"),
        "cpu_current": current,
        "cpu_target": target,
    }


def events_view(events, limit=15):
    def when(e):
        return e.get("lastTimestamp") or e.get("eventTime") or \
            (e.get("metadata") or {}).get("creationTimestamp") or ""

    items = sorted((events or {}).get("items", []), key=when, reverse=True)[:limit]
    out = []
    for e in items:
        obj = e.get("involvedObject") or {}
        out.append({
            "time": when(e),
            "type": e.get("type"),
            "reason": e.get("reason"),
            "object": f"{obj.get('kind', '?')}/{obj.get('name', '?')}",
            "message": (e.get("message") or "")[:200],
        })
    return out
