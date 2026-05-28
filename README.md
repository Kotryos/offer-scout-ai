# Offer Scout AI

Offer Scout AI is a personal AI service for evaluating job offers against a candidate profile.

## Projects

- `scout-agent`: Kotlin/Spring Boot service that evaluates job offers with Spring AI, Groq-compatible chat, Tavily search, and Jina page fetching.
- `scout-coordinator`: placeholder for a future coordinator service.

## Run

Copy the environment template:

```bash
cp .env.example .env
```

Start the agent:

```bash
docker compose up --build scout-agent
```

Example `curl` requests are in `scout-agent/README.md`.

## Development

See `scout-agent/README.md` for service-specific commands and architecture notes.
