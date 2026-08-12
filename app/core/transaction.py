from __future__ import annotations

import sqlite3


class Transaction:

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def __enter__(self):
        self.connection.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()

        return False