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


class ModelAuthError(ModelUnavailableError):
    """The LLM provider rejected the configured credentials (401/403)."""

    code = "model_auth_failed"


class ModelRateLimitError(ModelUnavailableError):
    """The LLM provider is rate-limiting this deployment (429)."""

    code = "model_rate_limited"


class ModelResponseError(ModelUnavailableError):
    """The LLM provider returned a response that could not be parsed."""

    code = "model_bad_response"


class ModelConfigurationError(FatalError):
    """The selected LLM provider is missing required configuration."""

    code = "model_misconfigured"


class RateLimitExceededError(RecoverableError):
    """This user sent too many requests in a short window (per-user throttle)."""

    code = "rate_limited"
