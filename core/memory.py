"""
JARVIS Memory System
====================
כל גישה למסד הנתונים אסינכרונית.
WAL mode מופעל לביצועים מיטביים (קריאות מקבילות תוך כדי כתיבה).
החיבור נפתח פעם אחת ונשאר פתוח — אין עלות פתיחה בכל בקשה.
"""
import asyncio
from datetime import datetime
from typing import Optional
import aiosqlite
from config.settings import settings


_connection: Optional[aiosqlite.Connection] = None


# ─── אתחול ─────────────────────────────────────────────────────────────────

async def init_db():
    """פותח חיבור קבוע ויוצר טבלאות אם לא קיימות."""
    global _connection
    _connection = await aiosqlite.connect(settings.db_path)
    _connection.row_factory = aiosqlite.Row

    # WAL = Write-Ahead Logging: קריאות לא חוסמות כתיבות
    await _connection.execute("PRAGMA journal_mode=WAL;")
    await _connection.execute("PRAGMA synchronous=NORMAL;")
    await _connection.execute("PRAGMA cache_size=10000;")

    await _connection.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT    NOT NULL DEFAULT 'pc',
            role      TEXT    NOT NULL,
            content   TEXT    NOT NULL,
            timestamp TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp);
        CREATE INDEX IF NOT EXISTS idx_conv_device    ON conversations(device_id);

        CREATE TABLE IF NOT EXISTS memories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            category   TEXT    NOT NULL,
            fact       TEXT    NOT NULL,
            confidence REAL    DEFAULT 1.0,
            created_at TEXT    NOT NULL,
            last_used  TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_mem_category  ON memories(category);
        CREATE INDEX IF NOT EXISTS idx_mem_last_used ON memories(last_used);

        CREATE TABLE IF NOT EXISTS devices (
            id          TEXT PRIMARY KEY,
            device_type TEXT NOT NULL,
            device_name TEXT NOT NULL,
            last_seen   TEXT NOT NULL,
            token       TEXT
        );
    """)
    await _connection.commit()


async def close_db():
    global _connection
    if _connection:
        await _connection.close()
        _connection = None


def _db() -> aiosqlite.Connection:
    if _connection is None:
        raise RuntimeError("DB not initialized — call init_db() first")
    return _connection


# ─── שיחות ─────────────────────────────────────────────────────────────────

async def save_message(role: str, content: str, device_id: str = "pc"):
    await _db().execute(
        "INSERT INTO conversations (device_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (device_id, role, content, datetime.utcnow().isoformat()),
    )
    await _db().commit()


async def get_recent_conversation(limit: int = 20) -> list[dict]:
    async with _db().execute(
        "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (limit,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ─── זיכרונות (עובדות על המשתמש) ──────────────────────────────────────────

async def save_memory(category: str, fact: str, confidence: float = 1.0):
    now = datetime.utcnow().isoformat()
    await _db().execute(
        "INSERT INTO memories (category, fact, confidence, created_at, last_used) VALUES (?, ?, ?, ?, ?)",
        (category, fact, confidence, now, now),
    )
    await _db().commit()


async def get_memories(category: Optional[str] = None, limit: int = 50) -> list[dict]:
    if category:
        async with _db().execute(
            "SELECT category, fact FROM memories WHERE category=? ORDER BY last_used DESC LIMIT ?",
            (category, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    else:
        async with _db().execute(
            "SELECT category, fact FROM memories ORDER BY last_used DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"category": r["category"], "fact": r["fact"]} for r in rows]


async def format_memory_context() -> str:
    memories = await get_memories()
    if not memories:
        return "No memories stored yet."
    return "\n".join(f"- [{m['category']}] {m['fact']}" for m in memories)


# ─── מכשירים ───────────────────────────────────────────────────────────────

async def upsert_device(device_id: str, device_type: str, device_name: str, token: str = ""):
    now = datetime.utcnow().isoformat()
    await _db().execute(
        """INSERT INTO devices (id, device_type, device_name, last_seen, token)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen, token=excluded.token""",
        (device_id, device_type, device_name, now, token),
    )
    await _db().commit()


async def get_active_devices() -> list[dict]:
    async with _db().execute("SELECT id, device_type, device_name FROM devices") as cursor:
        rows = await cursor.fetchall()
    return [{"id": r["id"], "type": r["device_type"], "name": r["device_name"]} for r in rows]
