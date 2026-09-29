import sqlite3
from pathlib import Path


class MemoryStore:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(str(self.database_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    user_input TEXT,
                    assistant_output TEXT,
                    category TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    rating INTEGER,
                    note TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    value TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def record_interaction(self, user_input: str, assistant_output: str, category: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO interactions (user_input, assistant_output, category) VALUES (?, ?, ?)",
                (user_input, assistant_output, category),
            )
            conn.commit()

    def record_feedback(self, session_id: str, rating: int, note: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO feedback (session_id, rating, note) VALUES (?, ?, ?)",
                (session_id, rating, note),
            )
            conn.commit()

    def remember_preference(self, key: str, value: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
                (key, value),
            )
            conn.commit()

    def get_preference(self, key: str):
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def get_preferences(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM preferences ORDER BY updated_at DESC"
            ).fetchall()
            return {row["key"]: row["value"] for row in rows}

    def get_recent(self, limit: int = 10):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT timestamp, user_input, assistant_output, category FROM interactions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return list(reversed([
                {
                    "timestamp": row["timestamp"],
                    "user_input": row["user_input"],
                    "assistant_output": row["assistant_output"],
                    "category": row["category"],
                }
                for row in rows
            ]))

    def get_feedback_summary(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT rating, COUNT(*) as count FROM feedback GROUP BY rating ORDER BY rating"
            ).fetchall()
            return [{"rating": row["rating"], "count": row["count"]} for row in rows]

    def get_learning_summary(self):
        with self._connect() as conn:
            interaction_counts = conn.execute(
                "SELECT category, COUNT(*) AS count FROM interactions GROUP BY category ORDER BY count DESC"
            ).fetchall()
            preferences = conn.execute(
                "SELECT key, value FROM preferences ORDER BY updated_at DESC LIMIT 10"
            ).fetchall()
            feedback = conn.execute(
                "SELECT AVG(rating) AS average_rating, COUNT(*) AS total FROM feedback"
            ).fetchone()

            return {
                "interaction_counts": [{"category": row["category"], "count": row["count"]} for row in interaction_counts],
                "preferences": [{"key": row["key"], "value": row["value"]} for row in preferences],
                "average_feedback_rating": float(feedback["average_rating"]) if feedback["average_rating"] is not None else 0.0,
                "feedback_count": feedback["total"] if feedback["total"] is not None else 0,
            }
