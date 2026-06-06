package com.github.constantinet.offerscoutai.agent.evaluation

import com.github.constantinet.offerscoutai.agent.tool.WebTool
import org.slf4j.LoggerFactory
import org.springframework.ai.chat.client.ChatClient
import org.springframework.ai.retry.NonTransientAiException
import org.springframework.beans.factory.annotation.Value
import org.springframework.core.io.Resource
import org.springframework.stereotype.Service
import reactor.core.publisher.Mono
import reactor.core.scheduler.Schedulers

@Service
class EvaluationService(
    private val chatClient: ChatClient,
    private val webTool: WebTool,
    @Value("classpath:prompts/offer-evaluation-system.st")
    systemPromptResource: Resource,
) {
    private val systemPrompt: String = systemPromptResource.inputStream.bufferedReader().readText()

    fun evaluate(offerText: String, profileContext: String): Mono<String> {
        log.info("Starting an evaluation")
        val userMessage = """
            Candidate Profile:
            $profileContext

            Job Offer to Evaluate:
            $offerText
        """.trimIndent()

        return Mono.fromCallable { evaluateWithToolFallback(userMessage) }
            .subscribeOn(Schedulers.boundedElastic())
            .doOnSuccess { log.info("Evaluation completed") }
            .doOnError { e -> log.error("Evaluation error", e) }
    }

    private fun evaluateWithToolFallback(userMessage: String): String =
        try {
            evaluateWithTools(userMessage)
        } catch (ex: NonTransientAiException) {
            if (!ex.isToolUseFailed()) {
                throw ex
            }

            log.warn("Model produced an invalid tool call; retrying evaluation without tools")
            evaluateWithoutTools(userMessage)
        }

    private fun evaluateWithTools(userMessage: String): String =
        chatClient
            .prompt()
            .system(systemPrompt)
            .user(userMessage)
            .tools(webTool)
            .call()
            .content()
            .orEmpty()

    private fun evaluateWithoutTools(userMessage: String): String =
        chatClient
            .prompt()
            .system(systemPromptWithoutTools)
            .user(userMessage)
            .call()
            .content()
            .orEmpty()

    private fun NonTransientAiException.isToolUseFailed(): Boolean =
        message?.contains(TOOL_USE_FAILED) == true

    companion object {
        private val log = LoggerFactory.getLogger(EvaluationService::class.java)
        private const val TOOL_USE_FAILED = "tool_use_failed"
        private val systemPromptWithoutToolsSuffix = """

            Tool retry policy:
            External tools are unavailable for this retry. Do not call tools, do not write pseudo tool calls, and do not mention tool-call syntax.
            Use only the candidate profile and job offer text. If company research is missing, state that clearly. Do not infer or convert salary values.
        """.trimIndent()
    }

    private val systemPromptWithoutTools = systemPrompt + "\n\n" + systemPromptWithoutToolsSuffix
}
