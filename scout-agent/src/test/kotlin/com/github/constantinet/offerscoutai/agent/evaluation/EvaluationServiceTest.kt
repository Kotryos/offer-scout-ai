package com.github.constantinet.offerscoutai.agent.evaluation

import com.github.constantinet.offerscoutai.agent.tool.WebTool
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.mockito.ArgumentMatchers.anyString
import org.mockito.Mockito.mock
import org.mockito.Mockito.never
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import org.springframework.ai.chat.client.ChatClient
import reactor.test.StepVerifier

class EvaluationServiceTest {

    private val chatClient = mock(ChatClient::class.java)
    private val requestSpec = mock(ChatClient.ChatClientRequestSpec::class.java)
    private val callResponseSpec = mock(ChatClient.CallResponseSpec::class.java)
    private val webTool = mock(WebTool::class.java)
    private val evaluationService = EvaluationService(chatClient, webTool)

    @Test
    fun `evaluate builds prompt and returns model content`() {
        givenChatClientReturns("evaluation result")

        StepVerifier.create(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .expectNext("evaluation result")
            .verifyComplete()

        verify(chatClient).prompt()
        verify(requestSpec).system(anyString())
        verify(requestSpec).user(
            """
            Candidate Profile:
            $PROFILE_CONTEXT

            Job Offer to Evaluate:
            $OFFER_TEXT
            """.trimIndent()
        )
        verify(requestSpec).tools(webTool)
        verify(requestSpec).call()
        verify(callResponseSpec).content()
    }

    @Test
    fun `evaluate converts null model content to empty string`() {
        givenChatClientReturns(null)

        StepVerifier.create(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .expectNext("")
            .verifyComplete()
    }

    @Test
    fun `evaluate defers blocking chat call until subscription`() {
        givenChatClientReturns("evaluation result")

        val result = evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT)

        verify(chatClient, never()).prompt()

        StepVerifier.create(result)
            .expectNext("evaluation result")
            .verifyComplete()
    }

    @Test
    fun `evaluate runs chat call away from caller thread`() {
        val callerThread = Thread.currentThread().name
        var chatThread: String? = null

        `when`(chatClient.prompt()).thenAnswer {
            chatThread = Thread.currentThread().name
            requestSpec
        }
        `when`(requestSpec.system(anyString())).thenReturn(requestSpec)
        `when`(requestSpec.user(anyString())).thenReturn(requestSpec)
        `when`(requestSpec.tools(webTool)).thenReturn(requestSpec)
        `when`(requestSpec.call()).thenReturn(callResponseSpec)
        `when`(callResponseSpec.content()).thenReturn("evaluation result")

        StepVerifier.create(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .expectNext("evaluation result")
            .verifyComplete()

        assertThat(chatThread).isNotNull()
        assertThat(chatThread).isNotEqualTo(callerThread)
        assertThat(chatThread).contains("boundedElastic")
    }

    private fun givenChatClientReturns(content: String?) {
        `when`(chatClient.prompt()).thenReturn(requestSpec)
        `when`(requestSpec.system(anyString())).thenReturn(requestSpec)
        `when`(requestSpec.user(anyString())).thenReturn(requestSpec)
        `when`(requestSpec.tools(webTool)).thenReturn(requestSpec)
        `when`(requestSpec.call()).thenReturn(callResponseSpec)
        `when`(callResponseSpec.content()).thenReturn(content)
    }

    companion object {
        private const val OFFER_TEXT = "Kotlin Spring job"
        private const val PROFILE_CONTEXT = "Senior Kotlin developer"
    }
}
