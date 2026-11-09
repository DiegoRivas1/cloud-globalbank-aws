import math
import os
import socket
import time

from flask import Flask, jsonify, request

import service
from db import Database


def _meta():
    return {
        "pod": os.environ.get("HOSTNAME", socket.gethostname()),
        "node": os.environ.get("NODE_NAME", "local"),
        "version": os.environ.get("APP_VERSION", "dev"),
    }


def create_app(db=None):
    app = Flask(__name__)
    db = db or Database.from_env()
    db.init_schema(retries=int(os.environ.get("DB_INIT_RETRIES", "10")))

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/readyz")
    def readyz():
        try:
            db.ping()
        except Exception:
            return jsonify(status="db_unavailable"), 503
        return jsonify(status="ready")

    @app.get("/api/whoami")
    def whoami():
        return jsonify(**_meta())

    @app.get("/api/cuenta")
    def cuenta():
        return jsonify(**service.get_account(db), motor_db=db.engine_name, **_meta())

    @app.post("/api/transfer")
    def transfer():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Cuerpo JSON inválido"), 400
        try:
            res = service.transfer(db, data.get("destino"), data.get("monto"))
        except service.ValidationError as e:
            return jsonify(error=str(e)), 400
        except service.InsufficientFunds:
            return jsonify(error="Fondos insuficientes"), 400
        return jsonify(mensaje="Transferencia exitosa", **res, **_meta())

    @app.get("/api/work")
    def work():
        """Consume CPU durante `ms` milisegundos (acotado) para disparar el HPA."""
        tope = int(os.environ.get("MAX_WORK_MS", "1000"))
        ms = max(1, min(request.args.get("ms", default=200, type=int), tope))
        fin = time.perf_counter() + ms / 1000
        x = 0.0
        while time.perf_counter() < fin:
            x += math.sqrt(12345.678)
        return jsonify(burned_ms=ms, **_meta())

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "3000")))
