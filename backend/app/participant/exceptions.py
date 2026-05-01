from app.core.exceptions import BadRequestError, NotFoundError


class ParticipantNameUnresolvedError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("The participant name could not be resolved")


class ParticipantNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("The participant not found")
