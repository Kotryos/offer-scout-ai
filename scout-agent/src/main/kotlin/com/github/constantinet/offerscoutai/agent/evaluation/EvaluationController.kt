package com.github.constantinet.offerscoutai.agent.evaluation

import org.slf4j.LoggerFactory
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import reactor.core.publisher.Mono

@RestController
@RequestMapping("/offer")
class EvaluationController(
    private val evaluationService: EvaluationService,
) {

    @PostMapping("/evaluation")
    fun evaluate(@RequestBody request: EvaluationRequest): Mono<EvaluationResponse> {
        log.info("Received an evaluation request")
        return evaluationService.evaluate(request.offerText, request.profileContext)
            .map { evaluation -> EvaluationResponse(evaluation) }
    }

    data class EvaluationRequest(
        val offerText: String,
        val profileContext: String,
    )

    data class EvaluationResponse(
        val evaluation: String,
    )

    companion object {
        private val log = LoggerFactory.getLogger(EvaluationController::class.java)
    }
}