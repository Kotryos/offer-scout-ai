from email.message import EmailMessage

from scout_coordinator.integrations import gmail
from scout_coordinator.integrations.gmail import GmailSmtpSender


async def test_gmail_sender_sends_plain_text_reply(monkeypatch) -> None:
    sent: dict = {}

    async def fake_send(message: EmailMessage, **kwargs) -> None:
        sent["message"] = message
        sent["kwargs"] = kwargs

    monkeypatch.setattr(gmail.aiosmtplib, "send", fake_send)
    sender = GmailSmtpSender(
        username="sender@gmail.com",
        app_password="app-password",
        host="smtp.gmail.com",
        port=587,
    )

    await sender.send_reply(
        to_email="recipient@example.com",
        subject="Test offer",
        body="Worth pursuing.",
        original_message_id="<message-1@example.com>",
    )

    message = sent["message"]
    assert message["From"] == "sender@gmail.com"
    assert message["To"] == "recipient@example.com"
    assert message["Subject"] == "Re: Test offer"
    assert message["In-Reply-To"] == "<message-1@example.com>"
    assert message["References"] == "<message-1@example.com>"
    assert message.get_content().strip() == "Worth pursuing."
    assert sent["kwargs"] == {
        "hostname": "smtp.gmail.com",
        "port": 587,
        "start_tls": True,
        "username": "sender@gmail.com",
        "password": "app-password",
    }


async def test_gmail_sender_does_not_duplicate_reply_prefix(monkeypatch) -> None:
    sent: dict = {}

    async def fake_send(message: EmailMessage, **kwargs) -> None:
        sent["message"] = message

    monkeypatch.setattr(gmail.aiosmtplib, "send", fake_send)
    sender = GmailSmtpSender(
        username="sender@gmail.com",
        app_password="app-password",
        host="smtp.gmail.com",
        port=587,
    )

    await sender.send_reply(
        to_email="recipient@example.com",
        subject="Re: Test offer",
        body="Worth pursuing.",
    )

    assert sent["message"]["Subject"] == "Re: Test offer"


async def test_gmail_sender_omits_threading_headers_without_original_message_id(monkeypatch) -> None:
    sent: dict = {}

    async def fake_send(message: EmailMessage, **kwargs) -> None:
        sent["message"] = message

    monkeypatch.setattr(gmail.aiosmtplib, "send", fake_send)
    sender = GmailSmtpSender(
        username="sender@gmail.com",
        app_password="app-password",
        host="smtp.gmail.com",
        port=587,
    )

    await sender.send_reply(
        to_email="recipient@example.com",
        subject="Test offer",
        body="Worth pursuing.",
    )

    message = sent["message"]
    assert message["Subject"] == "Re: Test offer"
    assert "In-Reply-To" not in message
    assert "References" not in message
