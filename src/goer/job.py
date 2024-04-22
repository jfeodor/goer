from asyncio import StreamReader, subprocess
import asyncio
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
