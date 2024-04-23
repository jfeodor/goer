from dataclasses import dataclass
from datetime import datetime

from goer.text import TextMode


@dataclass
class Dependency:
    dep_id: str
    depends_on: list["Dependency"]
    color: str

    @property
    def pretty_id(self) -> str:
        return f"{self.color}{self.dep_id}{TextMode.RESET}"

    @property
    def last_modified(self) -> datetime:
        return datetime.now()

    async def run(self) -> bool:
        return True
