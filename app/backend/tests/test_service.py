import pytest

import service
from service import InsufficientFunds, ValidationError


def test_to_cents_valido():
    assert service.to_cents(10.5) == 1050
    assert service.to_cents("0.01") == 1


@pytest.mark.parametrize("monto", [0, -5, None, True, "abc", float("nan"), float("inf"), 10**7])
def test_to_cents_invalido(monto):
    with pytest.raises(ValidationError):
        service.to_cents(monto)


@pytest.mark.parametrize("destino", ["", "   ", 123, None, "x" * 51])
def test_destino_invalido(destino):
    with pytest.raises(ValidationError):
        service.clean_destino(destino)


def test_transferencia_descuenta_saldo(db):
    res = service.transfer(db, "123456789", 100)
    assert res["nuevo_saldo"] == 14900.0
    assert service.get_account(db)["saldo"] == 14900.0


def test_fondos_insuficientes_no_cambia_saldo(db):
    with pytest.raises(InsufficientFunds):
        service.transfer(db, "123", 20000)
    assert service.get_account(db)["saldo"] == 15000.0


def test_transferir_saldo_exacto(db):
    service.transfer(db, "123", 15000)
    assert service.get_account(db)["saldo"] == 0.0


def test_solo_ultimos_5_movimientos(db):
    for _ in range(7):
        service.transfer(db, "123", 1)
    acc = service.get_account(db)
    assert len(acc["movimientos"]) == 5
    assert acc["saldo"] == 14993.0
