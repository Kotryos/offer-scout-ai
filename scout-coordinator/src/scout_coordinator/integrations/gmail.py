from email.message import EmailMessage

import aiosmtplib


class GmailSmtpSender:
    def __init__(
        self,
        username: str,
        app_password: str,
        host: str,
        port: int,
    ) -> None:
        self._username = username
        self._app_password = app_password
        self._host = host
        self._port = port

    async def send_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        original_message_id: str | None = None,
    ) -> None:
        message = EmailMessage()
        message["From"] = self._username
        message["To"] = to_email
        message["Subject"] = self._reply_subject(subject)

        if original_message_id:
            message["In-Reply-To"] = original_message_id
            message["References"] = original_message_id

        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            start_tls=True,
            username=self._username,
            password=self._app_password,
        )

    @staticmethod
    def _reply_subject(subject: str) -> str:
        if subject.lower().startswith("re:"):
            return subject
        return f"Re: {subject}"
