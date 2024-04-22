import asyncio
import os
import random
from asyncio import StreamReader, subprocess
from dataclasses import dataclass, field
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
