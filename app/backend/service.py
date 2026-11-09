"""Lógica de negocio, independiente de Flask."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MAX_TRANSFER = Decimal("1000000")


class ValidationError(ValueError):
    pass


class InsufficientFunds(Exception):
    pass


def to_cents(monto):
    if monto is None or isinstance(monto, bool):
        raise ValidationError("Monto inválido")
    try:
        d = Decimal(str(monto))
    except InvalidOperation:
        raise ValidationError("Monto inválido")
    if not d.is_finite() or d <= 0 or d > MAX_TRANSFER:
        raise ValidationError("Monto inválido")
    cents = int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cents <= 0:
        raise ValidationError("Monto inválido")
    return cents


def clean_destino(destino):
    if not isinstance(destino, str):
        raise ValidationError("Cuenta destino inválida")
    destino = destino.strip()
    if not 1 <= len(destino) <= 50:
        raise ValidationError("Cuenta destino inválida")
    return destino


def _fmt_fecha(valor):
    if hasattr(valor, "isoformat"):
        return valor.isoformat(sep=" ", timespec="seconds")
    return str(valor)[:19]


def get_account(db):
    with db.connection() as conn:
        saldo = db.execute(conn, "SELECT saldo_centavos FROM cuenta WHERE id = 1").fetchone()[0]
        rows = db.execute(
            conn,
            "SELECT tipo, monto_centavos, cuenta_destino, fecha "
            "FROM transacciones ORDER BY id DESC LIMIT 5",
        ).fetchall()
    return {
        "saldo": saldo / 100,
        "movimientos": [
            {"tipo": r[0], "monto": r[1] / 100, "destino": r[2], "fecha": _fmt_fecha(r[3])}
            for r in rows
        ],
    }


def transfer(db, destino, monto):
    cents = to_cents(monto)
    destino = clean_destino(destino)
    with db.connection() as conn:
        # UPDATE atómico: evita la condición de carrera entre réplicas
        cur = db.execute(
            conn,
            "UPDATE cuenta SET saldo_centavos = saldo_centavos - ? "
            "WHERE id = 1 AND saldo_centavos >= ?",
            (cents, cents),
        )
        if cur.rowcount != 1:
            raise InsufficientFunds()
        db.execute(
            conn,
            "INSERT INTO transacciones (tipo, monto_centavos, cuenta_destino) VALUES (?, ?, ?)",
            ("Transferencia enviada", cents, destino),
        )
        nuevo = db.execute(conn, "SELECT saldo_centavos FROM cuenta WHERE id = 1").fetchone()[0]
    return {"nuevo_saldo": nuevo / 100}
