import asyncio
import time
from typing import Any

from goer.dep import DependencyDef
from goer.depman import DependencyManager
from goer.text import print_error, print_header


class Gør:
    def __init__(self, depman: DependencyManager) -> None:
        self.depman = depman

    def list_job_ids(self) -> list[str]:
        return [job_id for job_id in self.depman.deps.keys()]

    async def run(self, job_ids: list[str]) -> bool:
        t = time.time()

        jobs = self.depman.find_deps(job_ids)
        results = await asyncio.gather(*[self.depman.run_dep(job) for job in jobs])
        failed_jobs = not all(results)
        if failed_jobs:
            print_error("jobs failed")

        elapsed = time.time() - t
        print_header(f"elapsed: {elapsed:.2f}s")
        return failed_jobs

    @staticmethod
    def load_python(path: str) -> "Gør":
        scope: dict[str, Any] = {}

        with open(path) as f:
            exec(f.read(), {}, scope)

        job_defs = {
            job_id: job_def
            for job_id, job_def in scope.items()
            if isinstance(job_def, DependencyDef)
        }
        return Gør(DependencyManager.from_defs(job_defs))
