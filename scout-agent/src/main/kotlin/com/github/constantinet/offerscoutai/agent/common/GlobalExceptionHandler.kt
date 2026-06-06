package com.github.constantinet.offerscoutai.agent.common

import org.slf4j.LoggerFactory
import org.springframework.ai.retry.NonTransientAiException
import org.springframework.ai.retry.TransientAiException
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.reactive.function.client.WebClientResponseException

@RestControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(NonTransientAiException::class)
    fun handleNonTransientAiException(ex: NonTransientAiException): ResponseEntity<Map<String, String>> {
        val msg = ex.message ?: ""
        log.error("Non-transient AI error", ex)

        return when {
            msg.contains("tool_use_failed") ->
                ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(mapOf("error" to CODE_AI_TOOL_CALL_ERROR, "message" to MSG_AI_TOOL_CALL_ERROR))

            msg.contains("429") || msg.contains("RESOURCE_EXHAUSTED") || msg.lowercase().contains("quota") ->
                ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                    .body(mapOf("error" to CODE_QUOTA_EXCEEDED, "message" to MSG_PLEASE_TRY_LATER))

            msg.contains("401") || msg.contains("API_KEY_INVALID") || msg.lowercase().contains("unauthorized") ->
                ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(mapOf("error" to CODE_INVALID_API_KEY, "message" to MSG_INVALID_CONFIGURATION))

            else -> ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                .body(mapOf("error" to CODE_AI_ERROR, "message" to MSG_UNEXPECTED_AI_ERROR))
        }
    }

    @ExceptionHandler(TransientAiException::class)
    fun handleTransientAiException(ex: TransientAiException): ResponseEntity<Map<String, String>> {
        log.error("Transient AI error", ex)
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(mapOf("error" to CODE_AI_UNAVAILABLE, "message" to MSG_AI_UNAVAILABLE))
    }

    @ExceptionHandler(WebClientResponseException::class)
    fun handleWebClientResponseException(ex: WebClientResponseException): ResponseEntity<Map<String, String>> {
        log.error("Upstream HTTP error {}", ex.statusCode, ex)
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
            .body(mapOf("error" to CODE_UPSTREAM_ERROR, "message" to UPSTREAM_MSG_PREFIX + ex.statusCode))
    }

    @ExceptionHandler(Exception::class)
    fun handleGenericException(ex: Exception): ResponseEntity<Map<String, String>> {
        log.error("Unexpected error", ex)
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(mapOf("error" to CODE_INTERNAL_ERROR, "message" to MSG_INTERNAL_ERROR))
    }

    companion object {
        private val log = LoggerFactory.getLogger(GlobalExceptionHandler::class.java)

        const val CODE_QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
        const val CODE_INVALID_API_KEY = "INVALID_API_KEY"
        const val CODE_AI_TOOL_CALL_ERROR = "AI_TOOL_CALL_ERROR"
        const val CODE_AI_ERROR = "AI_ERROR"
        const val CODE_AI_UNAVAILABLE = "AI_UNAVAILABLE"
        const val CODE_UPSTREAM_ERROR = "UPSTREAM_ERROR"
        const val CODE_INTERNAL_ERROR = "INTERNAL_ERROR"

        const val MSG_PLEASE_TRY_LATER = "Please try again later"
        const val MSG_INVALID_CONFIGURATION = "Invalid configuration"
        const val MSG_AI_TOOL_CALL_ERROR = "The AI model produced an invalid tool call"
        const val MSG_UNEXPECTED_AI_ERROR = "An unexpected AI service error occurred"
        const val MSG_AI_UNAVAILABLE = "AI service temporarily unavailable"
        const val UPSTREAM_MSG_PREFIX = "Upstream service returned "
        const val MSG_INTERNAL_ERROR = "An unexpected error occurred"
    }
}
