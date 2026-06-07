from io import BytesIO

from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

from scout_coordinator.models import AttachmentText

SUPPORTED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/html",
}


def is_supported(content_type: str) -> bool:
    return content_type.lower().split(";")[0].strip() in SUPPORTED_CONTENT_TYPES


def extract_attachment_text(filename: str, content_type: str, data: bytes) -> AttachmentText:
    normalized_type = content_type.lower().split(";")[0].strip()

    try:
        if normalized_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = _extract_docx(data)
        elif normalized_type == "application/pdf":
            text = _extract_pdf(data)
        elif normalized_type in {"text/plain", "text/markdown"}:
            text = data.decode("utf-8", errors="replace")
        elif normalized_type == "text/html":
            text = _extract_html(data.decode("utf-8", errors="replace"))
        else:
            return AttachmentText(
                filename=filename,
                content_type=content_type,
                text="",
                skipped=True,
                reason="unsupported content type",
            )
    except Exception:
        return AttachmentText(
            filename=filename,
            content_type=content_type,
            text="",
            skipped=True,
            reason="could not extract text",
        )

    return AttachmentText(
        filename=filename,
        content_type=content_type,
        text=text.strip(),
    )


def html_to_text(html: str) -> str:
    return _extract_html(html)


def _extract_docx(data: bytes) -> str:
    document = Document(BytesIO(data))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs)


def _extract_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page.strip() for page in pages if page.strip())


def _extract_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)
