"""Domain failures translated to useful, sanitized HTTP errors."""


class DatabaseUnavailable(Exception):
    """FalkorDB cannot be reached; never replace it with synthetic answers."""


class GraphQueryError(Exception):
    """A graph command failed; log the cause without exposing internals in HTTP."""


class EntityNotFound(Exception):
    def __init__(self, label: str, entity_id: str):
        self.label = label
        self.entity_id = entity_id
        super().__init__(f"{label} {entity_id} was not found")


class OperationError(Exception):
    """An intentionally public, sanitized bounded-operation failure."""

    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)
