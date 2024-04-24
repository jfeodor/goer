import asyncio
import os
import random
from asyncio import StreamReader, subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

from goer.dep import Dependency, DependencyDef
from goer.text import COLORS, TextMode


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
class ShellScript(Dependency):
    color: str = field(default_factory=lambda: random.choice(COLORS))
    depends_on: list["Dependency"] = field(default_factory=list)
    steps: Sequence[Step | str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=lambda: dict(os.environ))
    workdir: str | None = None
    targets: list[str] | None = None

    async def _run(self) -> bool:
        exit_code = await self.run_steps()
        if exit_code is None:
            return True

        if exit_code != 0:
            raise RuntimeError(f"shell script failed with exit code {exit_code}")

        return True

    async def run_steps(self) -> int | None:
        workdir = self.workdir or os.curdir
        for step in self.steps:
            step = Step(step) if isinstance(step, str) else step
            proc, stdout, stderr = await step.run(self.env, workdir)
            print(self._prefix(step.cmd, "$"))
            pstdout = self._print_stream(stdout)
            pstderr = self._print_stream(stderr)
            await asyncio.gather(pstdout, pstderr)
            if exit_code := await proc.wait() != 0:
                return exit_code

        return None

    async def _print_stream(self, stream: StreamReader) -> None:
        while not stream.at_eof():
            raw_ln = await stream.readline()
            if not raw_ln:
                continue
            ln = raw_ln.decode().rstrip("\n")
            print(self._prefix(ln, "|"))

    def _prefix(self, s: str, sep: str) -> str:
        return f"{self.color}{self.dep_id}{sep}{TextMode.RESET}{s}"

    @property
    def last_modified(self) -> datetime:
        if self.targets:
            return max(_target_last_modified(target) for target in self.targets)
        else:
            return datetime.fromtimestamp(0)


def _target_last_modified(target: str) -> datetime:
    try:
        return datetime.fromtimestamp(os.stat(target).st_mtime)
    except FileNotFoundError:
        return datetime.fromtimestamp(0)


@dataclass
class ShellScriptDef(DependencyDef):
    steps: list[str]
    dependencies: list[DependencyDef]
    workdir: str | None = None
    targets: list[str] | None = None

    @property
    def depends_on(self) -> list[DependencyDef]:
        return self.dependencies

    def initialize(
        self, dep_id: str, color: str, depends_on: list[Dependency]
    ) -> ShellScript:
        return ShellScript(
            dep_id,
            color=color,
            depends_on=depends_on,
            steps=self.steps,
            workdir=self.workdir,
            targets=self.targets,
        )


def shell(
    *steps: str,
    depends_on: list[DependencyDef] | None = None,
    workdir: str | None = None,
    targets: list[str] | None = None,
) -> ShellScriptDef:
    return ShellScriptDef(list(steps), depends_on or [], workdir, targets)
