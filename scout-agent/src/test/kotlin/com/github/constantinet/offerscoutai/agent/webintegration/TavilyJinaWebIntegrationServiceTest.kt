package com.github.constantinet.offerscoutai.agent.webintegration

import org.junit.jupiter.api.Test
import org.assertj.core.api.Assertions.assertThat
import org.springframework.http.HttpStatus
import org.springframework.web.reactive.function.client.ClientRequest
import org.springframework.web.reactive.function.client.ClientResponse
import org.springframework.web.reactive.function.client.ExchangeFunction
import org.springframework.web.reactive.function.client.WebClient
import reactor.core.publisher.Mono
import reactor.test.StepVerifier
import java.time.Duration

class TavilyJinaWebIntegrationServiceTest {

    @Test
    fun `searchWeb formats tavily results`() {
        val service = service(
            tavilyResponse = jsonResponse(
                """
                {
                  "results": [
                    {
                      "title": "ExampleCo News",
                      "url": "https://example.com/news",
                      "content": "Company update"
                    }
                  ]
                }
                """.trimIndent()
            )
        )

        StepVerifier.create(service.searchWeb(TEST_COMPANY_QUERY))
            .expectNext("**ExampleCo News** (https://example.com/news)\nCompany update")
            .verifyComplete()
    }

    @Test
    fun `searchWeb returns fallback for upstream error`() {
        val service = service(tavilyResponse = ClientResponse.create(HttpStatus.BAD_GATEWAY).build())

        StepVerifier.create(service.searchWeb(TEST_COMPANY_QUERY))
            .expectNextMatches { it.contains("Web search failed or timed out") }
            .verifyComplete()
    }

    @Test
    fun `searchWeb returns fallback for timeout`() {
        val service = service(tavilyResponse = Mono.never(), timeout = Duration.ofMillis(10))

        StepVerifier.create(service.searchWeb(TEST_COMPANY_QUERY))
            .expectNextMatches { it.contains("Web search failed or timed out") }
            .verifyComplete()
    }

    @Test
    fun `searchWeb returns fallback for malformed response`() {
        val service = service(tavilyResponse = jsonResponse("""{"results": "wrong-shape"}"""))

        StepVerifier.create(service.searchWeb(TEST_COMPANY_QUERY))
            .expectNextMatches { it.contains("Web search failed or timed out") }
            .verifyComplete()
    }

    @Test
    fun `searchWeb returns no results message for empty results`() {
        val service = service(tavilyResponse = jsonResponse("""{"results": []}"""))

        StepVerifier.create(service.searchWeb(TEST_COMPANY_QUERY))
            .expectNext("No results found for: $TEST_COMPANY_QUERY")
            .verifyComplete()
    }

    @Test
    fun `searchWeb truncates long formatted result`() {
        val service = service(
            tavilyResponse = jsonResponse(
                """
                {
                  "results": [
                    {
                      "title": "ExampleCo News",
                      "url": "https://example.com/news",
                      "content": "Long company update"
                    }
                  ]
                }
                """.trimIndent()
            ),
            maxContentLength = 20,
        )

        StepVerifier.create(service.searchWeb(TEST_COMPANY_QUERY))
            .assertNext { result ->
                assertThat(result).hasSize(20)
                assertThat(result).startsWith("**ExampleCo News**")
            }
            .verifyComplete()
    }

    @Test
    fun `fetchPage trims and truncates content`() {
        val service = service(jinaResponse = textResponse("  abcdef  "), maxContentLength = 4)

        StepVerifier.create(service.fetchPage("https://example.com/job"))
            .expectNext("abcd")
            .verifyComplete()
    }

    @Test
    fun `fetchPage returns fallback for blank content`() {
        val service = service(jinaResponse = textResponse("   "))

        StepVerifier.create(service.fetchPage("https://example.com/job"))
            .expectNextMatches { it.contains("Could not extract content") }
            .verifyComplete()
    }

    @Test
    fun `fetchPage returns fallback for upstream error`() {
        val service = service(jinaResponse = ClientResponse.create(HttpStatus.BAD_GATEWAY).build())

        StepVerifier.create(service.fetchPage("https://example.com/job"))
            .expectNextMatches { it.contains("Could not extract content") }
            .verifyComplete()
    }

    @Test
    fun `fetchPage returns fallback for timeout`() {
        val service = service(jinaResponse = Mono.never(), timeout = Duration.ofMillis(10))

        StepVerifier.create(service.fetchPage("https://example.com/job"))
            .expectNextMatches { it.contains("Could not extract content") }
            .verifyComplete()
    }

    private fun service(
        tavilyResponse: Mono<ClientResponse> = Mono.just(jsonResponse("""{"results": []}""")),
        jinaResponse: Mono<ClientResponse> = Mono.just(textResponse("page content")),
        maxContentLength: Int = 4000,
        timeout: Duration = Duration.ofSeconds(1),
    ): TavilyJinaWebIntegrationService =
        TavilyJinaWebIntegrationService(
            tavilySearchClient = TavilySearchClient(clientReturning(tavilyResponse)),
            jinaReaderClient = JinaReaderClient(clientReturning(jinaResponse)),
            props = WebIntegrationProperties(
                timeout = timeout,
                maxContentLength = maxContentLength,
            ),
        )

    private fun service(
        tavilyResponse: ClientResponse = jsonResponse("""{"results": []}"""),
        jinaResponse: ClientResponse = textResponse("page content"),
        maxContentLength: Int = 4000,
        timeout: Duration = Duration.ofSeconds(1),
    ): TavilyJinaWebIntegrationService =
        service(
            tavilyResponse = Mono.just(tavilyResponse),
            jinaResponse = Mono.just(jinaResponse),
            maxContentLength = maxContentLength,
            timeout = timeout,
        )

    private fun clientReturning(response: Mono<ClientResponse>): WebClient =
        WebClient.builder()
            .exchangeFunction(ExchangeFunction { _: ClientRequest -> response })
            .build()

    companion object {
        private const val TEST_COMPANY_QUERY = "ExampleCo news"

        private fun jsonResponse(body: String): ClientResponse =
            ClientResponse.create(HttpStatus.OK)
                .header("Content-Type", "application/json")
                .body(body)
                .build()

        private fun textResponse(body: String): ClientResponse =
            ClientResponse.create(HttpStatus.OK)
                .header("Content-Type", "text/plain")
                .body(body)
                .build()
    }
}
