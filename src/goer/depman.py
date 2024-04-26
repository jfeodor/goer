"""Dependency manager.

The dependency manager can be initialized with a mapping of dependency IDs to
dependency definitions, setting up the correct relations between the initialized
dependencies.

When initialized, the dependency manager can run specific dependencies,
including running all sub-dependencies.
"""

import asyncio
import random
from typing import Iterable

from goer.dep import Dependency, DependencyDef
from goer.text import COLORS, print_error, print_header


class DependencyManager:
    """Runs a dependency tree recursively."""

    def __init__(self, deps: Iterable[Dependency]) -> None:
        self.deps: dict[str, Dependency] = {dep.dep_id: dep for dep in deps}
        self.deps_running: dict[str, asyncio.Future[bool]] = {}

    async def run_dep(self, dep: Dependency) -> bool:
        """Runs the dependency tree."""

        last_modified = dep.last_modified
        if dep.depends_on and all(
            last_modified > dep_dep.last_modified for dep_dep in dep.depends_on
        ):
            print_header("skipping '", dep.pretty_id, "'")
            return True

        print_header("starting '", dep.pretty_id, "'")
        try:
            return await self._run_dep(dep)
        except Exception as e:
            print_error(f"dependency '{dep.dep_id}' failed with error: {e}")
            return False

    async def _run_dep(self, dep: Dependency) -> bool:
        if check_job_result := await self._run_recursive_deps(dep) is not None:
            return check_job_result

        if running_dep := self.deps_running.get(dep.dep_id):
            return await running_dep

        dep_task = asyncio.create_task(dep.run())
        self.deps_running[dep.dep_id] = dep_task
        return await dep_task

    async def _run_recursive_deps(self, dep: Dependency) -> bool | None:
        if dep.depends_on:
            print_header("running dependencies for '", dep.pretty_id, "'")
            tasks: list[asyncio.Future[bool]] = []
            for dep in dep.depends_on:
                if dep_fut := self.deps_running.get(dep.dep_id):
                    tasks.append(dep_fut)
                else:
                    tasks.append(
                        asyncio.create_task(self.run_dep(dep), name=dep.dep_id)
                    )

            results = await asyncio.gather(*tasks)
            if not all(results):
                print_error("dependency failed for '", dep.pretty_id, "'")
                return False

        return None

    @staticmethod
    def from_defs(defs: dict[str, DependencyDef]) -> "DependencyManager":
        """Initialize a dependency manager from dependency definitions.

        Sets up correct relations between definitions. Dependency cycles will
        result in an error being raised.
        """
        uninitialized_dep_defs = dict(defs)
        initialized_deps: dict[str, Dependency] = {}

        iterations_left = 1000
        while uninitialized_dep_defs:
            iterations_left -= 1
            if iterations_left <= 0:
                raise RuntimeError("Could not resolve dependencies")

            for dep_id, dep_def in dict(uninitialized_dep_defs).items():
                dep_ids = _find_dep_ids(defs, dep_def.depends_on)
                if not all(dep_dep_id in initialized_deps for dep_dep_id in dep_ids):
                    continue

                initialized_deps[dep_id] = dep_def.initialize(
                    dep_id,
                    random.choice(COLORS),
                    depends_on=[initialized_deps[dep_dep_id] for dep_dep_id in dep_ids],
                )
                del uninitialized_dep_defs[dep_id]

        return DependencyManager(initialized_deps.values())

    def find_deps(self, dep_ids: list[str]) -> list[Dependency]:
        return [dep for dep in self.deps.values() if dep.dep_id in dep_ids]


def _find_dep_ids(
    defs: dict[str, DependencyDef], deps: list[DependencyDef]
) -> list[str]:
    dep_ids: list[str] = []

    for dep in deps:
        found = False
        for dep_id, dep_def in defs.items():
            if dep is dep_def:
                dep_ids.append(dep_id)
                found = True
        if not found:
            raise RuntimeError(f"Could not match dependency")

    return dep_ids
