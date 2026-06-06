package com.github.constantinet.offerscoutai.agent.tool

import com.github.constantinet.offerscoutai.agent.webintegration.WebIntegrationService
import org.slf4j.LoggerFactory
import org.springframework.ai.tool.annotation.Tool
import org.springframework.ai.tool.annotation.ToolParam
import org.springframework.stereotype.Component

@Component
class WebTool(
    private val webIntegrationService: WebIntegrationService,
) {

    @Tool(
        name = "search_web",
        description = "Search the web for up-to-date information about a company, reputation, recent news, funding, layoffs, reviews, or market salary benchmarks. Do not use this to infer the offered salary and do not use this to fetch a specific page URL. Budget: use at most 2 times per evaluation."
    )
    fun searchWeb(
        @ToolParam(
            description = "A concise web search query, for example 'ExampleSoft company news funding layoffs reviews' or 'Senior Kotlin Spring developer salary Poland B2B PLN monthly'. This must not be a URL.",
            required = true,
        )
        query: String,
    ): String {
        log.debug("Invoking searchWeb tool")
        return webIntegrationService.searchWeb(query).block()
            ?: "Web search failed or timed out for: $query. Continue the evaluation using the offer text and any other available context."
    }

    @Tool(
        name = "fetch_page",
        description = "Fetch and extract the full text content of a specific job offer page. Use this only when the user's job offer text contains an explicit URL. Never invent, guess, or construct URLs. For plain text job offers, do not use this tool. Budget: use at most 1 time per evaluation."
    )
    fun fetchPage(
        @ToolParam(
            description = "The exact URL copied from the user's job offer text. It must already appear in the offer. Do not pass guessed company or careers URLs.",
            required = true,
        )
        url: String,
    ): String {
        log.debug("Invoking fetchPage tool")
        return webIntegrationService.fetchPage(url).block()
            ?: "Could not extract content from URL $url. Proceed using only the information available from the URL slug and web search."
    }

    companion object {
        private val log = LoggerFactory.getLogger(WebTool::class.java)
    }
}
