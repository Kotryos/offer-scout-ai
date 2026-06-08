import logging

import anyio

from scout_coordinator.attachments.extractor import extract_attachment_text, html_to_text, is_supported
from scout_coordinator.integrations.gmail import GmailSmtpSender
from scout_coordinator.integrations.resend import ResendClient
from scout_coordinator.integrations.scout_agent import ScoutAgentClient
from scout_coordinator.models import AttachmentText, ReceivedAttachment, ReceivedEmail

log = logging.getLogger(__name__)


class EmailProcessor:
    def __init__(
        self,
        resend_client: ResendClient,
        scout_agent_client: ScoutAgentClient,
        gmail_sender: GmailSmtpSender,
        profile_context: str,
        max_attachment_bytes: int,
        max_offer_text_chars: int,
    ) -> None:
        self._resend_client = resend_client
        self._scout_agent_client = scout_agent_client
        self._gmail_sender = gmail_sender
        self._profile_context = profile_context
        self._max_attachment_bytes = max_attachment_bytes
        self._max_offer_text_chars = max_offer_text_chars

    async def process_email(self, email_id: str) -> None:
        log.info("Processing email %s", email_id)
        email = await self._resend_client.get_received_email(email_id)
        log.info("Fetched email %s with %s attachment(s)", email_id, len(email.attachments))

        attachments = await self._extract_attachments(email)
        offer_text = self._build_offer_text(email, attachments)
        log.info("Built offer text for email %s with %s chars", email_id, len(offer_text))

        evaluation = await self._scout_agent_client.evaluate_offer(
            offer_text=offer_text,
            profile_context=self._profile_context,
        )
        log.info("Received evaluation for email %s with %s chars", email_id, len(evaluation))

        await self._gmail_sender.send_reply(
            to_email=email.from_email,
            subject=email.subject or "Scout evaluation",
            body=evaluation,
            original_message_id=email.message_id,
        )
        log.info("Sent evaluation reply for email %s", email_id)

    async def _extract_attachments(self, email: ReceivedEmail) -> list[AttachmentText]:
        results: list[AttachmentText] = []

        for attachment in email.attachments:
            if attachment.size > self._max_attachment_bytes:
                log.info("Skipping attachment %s: attachment is too large", attachment.filename)
                results.append(self._skipped(attachment, "attachment is too large"))
                continue

            if not is_supported(attachment.content_type):
                log.info("Skipping attachment %s: unsupported content type", attachment.filename)
                results.append(self._skipped(attachment, "unsupported content type"))
                continue

            log.info("Extracting attachment %s", attachment.filename)
            download_url = await self._resend_client.get_attachment_download_url(email.id, attachment.id)
            data = await self._resend_client.download_attachment(download_url)

            extracted = await anyio.to_thread.run_sync(
                extract_attachment_text,
                attachment.filename,
                attachment.content_type,
                data,
            )
            results.append(extracted)
            log.info("Extracted attachment %s with %s chars", attachment.filename, len(extracted.text))

        return results

    def _build_offer_text(self, email: ReceivedEmail, attachments: list[AttachmentText]) -> str:
        body = (email.text or "").strip()
        if not body and email.html:
            body = html_to_text(email.html)

        sections = [
            "Email Subject:",
            email.subject or "(no subject)",
            "",
            "Email Body:",
            body or "(empty body)",
        ]

        for attachment in attachments:
            sections.extend(
                [
                    "",
                    f"Attachment: {attachment.filename}",
                    f"Content-Type: {attachment.content_type}",
                ]
            )

            if attachment.skipped:
                sections.append(f"Skipped attachment: {attachment.reason}")
            else:
                sections.append(attachment.text or "(no extractable text)")

        offer_text = "\n".join(sections).strip()
        if len(offer_text) > self._max_offer_text_chars:
            return offer_text[: self._max_offer_text_chars] + "\n\n[Content truncated by scout-coordinator]"
        return offer_text

    @staticmethod
    def _skipped(attachment: ReceivedAttachment, reason: str) -> AttachmentText:
        return AttachmentText(
            filename=attachment.filename,
            content_type=attachment.content_type,
            text="",
            skipped=True,
            reason=reason,
        )
