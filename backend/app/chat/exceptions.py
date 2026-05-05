from app.core.exceptions import BadRequestError, ConflictError, NotFoundError


class ChatSessionNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Chat session not found")


class MeetingNotFinalizedError(ConflictError):
    def __init__(self) -> None:
        super().__init__("Meeting is not finalized yet")


class InvalidChatScopeError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("Invalid chat scope")


class ChatGenerationError(ConflictError):
    def __init__(self) -> None:
        super().__init__("Failed to generate chat response")
