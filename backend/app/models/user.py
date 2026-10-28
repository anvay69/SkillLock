from dataclasses import dataclass
import json
import sqlite3
from typing import Any


@dataclass(frozen=True)
class User:
    id: int
    name: str
    username: str
    email: str
    password_hash: str
    profile: dict[str, Any]

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        return cls(
            id=row["id"],
            name=row["name"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            profile=json.loads(row["profile_json"]),
        )
