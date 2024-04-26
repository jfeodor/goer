"""Abstract dependencies.

This module contains the abstract classes, which defines the interface and some
basic functionality of dependencies. Both the `DependencyDef`s which the user
creates in a `Goerfile.py`, and the internal `Dependency` instances, which are
used to actually execute the dependencies.
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from goer.text import COLORS, TextMode, print_error


@dataclass
class Dependency(ABC):
    """An abstract dependency.

    Should implement the `_run` method, and potentially override the
    `last_modified` property.
    """

    dep_id: str
    color: str = field(default_factory=lambda: random.choice(COLORS))
    depends_on: list["Dependency"] = field(default_factory=list)

    @property
    def pretty_id(self) -> str:
        """A colorized pretty ID, for printing in the terminal."""
        return f"{self.color}{self.dep_id}{TextMode.RESET}"

    @property
    def last_modified(self) -> datetime:
        """The dependency manager runs dependencies, if their `last_modified`
        value is lower than that of their sub-dependencies."""
        return datetime.now()

    async def run(self) -> bool:
        """Runs the dependency (e.g. `_run`), handling exceptions by printing an
        error message and returning `False`."""
        try:
            return await self._run()
        except Exception as e:
            print_error("error occurred running '", self.pretty_id, f"': {e}")
            return False

    @abstractmethod
    async def _run(self) -> bool:
        """The actual run function for the dependency. Must be implemented."""


class DependencyDef(ABC):
    """An abstract dependency definition.

    Should implement the `depends_on` property, and the `initialize` factory
    method, which returns a corresponding `Dependency`.

    Implementations of `DependencyDef` are used to actually define dependencies
    in `Goerfile.py`.
    """

    @property
    @abstractmethod
    def depends_on(self) -> list["DependencyDef"]:
        """Should return the dependency definitions, this dependency defintion
        depends on."""

    @abstractmethod
    def initialize(
        self, dep_id: str, color: str, depends_on: list[Dependency]
    ) -> Dependency:
        """Should return a `Dependency` for this definition. Most commonly a
        `DependencyDef` implementation has a corresponding `Dependency`
        implementation."""
