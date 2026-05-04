from app.core.exceptions import BadRequestError


class UploadFormatError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("Unsupported audio format")


class UploadTooLargeError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("Uploaded file exceeds the size limit")


class UploadDurationExceededError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("Uploaded recording exceeds the duration limit")


class UploadDecodeError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("Could not decode the uploaded audio")
