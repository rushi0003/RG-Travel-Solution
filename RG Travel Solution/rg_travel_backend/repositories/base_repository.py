import sqlite3
from typing import Any, List, Optional, Tuple, Dict

class BaseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cur = conn.cursor()

    def execute(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        return self.cur.execute(query, params)

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        self.execute(query, params)
        return self.cur.fetchone()

    def fetch_all(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        self.execute(query, params)
        return self.cur.fetchall()

    def commit(self):
        self.conn.commit()
    
    def rollback(self):
        self.conn.rollback()
