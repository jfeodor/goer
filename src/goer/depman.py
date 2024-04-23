import asyncio
from typing import Iterable

from goer.dep import Dependency
from goer.job import Job, JobDef
from goer.text import print_error, print_header


class DependencyManager:
    def __init__(self, deps: Iterable[Dependency]) -> None:
        self.deps: dict[str, Dependency] = {dep.dep_id: dep for dep in deps}
        self.deps_running: dict[str, asyncio.Future[bool]] = {}

    async def run_dep(self, dep: Dependency) -> bool:
        print_header("starting '", dep.pretty_id, "'")
        try:
            return await self._run_dep(dep)
        except Exception as e:
            print_error(f"job '{dep.dep_id}' failed with error: {e}")
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
    def from_job_defs(job_defs: dict[str, JobDef]) -> "DependencyManager":
        deps: dict[str, Dependency] = {
            job_id: Job(
                job_id,
                steps=job_def.steps,
                rules=job_def.rules or [],
                workdir=job_def.workdir,
            )
            for job_id, job_def in job_defs.items()
        }

        for dep_id, dep in deps.items():
            job_def = job_defs[dep_id]
            dep_ids = _find_job_dep_ids(job_defs, job_def.depends_on)
            try:
                dep.depends_on = [deps[dep_id] for dep_id in dep_ids]
            except KeyError as e:
                print_error("could not find job", str(e.args[0]))

        return DependencyManager(deps.values())

    def find_deps(self, dep_ids: list[str]) -> list[Dependency]:
        return [dep for dep in self.deps.values() if dep.dep_id in dep_ids]


def _find_job_dep_ids(job_defs: dict[str, JobDef], deps: list[JobDef]) -> list[str]:
    job_dep_ids: list[str] = []

    for dep in deps:
        found = False
        for job_id, job_def in job_defs.items():
            if dep is job_def:
                job_dep_ids.append(job_id)
                found = True
        if not found:
            raise RuntimeError("Could not match dependency")

    return job_dep_ids
