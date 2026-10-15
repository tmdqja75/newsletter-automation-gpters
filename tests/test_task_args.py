"""The `task` tool must keep a brief sent under an undeclared key and still accept
the injected `runtime` (extra="forbid" once broke every call)."""

from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool

import deepagents.middleware.subagents as deepagents_subagents
import src.main  # noqa: F401  (installs the patched schema)


def _task_tool(received):
    # Same shape as deepagents' task tool: injected runtime + the module-global schema.
    def task(description: str, subagent_type: str, runtime: ToolRuntime) -> str:
        received.update(description=description, subagent_type=subagent_type, runtime=runtime)
        return "ok"

    return StructuredTool.from_function(
        name="task", func=task, infer_schema=False,
        args_schema=deepagents_subagents.TaskToolSchema,
    )


def test_injected_runtime_still_accepted():
    received = {}
    runtime = object()
    _task_tool(received).invoke({"description": "d", "subagent_type": "article-writer", "runtime": runtime})
    assert received == {"description": "d", "subagent_type": "article-writer", "runtime": runtime}


def test_stray_instruction_folded_into_description():
    received = {}
    _task_tool(received).invoke({
        "description": "재작성", "subagent_type": "article-writer",
        "instruction": "https://blog.example/post", "runtime": object(),
    })
    assert received["description"] == "재작성\n\nhttps://blog.example/post"


def test_instruction_without_description_still_reaches_subagent():
    received = {}
    _task_tool(received).invoke({
        "subagent_type": "article-writer", "instruction": "https://blog.example/post", "runtime": object(),
    })
    assert received["description"] == "https://blog.example/post"
