# Offer Scout AI

Offer Scout AI is a personal AI service for evaluating job offers against a candidate profile.

## Projects

- `scout-agent`: Kotlin/Spring Boot service that evaluates job offers with Spring AI, Groq-compatible chat, Tavily search, and Jina page fetching.
- `scout-coordinator`: Python/FastAPI service that receives Resend email webhooks, extracts email and attachment text, calls `scout-agent`, and replies through Gmail SMTP.

## Local Run

Copy the environment template:

```bash
cp .env.example .env
```

Start the services:

```bash
docker compose up --build scout-agent scout-coordinator
```

Docker Compose uses only the root `.env` file. Module-local `.env` files and
`application-local.yml` are for direct local runs outside Docker Compose.

## Local Testing

- Direct agent `curl` examples are in `scout-agent/README.md`.
- Email/webhook tests are in `scout-coordinator/README.md`.
- Coordinator supports two local webhook paths:
  - webhook.site capture and replay to `localhost`.
  - ngrok forwarding from Resend to local Docker Compose.

## Future GCP Deployment

Planned production shape:

- `scout-coordinator`: public Cloud Run service for Resend webhooks, protected by Svix signature verification.
- `scout-agent`: private Cloud Run service, invoked only by coordinator using Google ID tokens.
- Cloud Tasks: async email processing after webhook acceptance.
- Secret Manager: API keys and SMTP credentials.
- Artifact Registry and GitHub Actions: image build and deployment pipeline.

## Development

See each project README for service-specific commands and architecture notes.
