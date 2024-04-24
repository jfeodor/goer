import glob as builtin_glob
import os
from datetime import datetime

from goer.dep import Dependency, DependencyDef


class Glob(Dependency):
    def __init__(self, dep_id: str, pattern: str) -> None:
        super().__init__(dep_id)
        self._pattern = pattern

    @property
    def last_modified(self) -> datetime:
        return max(
            datetime.fromtimestamp(os.stat(path).st_mtime)
            for path in builtin_glob.glob(self._pattern)
        )

    async def _run(self) -> bool:
        return True


class GlobDef(DependencyDef):
    def __init__(self, pattern: str) -> None:
        self._pattern = pattern

    @property
    def depends_on(self) -> list[DependencyDef]:
        return []

    def initialize(
        self, dep_id: str, color: str, depends_on: list[Dependency]
    ) -> Dependency:
        return Glob(dep_id, self._pattern)


def glob(pattern: str) -> GlobDef:
    return GlobDef(pattern)
