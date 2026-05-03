from app.core.exceptions import BadRequestError, NotFoundError


class GraphNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Graph not found")


class UngroundedExtractionError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("Decision/ActionItem/OpenQuestion is missing a SOURCE edge to an utterance")


class UnknownUtteranceRefError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("LLM referenced an utterance id outside of the window")


class InvalidGraphOperationError(BadRequestError):
    def __init__(self) -> None:
        super().__init__("Graph operation references unknown temp_id or node id")
