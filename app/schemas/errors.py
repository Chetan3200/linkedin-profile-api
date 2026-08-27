from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: APIError
