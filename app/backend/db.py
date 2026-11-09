"""Acceso a datos: SQLite en local/tests, PostgreSQL en Kubernetes."""
import os
import sqlite3
import time
from contextlib import contextmanager


class Database:
    def __init__(self, sqlite_path=None, pg_params=None):
        self.pg_params = pg_params
        self.is_pg = pg_params is not None
        self.sqlite_path = sqlite_path or "banco_local.db"

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        host = env.get("DB_HOST")
        if host:
            return cls(pg_params={
                "host": host,
                "port": int(env.get("DB_PORT", "5432")),
                "dbname": env.get("DB_NAME", "banco_db"),
                "user": env.get("DB_USER", "postgres"),
                "password": env["DB_PASSWORD"],  # obligatoria: sin valor por defecto
                "connect_timeout": 3,
            })
        return cls(sqlite_path=env.get("DB_PATH", "banco_local.db"))

    @property
    def engine_name(self):
        return "PostgreSQL" if self.is_pg else "SQLite"

    @contextmanager
    def connection(self):
        if self.is_pg:
            import psycopg2
            conn = psycopg2.connect(**self.pg_params)
        else:
            conn = sqlite3.connect(self.sqlite_path, timeout=5)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, conn, sql, params=()):
        if self.is_pg:
            sql = sql.replace("?", "%s")
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur

    def ping(self):
        with self.connection() as conn:
            self.execute(conn, "SELECT 1").fetchone()

    def init_schema(self, retries=1, delay=2.0):
        """Crea tablas y la cuenta demo. Reintenta por si la BD aún está arrancando."""
        for intento in range(1, retries + 1):
            try:
                self._init_schema()
                return
            except Exception:
                if intento == retries:
                    raise
                time.sleep(delay)

    def _init_schema(self):
        pk = "SERIAL PRIMARY KEY" if self.is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
        with self.connection() as conn:
            self.execute(conn, """CREATE TABLE IF NOT EXISTS cuenta (
                id INTEGER PRIMARY KEY,
                titular TEXT NOT NULL,
                saldo_centavos BIGINT NOT NULL CHECK (saldo_centavos >= 0))""")
            self.execute(conn, f"""CREATE TABLE IF NOT EXISTS transacciones (
                id {pk},
                tipo TEXT NOT NULL,
                monto_centavos BIGINT NOT NULL,
                cuenta_destino TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            self.execute(conn, "INSERT INTO cuenta (id, titular, saldo_centavos) "
                               "VALUES (1, 'Usuario Demo', 1500000) ON CONFLICT (id) DO NOTHING")
