import pytest
from aiohttp import web

NS = "globalbank"


def pod(name, app, node="w1", ready=True, waiting=None, restarts=0, deleting=False):
    state = {"waiting": {"reason": waiting}} if waiting else {"running": {}}
    meta = {"name": name, "labels": {"app": app}, "creationTimestamp": "2026-11-09T06:00:00Z"}
    if deleting:
        meta["deletionTimestamp"] = "2026-11-09T06:09:00Z"
    return {
        "metadata": meta,
        "spec": {"nodeName": node},
        "status": {"phase": "Running",
                   "containerStatuses": [{"ready": ready, "restartCount": restarts, "state": state}]},
    }


PODS = {"items": [
    pod("backend-b", "backend", node="w2", ready=False, waiting="CrashLoopBackOff", restarts=4),
    pod("backend-a", "backend"),
    pod("postgres-0", "postgres", node="w2"),
]}

METRICS = {"items": [
    {"metadata": {"name": "backend-a"},
     "containers": [{"usage": {"cpu": "12345678n", "memory": "65536Ki"}}]},
]}

HPA = {
    "metadata": {"name": "backend"},
    "spec": {"minReplicas": 2, "maxReplicas": 8,
             "metrics": [{"type": "Resource",
                          "resource": {"name": "cpu", "target": {"averageUtilization": 60}}}]},
    "status": {"currentReplicas": 3, "desiredReplicas": 4,
               "currentMetrics": [{"type": "Resource",
                                   "resource": {"name": "cpu", "current": {"averageUtilization": 81}}}]},
}

EVENTS = {"items": [
    {"metadata": {"creationTimestamp": "2026-11-09T06:01:00Z"}, "lastTimestamp": "2026-11-09T06:01:00Z",
     "type": "Normal", "reason": "Scheduled", "message": "asignado",
     "involvedObject": {"kind": "Pod", "name": "backend-a"}},
    {"metadata": {"creationTimestamp": "2026-11-09T06:05:00Z"}, "lastTimestamp": "2026-11-09T06:05:00Z",
     "type": "Normal", "reason": "SuccessfulRescale", "message": "New size: 3",
     "involvedObject": {"kind": "HorizontalPodAutoscaler", "name": "backend"}},
]}


@pytest.fixture
async def fake_k8s(aiohttp_server):
    state = {"deleted": [], "metrics_status": 200}

    async def pods(_):
        return web.json_response(PODS)

    async def metrics(_):
        if state["metrics_status"] != 200:
            return web.json_response({"message": "no disponible"}, status=state["metrics_status"])
        return web.json_response(METRICS)

    async def hpa(_):
        return web.json_response(HPA)

    async def events(_):
        return web.json_response(EVENTS)

    async def pod_get(request):
        name = request.match_info["name"]
        for p in PODS["items"]:
            if p["metadata"]["name"] == name:
                return web.json_response(p)
        return web.json_response({"message": "not found"}, status=404)

    async def pod_delete(request):
        state["deleted"].append(request.match_info["name"])
        return web.json_response({"status": "Success"})

    app = web.Application()
    app.router.add_get(f"/api/v1/namespaces/{NS}/pods", pods)
    app.router.add_get(f"/apis/metrics.k8s.io/v1beta1/namespaces/{NS}/pods", metrics)
    app.router.add_get(f"/apis/autoscaling/v2/namespaces/{NS}/horizontalpodautoscalers/backend", hpa)
    app.router.add_get(f"/api/v1/namespaces/{NS}/events", events)
    app.router.add_get(f"/api/v1/namespaces/{NS}/pods/{{name}}", pod_get)
    app.router.add_delete(f"/api/v1/namespaces/{NS}/pods/{{name}}", pod_delete)
    server = await aiohttp_server(app)
    server.state = state
    return server
