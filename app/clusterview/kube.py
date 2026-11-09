"""Cliente mínimo de la API de Kubernetes usando el ServiceAccount del pod."""
import ssl

import aiohttp

SA_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"


class KubeError(Exception):
    def __init__(self, status, message=""):
        super().__init__(f"{status} {message}".strip())
        self.status = status


class KubeClient:
    def __init__(self, base=None, token_path=f"{SA_DIR}/token",
                 ca_path=f"{SA_DIR}/ca.crt", timeout=5):
        self.base = (base or "https://kubernetes.default.svc").rstrip("/")
        self.token_path = token_path
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = None
        self._ssl = None
        if self.base.startswith("https://"):
            try:
                self._ssl = ssl.create_default_context(cafile=ca_path)
            except (FileNotFoundError, OSError):
                self._ssl = ssl.create_default_context()

    def _headers(self):
        try:
            with open(self.token_path) as f:   # el token rota: se lee en cada petición
                return {"Authorization": f"Bearer {f.read().strip()}"}
        except OSError:
            return {}

    async def _request(self, method, path):
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        async with self._session.request(
            method, self.base + path, headers=self._headers(), ssl=self._ssl
        ) as r:
            if r.status >= 400:
                raise KubeError(r.status, (await r.text())[:150])
            return await r.json(content_type=None)

    async def get(self, path):
        return await self._request("GET", path)

    async def delete(self, path):
        return await self._request("DELETE", path)

    async def close(self):
        if self._session:
            await self._session.close()
