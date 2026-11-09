"""Panel del clúster: estado de pods/HPA/eventos y borrado controlado de pods."""
import asyncio
import hmac
import os
import re
from datetime import datetime, timezone

from aiohttp import web

from kube import SA_DIR, KubeClient, KubeError
from view import events_view, hpa_view, pods_view

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")


def create_app(kube, namespace, token, hpa_name="backend", killable=("backend",)):
    if not token:
        raise ValueError("CLUSTERVIEW_TOKEN es obligatorio")

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
        ns = namespace
        pods, metrics, hpa, events = await asyncio.gather(
            kube.get(f"/api/v1/namespaces/{ns}/pods"),
            kube.get(f"/apis/metrics.k8s.io/v1beta1/namespaces/{ns}/pods"),
            kube.get(f"/apis/autoscaling/v2/namespaces/{ns}/horizontalpodautoscalers/{hpa_name}"),
            kube.get(f"/api/v1/namespaces/{ns}/events"),
            return_exceptions=True,
        )
        if isinstance(pods, Exception):
            return web.json_response({"error": f"no se pudo leer los pods: {pods}"}, status=502)
        warnings = []
        if isinstance(metrics, Exception):
            warnings.append(f"métricas no disponibles: {str(metrics)[:100]}")
            metrics = None
        if isinstance(hpa, Exception):
            warnings.append(f"HPA no disponible: {str(hpa)[:100]}")
            hpa = None
        if isinstance(events, Exception):
            warnings.append(f"eventos no disponibles: {str(events)[:100]}")
            events = None
        now = datetime.now(timezone.utc)
        pod_rows = pods_view(pods, metrics, now)
        for p in pod_rows:
            p["killable"] = p["app"] in killable
        return web.json_response({
            "namespace": ns,
            "pods": pod_rows,
            "hpa": hpa_view(hpa),
            "events": events_view(events),
            "warnings": warnings,
        })

    @routes.post("/kill")
    async def kill(request):
        try:
            data = await request.json()
        except Exception:
            data = None
        name = data.get("pod") if isinstance(data, dict) else None
        if not isinstance(name, str) or not NAME_RE.match(name):
            return web.json_response({"error": "nombre de pod inválido"}, status=400)
        path = f"/api/v1/namespaces/{namespace}/pods/{name}"
        try:
            pod = await kube.get(path)
        except KubeError as e:
            code = 404 if e.status == 404 else 502
            return web.json_response({"error": f"pod no encontrado o error: {e}"}, status=code)
        app_label = ((pod.get("metadata") or {}).get("labels") or {}).get("app")
        if app_label not in killable:
            return web.json_response(
                {"error": f"solo se pueden borrar pods de: {list(killable)}"}, status=403)
        try:
            await kube.delete(path)
        except KubeError as e:
            return web.json_response({"error": str(e)}, status=502)
        return web.json_response({"deleted": name})

    app = web.Application(middlewares=[auth])
    app.add_routes(routes)

    async def close_kube(_):
        await kube.close()

    app.on_cleanup.append(close_kube)
    return app


def _namespace():
    ns = os.environ.get("NAMESPACE")
    if ns:
        return ns
    try:
        with open(f"{SA_DIR}/namespace") as f:
            return f.read().strip()
    except OSError:
        return "globalbank"


def main():
    app = create_app(
        KubeClient(base=os.environ.get("KUBE_API")),
        _namespace(),
        os.environ["CLUSTERVIEW_TOKEN"],
        hpa_name=os.environ.get("HPA_NAME", "backend"),
        killable=tuple(os.environ.get("KILLABLE_APPS", "backend").split(",")),
    )
    web.run_app(app, port=int(os.environ.get("PORT", "8100")))


if __name__ == "__main__":
    main()
