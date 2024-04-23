from datetime import datetime

import pytest
from goer.dep import Dependency
from goer.depman import DependencyManager
from goer.text import TextMode

DEFAULT_LAST_MODIFIED = datetime(2024, 1, 1)


class FakeDependency(Dependency):
    def __init__(
        self, dep_id: str, depends_on: list[Dependency], result: bool = True
    ) -> None:
        self.call_count = 0
        self._result = result
        self._last_modified = DEFAULT_LAST_MODIFIED
        super().__init__(dep_id=dep_id, depends_on=depends_on, color=TextMode.BLUE)

    @property
    def ran_dep(self) -> bool:
        return self.call_count > 0

    @property
    def last_modified(self) -> datetime:
        return self._last_modified

    async def run(self) -> bool:
        self.call_count += 1
        return self._result


@pytest.mark.asyncio()
async def test_run_returns_result() -> None:
    dep = FakeDependency("dep-id", depends_on=[])
    depman = DependencyManager([dep])

    result = await depman.run_dep(dep)

    assert result is True
    assert dep.ran_dep is True


@pytest.mark.asyncio()
async def test_runs_dep_tree() -> None:
    dep_1 = FakeDependency("dep-1", [])
    dep_2 = FakeDependency("dep-2", [])
    dep_3 = FakeDependency("dep-3", [dep_1, dep_2])
    dep_4 = FakeDependency("dep-4", [])
    dep_5 = FakeDependency("dep-5", [dep_4, dep_3])
    depman = DependencyManager([dep_1, dep_2, dep_3, dep_4, dep_5])

    result = await depman.run_dep(dep_5)

    assert result is True
    assert dep_1.ran_dep is True
    assert dep_2.ran_dep is True
    assert dep_3.ran_dep is True
    assert dep_4.ran_dep is True
    assert dep_5.ran_dep is True


@pytest.mark.asyncio()
async def test_returns_dep_run_result() -> None:
    dep = FakeDependency("dep_id", [], result=False)
    depman = DependencyManager([dep])

    result = await depman.run_dep(dep)

    assert result is False
    assert dep.ran_dep is True


@pytest.mark.asyncio()
async def test_only_runs_dependencies_once() -> None:
    dep_1 = FakeDependency("dep-1", [])
    dep_2 = FakeDependency("dep-2", [dep_1])
    dep_3 = FakeDependency("dep-3", [dep_2, dep_1])
    dep_4 = FakeDependency("dep-4", [dep_3, dep_2, dep_1])
    depman = DependencyManager([dep_1, dep_2, dep_3, dep_4])

    result = await depman.run_dep(dep_4)

    assert result is True
    assert dep_1.call_count == 1
    assert dep_2.call_count == 1
    assert dep_3.call_count == 1
    assert dep_4.call_count == 1
