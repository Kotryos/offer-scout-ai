---
name: kotlin-spring-logging
description: Apply concise Kotlin and Spring Boot logging practices. Use when adding, reviewing, or cleaning logs in Kotlin Spring services, controllers, tools, configuration, exception handlers, or WebClient integrations.
---

# Kotlin Spring Logging

Use this skill to keep logs useful, quiet, and safe.

## Rules

- Declare loggers in a companion object:

```kotlin
companion object {
    private val log = LoggerFactory.getLogger(MyClass::class.java)
}
```

- Use parameterized messages:

```kotlin
log.info("Evaluating offer {}", offerId)
```

- Do not use string interpolation in log messages:

```kotlin
log.info("Evaluating offer $offerId")
```

- Log expected recoverable upstream failures at `warn`.
- Log unexpected app failures at the boundary that handles them.
- Pass the exception as the last argument when stack traces are useful.
- Do not log API keys, full prompts, full resumes, or full offer text.
- Prefer a few high-signal logs over many lifecycle logs.
- Keep logging concise.

## Scout-Agent Notes

- `GlobalExceptionHandler` owns logs for uncaught request-level failures.
- `webintegration` may log expected Tavily/Jina failures before returning fallback tool text.
- Avoid duplicate logging: either log where the exception is handled, or let it bubble.
