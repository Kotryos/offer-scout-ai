from scout_coordinator.models import ReceivedAttachment, ReceivedEmail
from scout_coordinator.processing.email_processor import EmailProcessor


class FakeResendClient:
    def __init__(self) -> None:
        self.requested_attachment_ids: list[str] = []
        self.download_urls: list[str] = []
        self.email = ReceivedEmail(
            id="email-1",
            **{
                "from": "sender@example.com",
                "subject": "Test offer",
                "message_id": "<message-1@example.com>",
            },
            text="Please check this offer.",
            attachments=[
                ReceivedAttachment(
                    id="txt-1",
                    filename="offer.txt",
                    content_type="text/plain",
                    size=24,
                ),
                ReceivedAttachment(
                    id="zip-1",
                    filename="archive.zip",
                    content_type="application/zip",
                    size=10,
                ),
            ],
        )

    async def get_received_email(self, email_id: str) -> ReceivedEmail:
        assert email_id == "email-1"
        return self.email

    async def get_attachment_download_url(self, email_id: str, attachment_id: str) -> str:
        assert email_id == "email-1"
        assert attachment_id == "txt-1"
        self.requested_attachment_ids.append(attachment_id)
        return "https://download.example/offer.txt"

    async def download_attachment(self, download_url: str) -> bytes:
        assert download_url == "https://download.example/offer.txt"
        self.download_urls.append(download_url)
        return b"Java B2B"


class FakeScoutAgentClient:
    def __init__(self) -> None:
        self.offer_text = ""
        self.profile_context = ""

    async def evaluate_offer(self, offer_text: str, profile_context: str) -> str:
        self.offer_text = offer_text
        self.profile_context = profile_context
        return "Worth pursuing."


class FakeGmailSender:
    def __init__(self) -> None:
        self.sent: dict[str, str | None] = {}

    async def send_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        original_message_id: str | None = None,
    ) -> None:
        self.sent = {
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "original_message_id": original_message_id,
        }


async def test_process_email_sends_combined_offer_text_to_agent_and_replies() -> None:
    resend = FakeResendClient()
    scout_agent = FakeScoutAgentClient()
    gmail = FakeGmailSender()
    processor = EmailProcessor(
        resend_client=resend,  # type: ignore[arg-type]
        scout_agent_client=scout_agent,  # type: ignore[arg-type]
        gmail_sender=gmail,  # type: ignore[arg-type]
        profile_context="Senior Java developer",
        max_attachment_bytes=5_000_000,
        max_offer_text_chars=50_000,
    )

    await processor.process_email("email-1")

    assert "Email Subject:\nTest offer" in scout_agent.offer_text
    assert "Email Body:\nPlease check this offer." in scout_agent.offer_text
    assert "Attachment: offer.txt" in scout_agent.offer_text
    assert "Java B2B" in scout_agent.offer_text
    assert "Skipped attachment: unsupported content type" in scout_agent.offer_text
    assert scout_agent.profile_context == "Senior Java developer"
    assert gmail.sent == {
        "to_email": "sender@example.com",
        "subject": "Test offer",
        "body": "Worth pursuing.",
        "original_message_id": "<message-1@example.com>",
    }


async def test_process_email_uses_html_body_when_text_body_is_missing() -> None:
    resend = FakeResendClient()
    resend.email.text = None
    resend.email.html = "<p>Praca zdalna</p><p>Java</p>"
    resend.email.attachments = []
    scout_agent = FakeScoutAgentClient()
    gmail = FakeGmailSender()
    processor = EmailProcessor(
        resend_client=resend,  # type: ignore[arg-type]
        scout_agent_client=scout_agent,  # type: ignore[arg-type]
        gmail_sender=gmail,  # type: ignore[arg-type]
        profile_context="profile",
        max_attachment_bytes=5_000_000,
        max_offer_text_chars=50_000,
    )

    await processor.process_email("email-1")

    assert "Email Body:\nPraca zdalna\nJava" in scout_agent.offer_text
    assert resend.requested_attachment_ids == []


async def test_process_email_truncates_large_offer_text() -> None:
    resend = FakeResendClient()
    resend.email.text = "x" * 100
    scout_agent = FakeScoutAgentClient()
    gmail = FakeGmailSender()
    processor = EmailProcessor(
        resend_client=resend,  # type: ignore[arg-type]
        scout_agent_client=scout_agent,  # type: ignore[arg-type]
        gmail_sender=gmail,  # type: ignore[arg-type]
        profile_context="profile",
        max_attachment_bytes=5_000_000,
        max_offer_text_chars=80,
    )

    await processor.process_email("email-1")

    assert len(scout_agent.offer_text) > 80
    assert scout_agent.offer_text.endswith("[Content truncated by scout-coordinator]")


async def test_process_email_skips_oversized_attachment_without_downloading_it() -> None:
    resend = FakeResendClient()
    resend.email.attachments = [
        ReceivedAttachment(
            id="large-1",
            filename="large-offer.txt",
            content_type="text/plain",
            size=10,
        )
    ]
    scout_agent = FakeScoutAgentClient()
    gmail = FakeGmailSender()
    processor = EmailProcessor(
        resend_client=resend,  # type: ignore[arg-type]
        scout_agent_client=scout_agent,  # type: ignore[arg-type]
        gmail_sender=gmail,  # type: ignore[arg-type]
        profile_context="profile",
        max_attachment_bytes=5,
        max_offer_text_chars=50_000,
    )

    await processor.process_email("email-1")

    assert "Attachment: large-offer.txt" in scout_agent.offer_text
    assert "Skipped attachment: attachment is too large" in scout_agent.offer_text
    assert resend.requested_attachment_ids == []
    assert resend.download_urls == []
