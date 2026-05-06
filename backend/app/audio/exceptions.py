from app.core.exceptions import NotFoundError


class AudioTrackNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Audio track not found")
