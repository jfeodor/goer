import asyncio
import time
import toml

from typing import Any

from goer.job import Job, JobDef, DependencyManager
from goer.text import print_error, print_header


class Gør:

    def __init__(self, depman: DependencyManager) -> None:
        self.depman = depman

    def list_job_ids(self) -> list[str]:
        return [job_id for job_id in self.depman.jobs.keys()]

    async def run(self, job_ids: list[str]) -> bool:
        t = time.time()

        jobs = self.depman.find_jobs(job_ids)
        results = await asyncio.gather(*[self.depman.run_job(job) for job in jobs])
        failed_jobs = not all(results)
        if failed_jobs:
            print_error("jobs failed")

        elapsed = time.time() - t
        print_header(f"elapsed: {elapsed:.2f}s")
        return failed_jobs

    @staticmethod
    def load_toml(path: str) -> "Gør":
        data = toml.load(path)

        depman = DependencyManager()
        jobs = [
            Job.from_toml(job_id, job_data) for job_id, job_data in data["jobs"].items()
        ]
        depman.initialize(jobs)

        return Gør(depman)

    @staticmethod
    def load_python(path: str) -> "Gør":
        scope: dict[str, Any] = {}

        with open(path) as f:
            exec(f.read(), {}, scope)

        depman = DependencyManager()

        job_defs = {
            job_id: job_def
            for job_id, job_def in scope.items()
            if isinstance(job_def, JobDef)
        }

        jobs: list[Job] = []
        for job_id, job_def in job_defs.items():
            job = Job(
                job_id,
                job_def.steps,
                depends_on=_find_job_dep_ids(job_defs, job_def.depends_on),
                rules=job_def.rules or [],
                workdir=job_def.workdir,
            )
            jobs.append(job)

        depman.initialize(jobs)

        return Gør(depman)


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
