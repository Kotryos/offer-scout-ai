from pydantic import BaseModel, Field


class ResendWebhookAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    content_disposition: str | None = None
    content_id: str | None = None


class ResendWebhookData(BaseModel):
    email_id: str
    from_email: str = Field(alias="from")
    to: list[str] = Field(default_factory=list)
    subject: str | None = None
    message_id: str | None = None
    attachments: list[ResendWebhookAttachment] = Field(default_factory=list)


class ResendWebhookEvent(BaseModel):
    type: str
    data: ResendWebhookData


class ReceivedAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int = 0
    content_disposition: str | None = None
    content_id: str | None = None


class ReceivedEmail(BaseModel):
    id: str
    from_email: str = Field(alias="from")
    to: list[str] = Field(default_factory=list)
    subject: str | None = None
    message_id: str | None = None
    html: str | None = None
    text: str | None = None
    attachments: list[ReceivedAttachment] = Field(default_factory=list)


class EmailProcessingTask(BaseModel):
    email_id: str
    webhook_id: str | None = None


class AttachmentText(BaseModel):
    filename: str
    content_type: str
    text: str
    skipped: bool = False
    reason: str | None = None
