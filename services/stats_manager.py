# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5: Services Module - Stats Manager
# Pure extraction from main file - NO behavior changes

import sqlite3
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("FishingMacro")


class StatsManager:
    """
    Advanced Statistics Manager with SQLite persistence

    EXACT COPY from main file - NO behavior changes
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fishing_stats.db"
        )
        self.session_id = None
        self.session_start = None
        self._fish_count = 0
        self._fruit_count = 0
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        fish_count INTEGER DEFAULT 0,
                        fruit_count INTEGER DEFAULT 0
                    )
                """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS catches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        type TEXT NOT NULL,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions(id)
                    )
                """
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Stats DB init error: {e}")

    def start_session(self) -> int:
        """Start a new fishing session"""
        try:
            self.session_start = datetime.now()
            self._fish_count = 0
            self._fruit_count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sessions (start_time) VALUES (?)",
                    (self.session_start.isoformat(),),
                )
                self.session_id = cursor.lastrowid
                conn.commit()
            logger.info(f"Stats session started: {self.session_id}")
            return self.session_id
        except Exception as e:
            logger.error(f"Start session error: {e}")
            return -1

    def end_session(self):
        """End current session and save totals"""
        if not self.session_id:
            return
        try:
            end_time = datetime.now()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE sessions SET end_time = ?, fish_count = ?, fruit_count = ?
                    WHERE id = ?
                """,
                    (
                        end_time.isoformat(),
                        self._fish_count,
                        self._fruit_count,
                        self.session_id,
                    ),
                )
                conn.commit()
            duration = (
                end_time - self.session_start if self.session_start else timedelta(0)
            )
            logger.info(
                f"Session ended: fish={self._fish_count}, fruits={self._fruit_count}, duration={duration}"
            )
            self.session_id = None
            self.session_start = None
        except Exception as e:
            logger.error(f"End session error: {e}")

    def log_fish(self):
        """Log a fish catch"""
        self._fish_count += 1
        self._log_catch("fish")

    def log_fruit(self):
        """Log a fruit catch"""
        self._fruit_count += 1
        self._log_catch("fruit")

    def _log_catch(self, catch_type: str):
        """Internal: log catch to database"""
        if not self.session_id:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO catches (session_id, type) VALUES (?, ?)",
                    (self.session_id, catch_type),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Log catch error: {e}")

    @property
    def fish_count(self) -> int:
        return self._fish_count

    @property
    def fruit_count(self) -> int:
        return self._fruit_count

    def get_session_duration(self) -> float:
        """Get current session duration in seconds"""
        if self.session_start:
            return (datetime.now() - self.session_start).total_seconds()
        return 0.0

    def get_today_summary(self) -> dict:
        """Get today's statistics"""
        today = datetime.now().date().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*), COALESCE(SUM(fish_count), 0), COALESCE(SUM(fruit_count), 0)
                    FROM sessions WHERE date(start_time) = ?
                """,
                    (today,),
                )
                row = cursor.fetchone()
                return {
                    "date": today,
                    "sessions": row[0],
                    "fish": row[1],
                    "fruits": row[2],
                }
        except (sqlite3.Error, OSError) as e:
            logger.warning(f"Failed to get today's summary: {e}")
            return {"date": today, "sessions": 0, "fish": 0, "fruits": 0}

    def get_historical(self, days: int = 7) -> list:
        """Get summary for last N days"""
        results = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(fish_count), 0), COALESCE(SUM(fruit_count), 0)
                        FROM sessions WHERE date(start_time) = ?
                    """,
                        (date,),
                    )
                    row = cursor.fetchone()
                    results.append({"date": date, "fish": row[0], "fruits": row[1]})
            except (sqlite3.Error, OSError) as e:
                logger.warning(f"Failed to get historical data for {date}: {e}")
                results.append({"date": date, "fish": 0, "fruits": 0})
        return results

    def export_csv(self, filepath: str) -> bool:
        """Export all sessions to CSV"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions ORDER BY start_time DESC")
                rows = cursor.fetchall()
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("id,start_time,end_time,fish_count,fruit_count\n")
                    for row in rows:
                        f.write(",".join(str(x) if x else "" for x in row) + "\n")
            logger.info(f"Exported {len(rows)} sessions to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Export CSV error: {e}")
            return False
