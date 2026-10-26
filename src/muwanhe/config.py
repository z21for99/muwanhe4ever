from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    source_path: Path
    db_path: Path = Path("data/muwanhe.db")
    encoding: str = "utf-8"

    @classmethod
    def from_args(cls, source: str, db: str = "data/muwanhe.db") -> "Settings":
        return cls(source_path=Path(source), db_path=Path(db))
