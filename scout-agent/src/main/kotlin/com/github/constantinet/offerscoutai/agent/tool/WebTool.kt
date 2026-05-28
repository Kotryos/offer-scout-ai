package com.github.constantinet.offerscoutai.agent.tool

import com.github.constantinet.offerscoutai.agent.webintegration.WebIntegrationService
import org.slf4j.LoggerFactory
import org.springframework.ai.tool.annotation.Tool
import org.springframework.stereotype.Component

@Component
class WebTool(
    private val webIntegrationService: WebIntegrationService,
) {

    @Tool(description = "Search the web for up-to-date information about a company, salary benchmarks, job market trends, or recent news. Use this to research any company mentioned in a job offer. Budget: use at most 2 times per evaluation.")
    fun searchWeb(query: String): String {
        log.debug("Invoking searchWeb tool")
        return webIntegrationService.searchWeb(query).block()
            ?: "Web search failed or timed out for: $query. Continue the evaluation using the offer text and any other available context."
    }

    @Tool(description = "Fetch and extract the full text content of a web page by URL. Use this when the job offer is provided as a URL to retrieve the actual job description. Budget: use at most 1 time per evaluation.")
    fun fetchPage(url: String): String {
        log.debug("Invoking fetchPage tool")
        return webIntegrationService.fetchPage(url).block()
            ?: "Could not extract content from URL. Proceed using only the information available from the URL slug and web search."
    }

    companion object {
        private val log = LoggerFactory.getLogger(WebTool::class.java)
    }
}