from contextlib import asynccontextmanager, closing
import os
from pathlib import Path
import sqlite3
from threading import RLock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).resolve().parents[1] / "turnos.db"
DATABASE_URL = os.getenv("DATABASE_URL")
IS_POSTGRES = bool(DATABASE_URL)
if os.getenv("VERCEL") and not IS_POSTGRES:
    raise RuntimeError("Configura DATABASE_URL en Vercel para usar una base de datos persistente.")

lock = RLock()


def connect():
    if IS_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def execute(db, sql, params=()):
    if IS_POSTGRES:
        sql = sql.replace("?", "%s")
    return db.execute(sql, params)


def for_update():
    return " FOR UPDATE" if IS_POSTGRES else ""


def initialize():
    with closing(connect()) as db, db:
        if IS_POSTGRES:
            db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id BIGSERIAL PRIMARY KEY,
                    number TEXT UNIQUE,
                    status TEXT NOT NULL DEFAULT 'waiting',
                    desk INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    called_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS desks (
                    number INTEGER PRIMARY KEY,
                    ticket_id BIGINT REFERENCES tickets(id)
                )
            """)
        else:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    number TEXT UNIQUE,
                    status TEXT NOT NULL DEFAULT 'waiting',
                    desk INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    called_at TEXT,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS desks (
                    number INTEGER PRIMARY KEY,
                    ticket_id INTEGER REFERENCES tickets(id)
                );
            """)
        for number in range(1, 5):
            execute(
                db,
                "INSERT INTO desks(number) VALUES (?) ON CONFLICT DO NOTHING",
                (number,),
            )
        missing_numbers = execute(
            db, "SELECT id FROM tickets WHERE number IS NULL"
        ).fetchall()
        for row in missing_numbers:
            ticket_id = row["id"]
            execute(
                db,
                "UPDATE tickets SET number=? WHERE id=?",
                (f"T{ticket_id:03d}", ticket_id),
            )


@asynccontextmanager
async def lifespan(_app):
    initialize()
    yield


app = FastAPI(title="Turnero bancario", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def assign_waiting(db, desk_number):
    ticket = execute(
        db,
        "SELECT id, number FROM tickets WHERE status='waiting' "
        f"ORDER BY id LIMIT 1{for_update()}",
    ).fetchone()
    if ticket:
        execute(
            db,
            "UPDATE tickets SET status='serving', desk=?, called_at=CURRENT_TIMESTAMP WHERE id=?",
            (desk_number, ticket["id"]),
        )
        execute(
            db,
            "UPDATE desks SET ticket_id=? WHERE number=?",
            (ticket["id"], desk_number),
        )
        return {"id": ticket["id"], "number": ticket["number"], "desk": desk_number}
    execute(db, "UPDATE desks SET ticket_id=NULL WHERE number=?", (desk_number,))
    return None


def snapshot():
    with lock, closing(connect()) as db:
        desks = execute(
            db,
            """
            SELECT d.number, t.id AS ticket_id, t.number AS ticket_number, t.status
            FROM desks d LEFT JOIN tickets t ON t.id=d.ticket_id ORDER BY d.number
            """,
        ).fetchall()
        waiting = execute(
            db,
            "SELECT id, number, created_at FROM tickets "
            "WHERE status='waiting' ORDER BY id",
        ).fetchall()
        desk_rows = [dict(row) for row in desks]
        waiting_rows = [dict(row) for row in waiting]
        return {
            "desks": desk_rows,
            "available_desks": sum(row["ticket_id"] is None for row in desk_rows),
            "waiting_count": len(waiting_rows),
            "waiting": waiting_rows,
        }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/state")
def get_state():
    return snapshot()


@app.post("/api/tickets", status_code=201)
def create_ticket():
    with lock, closing(connect()) as db, db:
        ticket = execute(
            db, "INSERT INTO tickets(status) VALUES ('waiting') RETURNING id"
        ).fetchone()
        ticket_id = ticket["id"]
        number = f"T{ticket_id:03d}"
        execute(db, "UPDATE tickets SET number=? WHERE id=?", (number, ticket_id))
        free_desk = execute(
            db,
            "SELECT number FROM desks WHERE ticket_id IS NULL "
            f"ORDER BY number LIMIT 1{for_update()}",
        ).fetchone()
        if free_desk:
            desk_number = free_desk["number"]
            execute(
                db,
                "UPDATE tickets SET status='serving', desk=?, called_at=CURRENT_TIMESTAMP WHERE id=?",
                (desk_number, ticket_id),
            )
            execute(
                db,
                "UPDATE desks SET ticket_id=? WHERE number=?",
                (ticket_id, desk_number),
            )
            desk = desk_number
        else:
            desk = None
    return {
        "id": ticket_id,
        "number": number,
        "status": "serving" if desk else "waiting",
        "desk": desk,
    }


@app.post("/api/desks/{desk_number}/complete")
def complete_service(desk_number: int):
    if desk_number not in range(1, 5):
        raise HTTPException(status_code=404, detail="La mesa debe ser un número del 1 al 4.")
    with lock, closing(connect()) as db, db:
        desk = execute(
            db,
            f"SELECT ticket_id FROM desks WHERE number=?{for_update()}",
            (desk_number,),
        ).fetchone()
        if not desk or desk["ticket_id"] is None:
            raise HTTPException(status_code=409, detail="La mesa ya está disponible.")
        execute(
            db,
            "UPDATE tickets SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?",
            (desk["ticket_id"],),
        )
        next_ticket = assign_waiting(db, desk_number)
    return {"desk": desk_number, "next_ticket": next_ticket, "state": snapshot()}
