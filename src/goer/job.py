from asyncio import StreamReader, subprocess
import asyncio
from dataclasses import dataclass, field
import os
import random
from typing import Any, Sequence
from goer.rules import Rule
from goer.text import COLORS, TextMode, print_error, print_header


class Step:
    def __init__(self, cmd: str) -> None:
        self.cmd = cmd

    async def run(
        self, env: dict[str, str], workdir: str | None = None
    ) -> tuple[subprocess.Process, StreamReader, StreamReader]:
        proc = await subprocess.create_subprocess_exec(
            "bash",
            "-c",
            self.cmd,
            env=env,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout = proc.stdout
        if stdout is None:
            stdout = StreamReader()
            stdout.feed_eof()

        stderr = proc.stderr
        if stderr is None:
            stderr = StreamReader()
            stderr.feed_eof()

        return (proc, stdout, stderr)


@dataclass
class Job:
    job_id: str
    steps: Sequence[Step | str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=lambda: dict(os.environ))
    depends_on: list[str] = field(default_factory=list)
    workdir: str | None = None
    rules: list[Rule] = field(default_factory=list)
    color: str = field(default_factory=lambda: random.choice(COLORS))

    @property
    def pretty_job_id(self) -> str:
        return f"{self.color}{self.job_id}{TextMode.RESET}"

    async def run(self) -> bool:
        try:
            return await self._run()
        except Exception as e:
            print_error(f"error occurred: {e}")
            return False

    async def _run(self) -> bool:
        if self.steps:
            if exit_code := await self.run_steps():
                print_error(
                    "job '", self.pretty_job_id, f"' failed with exit code {exit_code}"
                )
                return False

        print_header("job '", self.pretty_job_id, "' done")
        return True

    async def run_steps(self) -> int | None:
        print_header("job '", self.pretty_job_id, f"' running in '{self.workdir}'")
        for step in self.steps:
            step = Step(step) if isinstance(step, str) else step
            proc, stdout, stderr = await step.run(self.env, self.workdir)
            print(self._prefix(step.cmd))
            pstdout = self._print_stream(stdout)
            pstderr = self._print_stream(stderr)
            await asyncio.gather(pstdout, pstderr)
            exit_code = await proc.wait()
            if exit_code != 0:
                return exit_code

        return None

    async def _print_stream(self, stream: StreamReader) -> None:
        while not stream.at_eof():
            raw_ln = await stream.readline()
            if not raw_ln:
                continue
            ln = raw_ln.decode().rstrip("\n")
            print(self._prefix(ln))

    def _prefix(self, s: str) -> str:
        return f"{self.color}{self.job_id}|{TextMode.RESET}{s}"

    @staticmethod
    def from_toml(job_id: str, data: dict[str, Any]) -> "Job":
        return Job(
            job_id,
            steps=data.get("steps", []),
            env=data.get("env") or dict(os.environ),
            depends_on=data.get("depends_on", []),
            workdir=data.get("workdir"),
        )


class JobDef:

    def __init__(
        self,
        steps: list[str],
        depends_on: list["JobDef"],
        rules: list[Rule] | None = None,
        workdir: str | None = None,
    ) -> None:
        self.steps = steps
        self.depends_on = depends_on
        self.rules = rules
        self.workdir = workdir


def job(
    *steps: str,
    depends_on: list[JobDef] | None = None,
    rules: list[Rule] | None = None,
    workdir: str | None = None,
) -> JobDef:
    return JobDef(list(steps), depends_on or [], rules, workdir)


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
