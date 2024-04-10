import asyncio
import os
import random
import sys
import toml

from asyncio import subprocess
from asyncio.streams import StreamReader
from typing import Any, Sequence


class TextMode:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREY = "\033[90m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[95m"


COLORS = [
    TextMode.GREY,
    TextMode.RED,
    TextMode.GREEN,
    TextMode.YELLOW,
    TextMode.BLUE,
    TextMode.PURPLE,
    TextMode.CYAN,
    TextMode.WHITE,
]


class Step:
    def __init__(self, cmd: str) -> None:
        self.cmd = cmd

    async def run(
        self, env: dict[str, str], workdir: str | None = None
    ) -> tuple[StreamReader, StreamReader]:
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

        return (stdout, stderr)


class Job:
    def __init__(
        self,
        depman: "DependencyManager",
        job_id: str,
        steps: Sequence[Step | str] | None = None,
        env: dict[str, str] | None = None,
        depends_on: "list[str] | None" = None,
        workdir: str | None = None,
    ) -> None:
        self.depman = depman
        self.job_id = job_id
        self.steps = steps
        self.env = env or dict(os.environ)
        self.depends_on = depends_on or []
        self.workdir = workdir or os.curdir
        self.color = random.choice(COLORS)

    async def run(self) -> None:
        if self.depends_on:
            print_header(f"running dependencies for '{self.job_id}'")
            await asyncio.gather(
                *[self.depman.await_job(job_id) for job_id in self.depends_on]
            )

        if self.steps:
            await self.run_steps()

    async def run_steps(self):
        print_header(f"running job '{self.job_id}' steps in '{self.workdir}'")
        for step in self.steps:
            step = Step(step) if isinstance(step, str) else step
            stdout, stderr = await step.run(self.env, self.workdir)
            print(self._prefix(step.cmd))
            pstdout = self._print_stream(stdout)
            pstderr = self._print_stream(stderr)
            await asyncio.gather(pstdout, pstderr)
        print_header(f"job steps '{self.job_id}' done")

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
    def from_toml(
        depman: "DependencyManager", job_id: str, data: dict[str, Any]
    ) -> "Job":
        return Job(
            depman,
            job_id,
            steps=data.get("steps", []),
            env=data.get("env"),
            depends_on=data.get("depends_on", []),
            workdir=data.get("workdir"),
        )


class DependencyManager:

    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.jobs_done: dict[str, bool] = {}

    async def await_job(self, job_id: str) -> None:
        if self.jobs_done.get(job_id, False):
            return

        job = self.jobs.get(job_id)
        if job is None:
            print_error(f"job '{job_id}' not found!")
            return

        await job.run()
        self.jobs_done[job_id] = True

    def initialize(self, jobs: list[Job]) -> None:
        for job in jobs:
            self.jobs[job.job_id] = job

    def find_jobs(self, job_ids: list[str]) -> list[Job]:
        return [job for job in self.jobs.values() if job.job_id in job_ids]


def print_header(msg: str) -> None:
    print(TextMode.BOLD, "===> ", msg, TextMode.RESET, sep="")


def print_error(msg: str) -> None:
    print(TextMode.BOLD, TextMode.RED, "===> ", msg, TextMode.RESET)


class JobDef:

    def __init__(
        self, steps: list[str], depends_on: list["JobDef"], workdir: str | None = None
    ) -> None:
        self.steps = steps
        self.depends_on = depends_on
        self.workdir = workdir


def job(
    *steps: str, depends_on: list[JobDef] | None = None, workdir: str | None = None
) -> JobDef:
    return JobDef(list(steps), depends_on or [], workdir)


class Gør:

    def __init__(self, depman: DependencyManager) -> None:
        self.depman = depman

    async def run(self, job_ids: list[str]) -> None:
        await asyncio.gather(*[job.run() for job in self.depman.find_jobs(job_ids)])

    @staticmethod
    def load_toml(path: str) -> "Gør":
        data = toml.load(path)

        depman = DependencyManager()
        jobs = [
            Job.from_toml(depman, job_id, job_data)
            for job_id, job_data in data["jobs"].items()
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
                depman,
                job_id,
                job_def.steps,
                depends_on=_find_job_dep_ids(job_defs, job_def.depends_on),
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
