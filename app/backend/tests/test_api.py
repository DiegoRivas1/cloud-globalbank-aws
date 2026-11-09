def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_readyz_ok(client):
    assert client.get("/readyz").get_json()["status"] == "ready"


def test_readyz_503_si_falla_la_bd(db, monkeypatch):
    from main import create_app
    app = create_app(db)
    monkeypatch.setattr(db, "ping", lambda: (_ for _ in ()).throw(RuntimeError("caída")))
    assert app.test_client().get("/readyz").status_code == 503


def test_cuenta_estructura(client):
    data = client.get("/api/cuenta").get_json()
    assert data["saldo"] == 15000.0
    assert data["movimientos"] == []
    assert {"pod", "node", "version", "motor_db"} <= data.keys()


def test_transferencia_y_consulta(client):
    r = client.post("/api/transfer", json={"destino": "987654321", "monto": 250.75})
    assert r.status_code == 200
    data = client.get("/api/cuenta").get_json()
    assert data["saldo"] == 14749.25
    assert data["movimientos"][0]["destino"] == "987654321"


def test_transferencia_invalida(client):
    r = client.post("/api/transfer", json={"destino": "1", "monto": -1})
    assert r.status_code == 400


def test_fondos_insuficientes(client):
    r = client.post("/api/transfer", json={"destino": "1", "monto": 999999})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Fondos insuficientes"


def test_cuerpo_no_json(client):
    r = client.post("/api/transfer", data="hola", content_type="text/plain")
    assert r.status_code == 400


def test_whoami(client):
    assert {"pod", "node", "version"} <= client.get("/api/whoami").get_json().keys()


def test_work_esta_acotado(client, monkeypatch):
    monkeypatch.setenv("MAX_WORK_MS", "20")
    data = client.get("/api/work?ms=999999").get_json()
    assert data["burned_ms"] == 20
