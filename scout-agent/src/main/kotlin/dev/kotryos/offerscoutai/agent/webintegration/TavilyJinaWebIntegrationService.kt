package dev.kotryos.offerscoutai.agent.webintegration

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty
import org.slf4j.LoggerFactory
import org.springframework.core.codec.DecodingException
import reactor.core.publisher.Mono
import org.springframework.stereotype.Service
import org.springframework.web.reactive.function.client.WebClientException
import org.springframework.web.reactive.function.client.bodyToMono
import java.util.concurrent.TimeoutException

@Service
internal class TavilyJinaWebIntegrationService(
    private val tavilySearchClient: TavilySearchClient,
    private val jinaReaderClient: JinaReaderClient,
    private val props: WebIntegrationProperties
) : WebIntegrationService {

    override fun searchWeb(query: String): Mono<String> {
        log.info("Searching web")
        return tavilySearchClient.post()
            .uri("")
            .bodyValue(TavilySearchRequest(query = query, maxResults = props.maxSearchResults))
            .retrieve()
            .bodyToMono<TavilySearchResponse>()
            .timeout(props.timeout)
            .map { response -> formatSearchResults(query, response.results) }
            .onErrorResume { ex: Throwable ->
                if (isRecoverableUpstreamFailure(ex)) {
                    log.warn("Web search failed", ex)
                    Mono.just(searchFailureMessage(query))
                } else {
                    Mono.error(ex)
                }
            }
            .switchIfEmpty(Mono.just(searchFailureMessage(query)))
    }

    override fun fetchPage(url: String): Mono<String> {
        log.info("Fetching page content")
        return jinaReaderClient
            .get()
            .uri("/$url")
            .retrieve()
            .bodyToMono<String>()
            .timeout(props.timeout)
            .map { content -> content.trim() }
            .filter { content -> content.isNotEmpty() }
            .map { content ->
                content.take(props.maxPageContentLength)
                    .also { log.info("Fetched page content with {} chars", it.length) }
            }
            .onErrorResume { ex: Throwable ->
                if (isRecoverableUpstreamFailure(ex)) {
                    log.warn("Page fetch failed", ex)
                    Mono.just(pageFetchFailureMessage(url))
                } else {
                    Mono.error(ex)
                }
            }
            .switchIfEmpty(Mono.just(pageFetchFailureMessage(url)))
    }

    private fun isRecoverableUpstreamFailure(ex: Throwable): Boolean =
        ex is WebClientException ||
            ex is TimeoutException ||
            ex is DecodingException

    private fun formatSearchResults(query: String, results: List<TavilyResult>): String {
        log.info("Found {} web results, using {}", results.size, minOf(results.size, props.maxSearchResults))
        if (results.isEmpty()) return "No results found for: $query"

        return results
            .take(props.maxSearchResults)
            .joinToString("\n\n") { r ->
                "**${r.title}** (${r.url})\n${r.content.take(props.maxSearchResultContentLength)}"
            }
    }

    private fun searchFailureMessage(query: String): String =
        "Web search failed or timed out for: $query. Continue the evaluation using the offer text and any other available context."

    private fun pageFetchFailureMessage(url: String): String =
        "Could not extract content from URL $url. Proceed using only the information available from the URL slug and web search."

    @JsonIgnoreProperties(ignoreUnknown = true)
    data class TavilySearchRequest(
        val query: String,
        @JsonProperty("max_results")
        val maxResults: Int,
    )

    @JsonIgnoreProperties(ignoreUnknown = true)
    data class TavilySearchResponse(
        val results: List<TavilyResult> = emptyList(),
    )

    @JsonIgnoreProperties(ignoreUnknown = true)
    data class TavilyResult(
        val title: String = "",
        val url: String = "",
        val content: String = "",
    )

    companion object {
        private val log = LoggerFactory.getLogger(TavilyJinaWebIntegrationService::class.java)
    }
}
