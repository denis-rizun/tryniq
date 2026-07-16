from app.core.base_schema import BaseSchema


class MarkdownExport(BaseSchema):
    body: str
    filename: str
    media_type: str
