import glob
import os
from pathlib import Path
from typing import Protocol


class Rule(Protocol):
    def rule_name(self) -> str: ...
    def can_skip(self) -> bool: ...


class FileRule:
    def __init__(self, source: str, target: str) -> None:
        self.source = Path(source)
        self.target = Path(target)

    def can_skip(self) -> bool:
        if not self.target.exists():
            return False

        source_mtime = os.stat(self.source).st_mtime
        target_mtime = os.stat(self.target).st_mtime
        return source_mtime <= target_mtime

    def rule_name(self) -> str:
        return f"FileFileRule(source={self.source}, target={self.target})"


class SourceGlobRule:
    def __init__(self, source: str, target: str) -> None:
        self.source = source
        self.target = Path(target)

    def can_skip(self) -> bool:
        if not self.target.exists():
            return False

        source_mtime = max(os.stat(s).st_mtime for s in glob.glob(self.source))
        target_mtime = os.stat(self.target).st_mtime
        return source_mtime <= target_mtime

    def rule_name(self) -> str:
        return f"SourceGlobRule(source={self.source}, target={self.target})"
