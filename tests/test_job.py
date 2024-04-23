import pytest
from goer.job import Job


@pytest.mark.asyncio
async def test_job() -> None:
    job = Job("my_job", steps=["echo hello world"])

    result = await job.run()

    assert result is True
