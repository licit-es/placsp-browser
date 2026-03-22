import uuid

from pydantic import BaseModel


class PublicationStatusWrite(BaseModel):
    valid_notice_info_id: uuid.UUID
    publication_media_name: str | None = None


class PublicationStatusRead(PublicationStatusWrite):
    id: uuid.UUID
