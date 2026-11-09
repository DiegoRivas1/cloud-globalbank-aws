"""Pruebas de integración contra PostgreSQL real.

Se ejecutan solo si hay una base de datos disponible (variable DB_HOST); en CI se
levanta un servicio Postgres y en local se omiten.
"""
import os
import threading

import pytest

import service
from db import Database
from main import create_app

pytestmark = pytest.mark.skipif(
    not os.environ.get("DB_HOST"), reason="requiere PostgreSQL (definir DB_HOST)")


@pytest.fixture
def pg():
    db = Database.from_env()
    db.init_schema(retries=10, delay=1)
    with db.connection() as conn:
        db.execute(conn, "DELETE FROM transacciones")
        db.execute(conn, "UPDATE cuenta SET saldo_centavos = 1500000 WHERE id = 1")
    return db


def test_motor_es_postgres(pg):
    assert pg.engine_name == "PostgreSQL"
    pg.ping()


def test_transferencia_persiste(pg):
    service.transfer(pg, "123456789", 250.75)
    cuenta = service.get_account(pg)
    assert cuenta["saldo"] == 14749.25
    assert cuenta["movimientos"][0]["destino"] == "123456789"


def test_fondos_insuficientes_no_modifica(pg):
    with pytest.raises(service.InsufficientFunds):
        service.transfer(pg, "x", 20000)
    assert service.get_account(pg)["saldo"] == 15000.0


def test_concurrencia_no_pierde_ni_crea_dinero(pg):
    """10 hilos x 5 transferencias de 1.00: el saldo final debe ser exacto."""
    errores = []

    def trabajador():
        try:
            for _ in range(5):
                service.transfer(pg, "concurrente", 1)
        except Exception as e:
            errores.append(e)

    hilos = [threading.Thread(target=trabajador) for _ in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert errores == []
    cuenta = service.get_account(pg)
    assert cuenta["saldo"] == 15000.0 - 50


def test_api_con_postgres(pg):
    client = create_app(pg).test_client()
    assert client.get("/readyz").get_json()["status"] == "ready"
    r = client.post("/api/transfer", json={"destino": "1", "monto": 10})
    assert r.status_code == 200
    assert client.get("/api/cuenta").get_json()["motor_db"] == "PostgreSQL"
