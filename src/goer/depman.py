import asyncio

from goer.job import Job
from goer.text import print_error, print_header


class DependencyManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.jobs_done: dict[str, bool] = {}

    async def run_job(self, job: Job) -> bool:
        try:
            return await self._run_job(job)
        except Exception as e:
            print_error(f"job '{job.job_id}' failed with error: {e}")
            return False

    async def _run_job(self, job: Job) -> bool:
        if self.jobs_done.get(job.job_id, False):
            return True

        if (
            check_job_result := await self._check_dependencies_and_rules(job)
            is not None
        ):
            return check_job_result

        job_exit_code = await job._run()
        self.jobs_done[job.job_id] = True
        return job_exit_code

    async def _check_dependencies_and_rules(self, job: Job) -> bool | None:
        if job.depends_on:
            print_header("running dependencies for '", job.pretty_job_id, "'")
            deps = self._resolve_job_deps(job)
            results = await asyncio.gather(*[self.run_job(dep) for dep in deps])
            if not all(results):
                print_error("dependency failed for '", job.pretty_job_id, "'")
                return False

        if job.rules and all(rule.can_skip() for rule in job.rules):
            print_header("skipping '", job.pretty_job_id, "' since all rules passed")
            return True

        return None

    def _resolve_job_deps(self, job: Job) -> list[Job]:
        deps: list[Job] = []
        for dep_job_id in job.depends_on:
            dep = self.jobs.get(dep_job_id)
            if dep is None:
                print_error(
                    f"dependency '{dep_job_id}' for '{job.pretty_job_id}' not found!"
                )
            else:
                deps.append(dep)
        return deps

    def initialize(self, jobs: list[Job]) -> None:
        for job in jobs:
            self.jobs[job.job_id] = job

    def find_jobs(self, job_ids: list[str]) -> list[Job]:
        return [job for job in self.jobs.values() if job.job_id in job_ids]
