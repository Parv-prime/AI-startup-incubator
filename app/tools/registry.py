from __future__ import annotations

from app.core.errors import ToolPermissionError, ToolValidationError
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolValidationError(f"Unknown tool '{name}'.") from exc

    def list_metadata(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "permission": tool.permission.value,
                "parameters": tool.spec().parameters,
            }
            for tool in self._tools.values()
        ]

    def specs(self, names: list[str] | None = None) -> list:
        if names is None:
            return [tool.spec() for tool in self._tools.values()]
        return [self.get(name).spec() for name in names]

    async def execute(
        self,
        name: str,
        arguments: dict,
        context: ToolContext,
        *,
        allowed_permissions: set[PermissionLevel] | None = None,
    ) -> dict:
        tool = self.get(name)
        allowed = allowed_permissions or {
            PermissionLevel.READ_ONLY,
            PermissionLevel.WRITE,
        }
        if tool.permission not in allowed:
            raise ToolPermissionError(
                f"Tool '{name}' requires {tool.permission.value} permission."
            )
        if tool.permission == PermissionLevel.HIGH_RISK and not context.confirmed:
            raise ToolPermissionError(
                f"High-risk tool '{name}' requires explicit confirmation."
            )
        return await tool.run(arguments, context)
