from contextlib import asynccontextmanager, closing
from pathlib import Path
import sqlite3
from threading import RLock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).resolve().parents[1] / "turnos.db"
lock = RLock()


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize():
    with closing(connect()) as db, db:
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
        db.executemany("INSERT OR IGNORE INTO desks(number) VALUES (?)", [(n,) for n in range(1, 5)])
        last = db.execute("SELECT id FROM tickets ORDER BY id DESC LIMIT 1").fetchone()
        if last:
            for row in db.execute("SELECT id FROM tickets WHERE number IS NULL"):
                db.execute("UPDATE tickets SET number=? WHERE id=?", (f"T{row['id']:03d}", row['id']))


@asynccontextmanager
async def lifespan(_app):
    initialize()
    yield


app = FastAPI(title="Turnero bancario", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def assign_waiting(db, desk_number):
    ticket = db.execute("SELECT id, number FROM tickets WHERE status='waiting' ORDER BY id LIMIT 1").fetchone()
    if ticket:
        db.execute("UPDATE tickets SET status='serving', desk=?, called_at=CURRENT_TIMESTAMP WHERE id=?", (desk_number, ticket['id']))
        db.execute("UPDATE desks SET ticket_id=? WHERE number=?", (ticket['id'], desk_number))
        return {"id": ticket['id'], "number": ticket['number'], "desk": desk_number}
    db.execute("UPDATE desks SET ticket_id=NULL WHERE number=?", (desk_number,))
    return None


def snapshot():
    with lock, closing(connect()) as db, db:
        desks = db.execute("""
            SELECT d.number, t.id AS ticket_id, t.number AS ticket_number, t.status
            FROM desks d LEFT JOIN tickets t ON t.id=d.ticket_id ORDER BY d.number
        """).fetchall()
        waiting = db.execute("SELECT id, number, created_at FROM tickets WHERE status='waiting' ORDER BY id").fetchall()
        return {
            "desks": [dict(row) for row in desks],
            "available_desks": sum(row['ticket_id'] is None for row in desks),
            "waiting_count": len(waiting),
            "waiting": [dict(row) for row in waiting],
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
        cursor = db.execute("INSERT INTO tickets(status) VALUES ('waiting')")
        ticket_id = cursor.lastrowid
        number = f"T{ticket_id:03d}"
        db.execute("UPDATE tickets SET number=? WHERE id=?", (number, ticket_id))
        free_desk = db.execute("SELECT number FROM desks WHERE ticket_id IS NULL ORDER BY number LIMIT 1").fetchone()
        if free_desk:
            db.execute("UPDATE tickets SET status='serving', desk=?, called_at=CURRENT_TIMESTAMP WHERE id=?", (free_desk['number'], ticket_id))
            db.execute("UPDATE desks SET ticket_id=? WHERE number=?", (ticket_id, free_desk['number']))
            desk = free_desk['number']
        else:
            desk = None
    return {"id": ticket_id, "number": number, "status": "serving" if desk else "waiting", "desk": desk}


@app.post("/api/desks/{desk_number}/complete")
def complete_service(desk_number: int):
    if desk_number not in range(1, 5):
        raise HTTPException(status_code=404, detail="La mesa debe ser un número del 1 al 4.")
    with lock, closing(connect()) as db, db:
        desk = db.execute("SELECT ticket_id FROM desks WHERE number=?", (desk_number,)).fetchone()
        if not desk or desk['ticket_id'] is None:
            raise HTTPException(status_code=409, detail="La mesa ya está disponible.")
        db.execute("UPDATE tickets SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?", (desk['ticket_id'],))
        next_ticket = assign_waiting(db, desk_number)
    return {"desk": desk_number, "next_ticket": next_ticket, "state": snapshot()}
