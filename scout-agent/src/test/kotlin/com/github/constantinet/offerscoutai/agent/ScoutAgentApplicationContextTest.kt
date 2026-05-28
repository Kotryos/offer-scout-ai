package com.github.constantinet.offerscoutai.agent

import org.junit.jupiter.api.Test
import org.springframework.boot.test.context.SpringBootTest

@SpringBootTest(
    webEnvironment = SpringBootTest.WebEnvironment.NONE,
    properties = [
        "GROQ_API_KEY=test",
        "TAVILY_API_KEY=test",
        "jina.reader-base-url=https://example.com",
        "tavily.search-base-url=https://example.com",
    ],
)
class ScoutAgentApplicationContextTest {

    @Test
    fun `context loads`() {
    }
}
