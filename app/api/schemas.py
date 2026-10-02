from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    version: str
    model_runtime: str
    model_name: str
    llm_status: str
    database_status: str
    ml_model_status: str


class ToolListResponse(BaseModel):
    tools: list[dict]
