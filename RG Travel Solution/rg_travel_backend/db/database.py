
from typing import Any, List, Tuple
from db import get_db

def query(conn, sql: str, params: list | tuple = ()) -> List[Any]:
    """
    Execute a SELECT query and return rows.
    """
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()

def execute(conn, sql: str, params: list | tuple = ()) -> Any:
    """
    Execute an INSERT/UPDATE/DELETE statement.
    """
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur
