# Scout Coordinator

Python/FastAPI service that receives Resend email webhooks, asks `scout-agent`
to evaluate the offer, and replies through Gmail SMTP.

## Requirements

- Python 3.12
- Resend API key
- Resend webhook signing secret
- Gmail app password
- running `scout-agent`

## Local Setup For Direct Python Run

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
```

Git Bash on Windows:

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements-dev.txt
pip install -e .
```

Unix/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

Create a local `.env` file from the root `.env.example` values.

## Run Locally

Run `scout-agent` on port `8080`, then run coordinator on port `8081`:

```bash
uvicorn scout_coordinator.main:app --reload --port 8081
```

With Docker Compose, run from the repository root:

```bash
docker compose up --build scout-agent scout-coordinator
```

Docker Compose uses the root `.env` file.

## Local Webhook Testing

### Option 1: webhook.site Replay

Use this when you do not want to expose localhost.

1. Set the Resend webhook URL to webhook.site.
2. Send or forward an email to the Resend receiving address.
3. Copy the webhook.site request as `curl`.
4. Change the URL to `http://localhost:8081/webhooks/resend`.
5. Remove `content-length` and `host` headers.
6. Keep the original `svix-*` headers and exact JSON body.

Example shape:

```bash
curl -i -X POST http://localhost:8081/webhooks/resend \
  -H "Content-Type: application/json" \
  -H "svix-id: msg_..." \
  -H "svix-timestamp: ..." \
  -H "svix-signature: v1,..." \
  -d '{"type":"email.received","data":{"email_id":"...","from":"...","to":["..."],"attachments":[]}}'
```

This path works with `TASK_BACKEND=local`; no ngrok or GCP resources are needed.

### Option 2: ngrok

Use this for a full local end-to-end flow from Resend to your machine.

Expose coordinator with ngrok:

```bash
ngrok http 8081
```

Set the Resend webhook URL to:

```text
https://your-ngrok-url.ngrok-free.app/webhooks/resend
```

Keep ngrok running while testing. If ngrok restarts, update the Resend webhook
URL because the free URL usually changes.

## How It Works

- `/webhooks/resend` verifies the Svix signature from Resend.
- Valid `email.received` events are scheduled through the configured task backend.
- The processor fetches the full email from Resend.
- Supported attachments are downloaded and converted to text.
- Combined email text is sent to `scout-agent`.
- The result is emailed back through Gmail SMTP.

## Task Backends

Local mode is the default:

```text
TASK_BACKEND=local
```

In local mode, `/webhooks/resend` starts a background coroutine in the same
process. This is good for webhook.site replay and ngrok testing.

Cloud Tasks mode is for GCP later:

```text
TASK_BACKEND=cloud_tasks
CLOUD_TASKS_PROJECT=your-gcp-project
CLOUD_TASKS_LOCATION=europe-west1
CLOUD_TASKS_QUEUE=scout-email-processing
CLOUD_TASKS_TARGET_URL=https://your-cloud-run-url/tasks/process-email
CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL=scout-tasks@your-gcp-project.iam.gserviceaccount.com
```

In Cloud Tasks mode, `/webhooks/resend` creates an HTTP task, and Cloud Tasks
calls `/tasks/process-email`. The task endpoint verifies Google OIDC.

In local mode, `/tasks/process-email` returns `404`. Local processing only starts
from `/webhooks/resend`.

## Future GCP Deployment

- Deploy as a public Cloud Run service so Resend can call `/webhooks/resend`.
- Keep webhook security at the application boundary with Svix signatures.
- Use `TASK_BACKEND=cloud_tasks` in production.
- Use Cloud Tasks to call `/tasks/process-email` with Google OIDC.
- Store Resend, Gmail, and profile secrets in Secret Manager.
- Call private `scout-agent` with `SCOUT_AGENT_AUTH_MODE=cloud_run_oidc`.

## Tests

```bash
python -m pytest --cov=scout_coordinator --cov-report=term-missing
```
