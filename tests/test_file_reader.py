from pathlib import Path

import pytest

from app.core.errors import ToolExecutionError
from app.tools.base import ToolContext
from app.tools.builtin.file_reader import FileReaderTool


@pytest.mark.asyncio
async def test_file_reader_rejects_path_traversal():
    tool = FileReaderTool()
    with pytest.raises(ToolExecutionError):
        await tool.run(
            {"relative_path": "../.env"},
            ToolContext(user_id="user_1", project_id="proj_1", run_id="run_test"),
        )


@pytest.mark.asyncio
async def test_file_reader_reads_sandbox_file():
    tool = FileReaderTool()
    result = await tool.run(
        {"relative_path": "safeplate-sodium.txt"},
        ToolContext(user_id="user_1", project_id="proj_1", run_id="run_test"),
    )
    assert "2 grams" in result["content"]
    assert Path(result["path"]).as_posix().endswith("data/knowledge/safeplate-sodium.txt")
