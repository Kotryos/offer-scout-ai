package com.github.constantinet.offerscoutai.agent

import com.github.constantinet.offerscoutai.agent.evaluation.EvaluationService
import org.junit.jupiter.api.Test
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.bean.override.mockito.MockitoBean

@SpringBootTest(
    webEnvironment = SpringBootTest.WebEnvironment.NONE,
    properties = [
        "spring.ai.model.embedding=none",
        "spring.ai.openai.api-key=test",
        "spring.ai.openai.base-url=https://example.com/openai",
        "spring.ai.openai.chat.options.model=test-model",
        "tavily.api-key=test",
        "tavily.search-base-url=https://example.com/tavily",
        "jina.api-key=",
        "jina.reader-base-url=https://example.com/jina",
        "web-integration-commons.max-page-content-length=6000",
        "web-integration-commons.max-search-results=3",
        "web-integration-commons.max-search-result-content-length=500",
        "web-integration-commons.timeout=15s",
    ],
)
class ScoutAgentApplicationContextTest {

    @MockitoBean
    lateinit var evaluationService: EvaluationService

    @Test
    fun `context loads`() {
    }
}
