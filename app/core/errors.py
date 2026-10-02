class AgentError(Exception):
    """Base application error."""

    code = "agent_error"
    recoverable = True

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RecoverableError(AgentError):
    recoverable = True


class FatalError(AgentError):
    recoverable = False


class ModelUnavailableError(RecoverableError):
    code = "model_unavailable"


class ModelTimeoutError(RecoverableError):
    code = "model_timeout"


class ToolValidationError(RecoverableError):
    code = "invalid_tool_arguments"


class ToolExecutionError(RecoverableError):
    code = "tool_failure"


class ToolPermissionError(FatalError):
    code = "tool_permission_denied"


class AgentTimeoutError(RecoverableError):
    code = "agent_timeout"


class AgentCancelledError(RecoverableError):
    code = "agent_cancelled"


class MaxIterationsError(RecoverableError):
    code = "max_iterations"
