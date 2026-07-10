"""PostgreSQL access for the application service."""
import os
import time

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://forge:forge@postgres:5432/failureforge"
)


def connect(retries: int = 10, delay: float = 1.5):
    """Open a connection, retrying while Postgres comes up."""
    last_err = None
    for _ in range(retries):
        try:
            return psycopg2.connect(DATABASE_URL)
        except psycopg2.OperationalError as err:  # not yet ready
            last_err = err
            time.sleep(delay)
    raise last_err


def init_schema() -> None:
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id   SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
                """
            )
            # Two rows used by the database_deadlock scenario.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id      INTEGER PRIMARY KEY,
                    balance INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute(
                "INSERT INTO accounts (id, balance) VALUES (1, 100), (2, 100)"
                " ON CONFLICT (id) DO NOTHING"
            )
    finally:
        conn.close()


def run_deadlock_txn(first_id: int, second_id: int, hold: float = 0.4) -> None:
    """Update two account rows in a given order inside one transaction.

    Two concurrent calls with opposite orders create a lock cycle; PostgreSQL's
    deadlock detector aborts one of them, raising psycopg2.errors.DeadlockDetected.
    The caller is expected to handle/log that error.
    """
    import time

    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE accounts SET balance = balance + 1 WHERE id = %s",
                (first_id,),
            )
            time.sleep(hold)  # widen the window so the cycle reliably forms
            cur.execute(
                "UPDATE accounts SET balance = balance - 1 WHERE id = %s",
                (second_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def slow_query(seconds: float):
    """Run an artificially slow query (server-side sleep) and read a row."""
    conn = connect()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT pg_sleep(%s)", (seconds,))
            cur.execute("SELECT id, name FROM items ORDER BY id DESC LIMIT 1")
            return cur.fetchone()
    finally:
        conn.close()


def write_item(name: str) -> int:
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO items (name) VALUES (%s) RETURNING id", (name,)
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def read_item(item_id: int):
    conn = connect()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM items WHERE id = %s", (item_id,))
            return cur.fetchone()
    finally:
        conn.close()
