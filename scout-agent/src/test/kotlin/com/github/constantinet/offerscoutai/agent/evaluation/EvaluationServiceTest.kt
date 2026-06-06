package com.github.constantinet.offerscoutai.agent.evaluation

import com.github.constantinet.offerscoutai.agent.tool.WebTool
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.mockito.ArgumentMatchers.anyString
import org.mockito.Mockito.mock
import org.mockito.Mockito.never
import org.mockito.Mockito.times
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import org.springframework.ai.chat.client.ChatClient
import org.springframework.ai.retry.NonTransientAiException
import org.springframework.core.io.ByteArrayResource
import reactor.test.StepVerifier

class EvaluationServiceTest {

    private val chatClient = mock(ChatClient::class.java)
    private val requestSpec = mock(ChatClient.ChatClientRequestSpec::class.java)
    private val callResponseSpec = mock(ChatClient.CallResponseSpec::class.java)
    private val webTool = mock(WebTool::class.java)
    private val evaluationService = EvaluationService(
        chatClient = chatClient,
        webTool = webTool,
        systemPromptResource = ByteArrayResource(SYSTEM_PROMPT.toByteArray()),
    )

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

    @Test
    fun `evaluate retries without tools when model produces invalid tool call`() {
        `when`(chatClient.prompt()).thenReturn(requestSpec)
        `when`(requestSpec.system(anyString())).thenReturn(requestSpec)
        `when`(requestSpec.user(anyString())).thenReturn(requestSpec)
        `when`(requestSpec.tools(webTool)).thenReturn(requestSpec)
        `when`(requestSpec.call()).thenReturn(callResponseSpec)
        `when`(callResponseSpec.content())
            .thenThrow(NonTransientAiException("HTTP 400 code=tool_use_failed"))
            .thenReturn("fallback evaluation")

        StepVerifier.create(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .expectNext("fallback evaluation")
            .verifyComplete()

        verify(requestSpec, times(2)).system(anyString())
        verify(requestSpec, times(2)).user(anyString())
        verify(requestSpec).tools(webTool)
        verify(requestSpec, times(2)).call()
        verify(callResponseSpec, times(2)).content()
    }

    @Test
    fun `evaluate keeps non tool ai errors for global exception handling`() {
        `when`(chatClient.prompt()).thenReturn(requestSpec)
        `when`(requestSpec.system(anyString())).thenReturn(requestSpec)
        `when`(requestSpec.user(anyString())).thenReturn(requestSpec)
        `when`(requestSpec.tools(webTool)).thenReturn(requestSpec)
        `when`(requestSpec.call()).thenReturn(callResponseSpec)
        `when`(callResponseSpec.content())
            .thenThrow(NonTransientAiException("HTTP 400 model failed"))

        StepVerifier.create(evaluationService.evaluate(OFFER_TEXT, PROFILE_CONTEXT))
            .expectError(NonTransientAiException::class.java)
            .verify()

        verify(requestSpec).tools(webTool)
        verify(requestSpec).call()
        verify(callResponseSpec).content()
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
        private const val SYSTEM_PROMPT = "Test system prompt"
        private const val OFFER_TEXT = "Java job"
        private const val PROFILE_CONTEXT = "Senior Java developer"
    }
}
