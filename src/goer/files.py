"""File dependencies.

Contains functionality for defining dependencies on files.
"""

import glob as builtin_glob
import os
from datetime import datetime

from goer.dep import Dependency, DependencyDef


class Glob(Dependency):
    """A dependency on a glob of files."""

    def __init__(self, dep_id: str, pattern: str) -> None:
        """Initialize the glob dependency with a dependency ID and a glob
        pattern."""
        super().__init__(dep_id)
        self._pattern = pattern

    @property
    def last_modified(self) -> datetime:
        """A glob is last modified at the latest time any file matched by glob
        is modified."""
        return max(
            datetime.fromtimestamp(os.stat(path).st_mtime)
            for path in builtin_glob.glob(self._pattern)
        )

    async def _run(self) -> bool:
        """The glob always runs successfully."""
        # TODO: Consider if globs should fail if no files are matched
        return True


class GlobDef(DependencyDef):
    """A definition of a dependency on files identified by a glob."""

    def __init__(self, pattern: str) -> None:
        self._pattern = pattern

    @property
    def depends_on(self) -> list[DependencyDef]:
        """Globs cannot have nested dependencies."""
        return []

    def initialize(
        self, dep_id: str, color: str, depends_on: list[Dependency]
    ) -> Dependency:
        """Returns a `Glob` with the given dependency ID and glob pattern."""
        return Glob(dep_id, self._pattern)


def glob(pattern: str) -> GlobDef:
    """Define a dependency on files identified by a glob.

    Examples:
        >>> glob("my_file.txt")
        >>> glob("some/folder/*.txt")
        >>> glob("**/*.py")
    """
    return GlobDef(pattern)
