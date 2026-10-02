from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.errors import ToolExecutionError, ToolValidationError
from app.models.base import ToolSpec
from app.tools.permissions import PermissionLevel


class ToolContext(BaseModel):
    user_id: str
    project_id: str
    run_id: str
    confirmed: bool = False


class BaseTool(ABC):
    name: str
    description: str
    permission: PermissionLevel
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    def spec(self) -> ToolSpec:
        schema = self.input_model.model_json_schema()
        parameters = {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        }
        return ToolSpec(name=self.name, description=self.description, parameters=parameters)

    def validate_input(self, arguments: dict[str, Any]) -> BaseModel:
        try:
            return self.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolValidationError(
                f"Invalid arguments for tool '{self.name}'.",
                details={"errors": exc.errors()},
            ) from exc

    async def run(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        payload = self.validate_input(arguments)
        try:
            result = await self.execute(payload, context)
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(
                f"Tool '{self.name}' failed.",
                details={"error": str(exc)},
            ) from exc
        return self.output_model.model_validate(result).model_dump()

    @abstractmethod
    async def execute(self, payload: BaseModel, context: ToolContext) -> Any: ...
