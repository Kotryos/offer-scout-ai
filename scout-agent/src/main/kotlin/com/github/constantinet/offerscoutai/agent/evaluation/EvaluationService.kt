package com.github.constantinet.offerscoutai.agent.evaluation

import com.github.constantinet.offerscoutai.agent.tool.WebTool
import org.slf4j.LoggerFactory
import org.springframework.ai.chat.client.ChatClient
import org.springframework.core.io.ClassPathResource
import org.springframework.stereotype.Service
import reactor.core.publisher.Mono
import reactor.core.scheduler.Schedulers

@Service
class EvaluationService(
    private val chatClient: ChatClient, private val webTool: WebTool
) {
    private val systemPrompt: String = ClassPathResource(PROMPT).inputStream.bufferedReader().readText()

    fun evaluate(offerText: String, profileContext: String): Mono<String> {
        log.info("Starting an evaluation")
        val userMessage = """
            Candidate Profile:
            $profileContext

            Job Offer to Evaluate:
            $offerText
        """.trimIndent()

        return Mono.fromCallable {
            chatClient
                .prompt()
                .system(systemPrompt)
                .user(userMessage)
                .tools(webTool)
                .call()
                .content()
                .orEmpty()
        }
            .subscribeOn(Schedulers.boundedElastic())
            .doOnSuccess { log.info("Evaluation completed") }
            .doOnError { e -> log.error("Evaluation error", e) }
    }

    companion object {
        private val log = LoggerFactory.getLogger(EvaluationService::class.java)

        private const val PROMPT = "prompts/offer-evaluation-system.st"
    }
}
