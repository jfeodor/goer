import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from goer.text import COLORS, TextMode, print_error


@dataclass
class Dependency(ABC):
    dep_id: str
    color: str = field(default_factory=lambda: random.choice(COLORS))
    depends_on: list["Dependency"] = field(default_factory=list)

    @property
    def pretty_id(self) -> str:
        return f"{self.color}{self.dep_id}{TextMode.RESET}"

    @property
    def last_modified(self) -> datetime:
        return datetime.now()

    async def run(self) -> bool:
        try:
            return await self._run()
        except Exception as e:
            print_error("error occurred running '", self.pretty_id, f"': {e}")
            return False

    @abstractmethod
    async def _run(self) -> bool: ...


class DependencyDef(ABC):
    @property
    @abstractmethod
    def depends_on(self) -> list["DependencyDef"]: ...

    @abstractmethod
    def initialize(
        self, dep_id: str, color: str, depends_on: list[Dependency]
    ) -> Dependency: ...
