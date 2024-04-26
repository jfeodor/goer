"""The main module, which contains the `Gør` class, which uses the
`DependencyManager` to run dependencies."""

import asyncio
import time
from typing import Any

from goer.dep import DependencyDef
from goer.depman import DependencyManager
from goer.text import print_error, print_header


class Gør:
    """All functionality for the `goer` command.

    * Reads python files with dependency definitions
    * Initializes the `DependencyManager` with the definitions
    * Runs the dependency trees rooted at given dependency IDs
    """

    def __init__(self, depman: DependencyManager) -> None:
        """Initialize with a dependency manager."""
        self.depman = depman

    def list_dep_ids(self) -> list[str]:
        """Returns all dependency definitions."""
        return [dep_id for dep_id in self.depman.deps.keys()]

    async def run(self, dep_ids: list[str]) -> bool:
        """Runs the dependencies identified by the given IDs.

        Returns `True` if all dependencies are successful, `False` otherwise."""
        t = time.time()

        deps = self.depman.find_deps(dep_ids)
        results = await asyncio.gather(*[self.depman.run_dep(dep) for dep in deps])
        failed_deps = not all(results)
        if failed_deps:
            print_error("deps failed")

        elapsed = time.time() - t
        print_header(f"elapsed: {elapsed:.2f}s")
        return failed_deps

    @staticmethod
    def load_python(path: str) -> "Gør":
        """Load a python file with dependency definitions."""
        scope: dict[str, Any] = {}

        with open(path) as f:
            exec(f.read(), {}, scope)

        dep_defs = {
            dep_id: dep_def
            for dep_id, dep_def in scope.items()
            if isinstance(dep_def, DependencyDef)
        }
        return Gør(DependencyManager.from_defs(dep_defs))
