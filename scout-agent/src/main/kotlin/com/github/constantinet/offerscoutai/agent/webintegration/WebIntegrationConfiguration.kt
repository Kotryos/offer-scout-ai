package com.github.constantinet.offerscoutai.agent.webintegration

import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.web.reactive.function.client.WebClient
import java.time.Duration

@Configuration
@EnableConfigurationProperties(TavilyProperties::class, JinaProperties::class, WebIntegrationProperties::class)
class WebIntegrationConfiguration {

    @Bean
    fun tavilySearchClient(builder: WebClient.Builder, tavily: TavilyProperties): TavilySearchClient =
        TavilySearchClient(
            builder
                .baseUrl(tavily.searchBaseUrl)
                .defaultHeader(CONTENT_TYPE, APPLICATION_JSON)
                .defaultHeader(AUTHORIZATION, "Bearer ${tavily.apiKey}")
                .build()
        )

    @Bean
    fun jinaReaderClient(builder: WebClient.Builder, jina: JinaProperties): JinaReaderClient =
        JinaReaderClient(
            builder
                .baseUrl(jina.readerBaseUrl)
                .defaultHeader(ACCEPT, TEXT_PLAIN)
                .defaultHeader(X_RETURN_FORMAT, MARKDOWN)
                .let { if (jina.apiKey.isNotBlank()) it.defaultHeader(AUTHORIZATION, "Bearer ${jina.apiKey}") else it }
                .build()
        )

    companion object {
        private const val CONTENT_TYPE = "Content-Type"
        private const val APPLICATION_JSON = "application/json"
        private const val ACCEPT = "Accept"
        private const val TEXT_PLAIN = "text/plain"
        private const val X_RETURN_FORMAT = "X-Return-Format"
        private const val MARKDOWN = "markdown"
        private const val AUTHORIZATION = "Authorization"
    }
}

@ConfigurationProperties(prefix = "tavily")
data class TavilyProperties(
    val apiKey: String,
    val searchBaseUrl: String
)

@ConfigurationProperties(prefix = "jina")
data class JinaProperties(
    val apiKey: String = "",
    val readerBaseUrl: String
)

@ConfigurationProperties(prefix = "web-integration-commons")
data class WebIntegrationProperties(
    val timeout: Duration,
    val maxContentLength: Int
)

class TavilySearchClient(val client: WebClient) : WebClient by client
class JinaReaderClient(val client: WebClient) : WebClient by client