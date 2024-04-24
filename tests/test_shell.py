import pytest
from goer.shell import ShellScript


@pytest.mark.asyncio
async def test_shellscript() -> None:
    sh = ShellScript("my_job", steps=["echo hello world"])

    result = await sh.run()

    assert result is True
