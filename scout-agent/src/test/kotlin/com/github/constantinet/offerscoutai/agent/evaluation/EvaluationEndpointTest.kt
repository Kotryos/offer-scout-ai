package com.github.constantinet.offerscoutai.agent.evaluation

import com.github.constantinet.offerscoutai.agent.common.CorrelationIdFilter
import com.github.constantinet.offerscoutai.agent.common.GlobalExceptionHandler
import org.junit.jupiter.api.Test
import org.mockito.Mockito.mock
import org.mockito.Mockito.`when`
import org.springframework.ai.retry.NonTransientAiException
import org.springframework.ai.retry.TransientAiException
import org.springframework.http.HttpHeaders
import org.springframework.http.HttpStatus
import org.springframework.test.web.reactive.server.WebTestClient
import org.springframework.web.reactive.function.client.WebClientResponseException
import reactor.core.publisher.Mono

class EvaluationEndpointTest {

    private val evaluationService = mock(EvaluationService::class.java)
    private val client: WebTestClient

    init {
        val serverSpec = WebTestClient
            .bindToController(EvaluationController(evaluationService))
            .controllerAdvice(GlobalExceptionHandler())

        serverSpec.webFilter<WebTestClient.ControllerSpec>(CorrelationIdFilter())
        client = serverSpec.build()
    }

    @Test
    fun `returns evaluation json and echoes provided correlation id`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(Mono.just("Worth pursuing."))

        client.post()
            .uri("/offer/evaluation")
            .header(CorrelationIdFilter.HEADER, CORRELATION_ID)
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isOk
            .expectHeader().valueEquals(CorrelationIdFilter.HEADER, CORRELATION_ID)
            .expectBody()
            .jsonPath("$.evaluation").isEqualTo("Worth pursuing.")
    }

    @Test
    fun `generates correlation id when request header is missing`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(Mono.just("Worth pursuing."))

        client.post()
            .uri("/offer/evaluation")
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isOk
            .expectHeader().exists(CorrelationIdFilter.HEADER)
    }

    @Test
    fun `maps transient ai errors through global exception handler`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(Mono.error(TransientAiException("temporary failure")))

        client.post()
            .uri("/offer/evaluation")
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo(GlobalExceptionHandler.CODE_AI_UNAVAILABLE)
            .jsonPath("$.message").isEqualTo(GlobalExceptionHandler.MSG_AI_UNAVAILABLE)
    }

    @Test
    fun `maps quota errors through global exception handler`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(Mono.error(NonTransientAiException("429 quota exceeded")))

        client.post()
            .uri("/offer/evaluation")
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isEqualTo(429)
            .expectBody()
            .jsonPath("$.error").isEqualTo(GlobalExceptionHandler.CODE_QUOTA_EXCEEDED)
    }

    @Test
    fun `maps invalid api key errors through global exception handler`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(Mono.error(NonTransientAiException("401 unauthorized")))

        client.post()
            .uri("/offer/evaluation")
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isEqualTo(401)
            .expectBody()
            .jsonPath("$.error").isEqualTo(GlobalExceptionHandler.CODE_INVALID_API_KEY)
    }

    @Test
    fun `maps invalid ai tool call errors through global exception handler`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(Mono.error(NonTransientAiException("HTTP 400 code=tool_use_failed")))

        client.post()
            .uri("/offer/evaluation")
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isEqualTo(502)
            .expectBody()
            .jsonPath("$.error").isEqualTo(GlobalExceptionHandler.CODE_AI_TOOL_CALL_ERROR)
            .jsonPath("$.message").isEqualTo(GlobalExceptionHandler.MSG_AI_TOOL_CALL_ERROR)
    }

    @Test
    fun `maps generic non transient ai errors through global exception handler`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(Mono.error(NonTransientAiException("model failed")))

        client.post()
            .uri("/offer/evaluation")
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isEqualTo(502)
            .expectBody()
            .jsonPath("$.error").isEqualTo(GlobalExceptionHandler.CODE_AI_ERROR)
    }

    @Test
    fun `maps web client response errors through global exception handler`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(
                Mono.error(
                    WebClientResponseException.create(
                        HttpStatus.BAD_GATEWAY.value(),
                        "Bad Gateway",
                        HttpHeaders.EMPTY,
                        ByteArray(0),
                        null,
                    )
                )
            )

        client.post()
            .uri("/offer/evaluation")
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isEqualTo(502)
            .expectBody()
            .jsonPath("$.error").isEqualTo(GlobalExceptionHandler.CODE_UPSTREAM_ERROR)
    }

    @Test
    fun `maps generic errors through global exception handler`() {
        `when`(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .thenReturn(Mono.error(IllegalStateException("unexpected")))

        client.post()
            .uri("/offer/evaluation")
            .bodyValue(requestBody())
            .exchange()
            .expectStatus().isEqualTo(500)
            .expectBody()
            .jsonPath("$.error").isEqualTo(GlobalExceptionHandler.CODE_INTERNAL_ERROR)
    }

    private fun requestBody(): Map<String, String> =
        mapOf(
            "offerText" to OFFER_TEXT,
            "profileContext" to PROFILE_CONTEXT,
        )

    companion object {
        private const val CORRELATION_ID = "test-correlation-id"
        private const val OFFER_TEXT = "Java job"
        private const val PROFILE_CONTEXT = "Senior Java developer"
    }
}
