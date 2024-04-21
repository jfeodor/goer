import asyncio
import os
import random
import time
import toml

from asyncio import subprocess
from asyncio.streams import StreamReader
from typing import Any, Optional, Sequence

from goer.rules import Rule


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


class Job:
    def __init__(
        self,
        depman: "DependencyManager",
        job_id: str,
        steps: Sequence[Step | str] | None = None,
        env: dict[str, str] | None = None,
        depends_on: "list[str] | None" = None,
        workdir: str | None = None,
        rules: list[Rule] | None = None,
    ) -> None:
        self.depman = depman
        self.job_id = job_id
        self.steps = steps or []
        self.env = env or dict(os.environ)
        self.depends_on = depends_on or []
        self.workdir = workdir or os.curdir
        self.rules = rules
        self.color = random.choice(COLORS)

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
        if self.depends_on:
            print_header("running dependencies for '", self.pretty_job_id, "'")
            results = await asyncio.gather(
                *[self.depman.await_job(job_id) for job_id in self.depends_on]
            )
            if not all(results):
                print_error("dependency failed for '", self.pretty_job_id, "'")
                return False

        if self.rules and all(rule.can_skip() for rule in self.rules):
            print_header("skipping '", self.pretty_job_id, "' since all rules passed")
            return True

        if self.steps:
            if exit_code := await self.run_steps():
                print_error(
                    "job '", self.pretty_job_id, f"' failed with exit code {exit_code}"
                )
                return False

        print_header("job '", self.pretty_job_id, "' done")
        return True

    async def run_steps(self) -> Optional[int]:
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

    async def await_job(self, job_id: str) -> bool:
        try:
            return await self._await_job(job_id)
        except Exception as e:
            print_error(f"job '{job_id}' failed with error: {e}")
            return False

    async def _await_job(self, job_id: str) -> bool:
        if self.jobs_done.get(job_id, False):
            return True

        job = self.jobs.get(job_id)
        if job is None:
            print_error(f"job '{job_id}' not found!")
            return False

        job_exit_code = await job._run()
        self.jobs_done[job_id] = True
        return job_exit_code

    def initialize(self, jobs: list[Job]) -> None:
        for job in jobs:
            self.jobs[job.job_id] = job

    def find_jobs(self, job_ids: list[str]) -> list[Job]:
        return [job for job in self.jobs.values() if job.job_id in job_ids]


def print_header(*args: str) -> None:
    msgs = []
    for arg in args:
        msgs.append(arg)
        msgs.append(TextMode.RESET)
        msgs.append(TextMode.BOLD)
    print(TextMode.BOLD, "--- ", *msgs, TextMode.RESET, sep="")


def print_error(*args: str) -> None:
    msgs = []
    for arg in args:
        msgs.append(arg)
        msgs.append(TextMode.RED)
    print(TextMode.BOLD, TextMode.RED, "--- ", *msgs, TextMode.RESET, sep="")


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


class Gør:

    def __init__(self, depman: DependencyManager) -> None:
        self.depman = depman

    def list_job_ids(self) -> list[str]:
        return [job_id for job_id in self.depman.jobs.keys()]

    async def run(self, job_ids: list[str]) -> bool:
        t = time.time()

        jobs = self.depman.find_jobs(job_ids)
        results = await asyncio.gather(*[job._run() for job in jobs])
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
                rules=job_def.rules,
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
