from app.core.exceptions import BadRequestError, NotFoundError


class MeetingNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Meeting not found")


class InvalidMeetUrlError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("Meet URL is invalid")
