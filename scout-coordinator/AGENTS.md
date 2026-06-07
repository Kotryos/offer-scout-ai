# AGENTS.md

Short instructions for AI agents working in `scout-coordinator`.

## How To Reply

- Be concise. Prefer short answers and compact bullet lists.
- Explain only what is needed for the current task.
- If the user asks for more detail, expand then.

## Project Basics

- Python / FastAPI service.
- Receives Resend webhooks, fetches the full email, extracts attachment text, calls `scout-agent`, and replies by Gmail SMTP.
- Configuration comes from environment variables through Pydantic `Settings`.
- Docker Compose uses the root `.env`; direct local Python runs may use `scout-coordinator/.env`.

## Important Rules

- Keep `/webhooks/resend` protected by Svix signature verification.
- Keep `/tasks/process-email` disabled in local mode and OIDC-protected in Cloud Tasks mode.
- Do not add a public `/health` endpoint unless deployment requirements change.
- Keep I/O async with `httpx`, `aiosmtplib`, and async Google clients.
- Offload blocking parsing or auth helpers with `anyio.to_thread`.
- Convert attachments to text before sending them to `scout-agent`; do not send raw bytes.
- Do not commit secrets, `.env` files, generated fixtures, virtualenvs, caches, or coverage output.

## Verify Changes

Run from this directory:

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=scout_coordinator --cov-report=term-missing
.\.venv\Scripts\python.exe -m compileall src tests
```

Unix:

```bash
python -m pytest --cov=scout_coordinator --cov-report=term-missing
python -m compileall src tests
```

Build the Docker image from the repository root:

```bash
docker compose build scout-coordinator
```
