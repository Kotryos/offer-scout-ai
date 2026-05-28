package com.github.constantinet.offerscoutai.agent.tool

import com.github.constantinet.offerscoutai.agent.webintegration.WebIntegrationService
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.mockito.Mockito.mock
import org.mockito.Mockito.`when`
import reactor.core.publisher.Mono

class WebToolTest {

    private val webIntegrationService = mock(WebIntegrationService::class.java)
    private val webTool = WebTool(webIntegrationService)

    @Test
    fun `searchWeb blocks and returns integration result`() {
        `when`(webIntegrationService.searchWeb(TEST_COMPANY_QUERY))
            .thenReturn(Mono.just("search result"))

        assertThat(webTool.searchWeb(TEST_COMPANY_QUERY)).isEqualTo("search result")
    }

    @Test
    fun `searchWeb returns fallback when integration returns empty`() {
        `when`(webIntegrationService.searchWeb(TEST_COMPANY_QUERY))
            .thenReturn(Mono.empty())

        assertThat(webTool.searchWeb(TEST_COMPANY_QUERY))
            .contains("Web search failed or timed out")
    }

    @Test
    fun `fetchPage blocks and returns integration result`() {
        `when`(webIntegrationService.fetchPage("https://example.com/job"))
            .thenReturn(Mono.just("page content"))

        assertThat(webTool.fetchPage("https://example.com/job")).isEqualTo("page content")
    }

    @Test
    fun `fetchPage returns fallback when integration returns empty`() {
        `when`(webIntegrationService.fetchPage("https://example.com/job"))
            .thenReturn(Mono.empty())

        assertThat(webTool.fetchPage("https://example.com/job"))
            .contains("Could not extract content")
    }

    companion object {
        private const val TEST_COMPANY_QUERY = "ExampleCo news"
    }
}
