package com.github.constantinet.offerscoutai.agent.common

import io.micrometer.context.ContextRegistry
import org.slf4j.MDC
import org.springframework.stereotype.Component
import org.springframework.web.server.ServerWebExchange
import org.springframework.web.server.WebFilter
import org.springframework.web.server.WebFilterChain
import reactor.core.publisher.Mono
import reactor.core.publisher.Hooks
import java.util.UUID

@Component
class CorrelationIdFilter : WebFilter {

    override fun filter(exchange: ServerWebExchange, chain: WebFilterChain): Mono<Void> {
        val correlationId = exchange.request.headers.getFirst(HEADER)
            ?.takeIf { it.isNotBlank() }
            ?: UUID.randomUUID().toString()

        exchange.response.headers.set(HEADER, correlationId)

        return Mono.defer {
            MDC.put(MDC_KEY, correlationId)
            chain.filter(exchange)
        }
            .contextWrite { context -> context.put(MDC_KEY, correlationId) }
            .doFinally { MDC.remove(MDC_KEY) }
    }

    companion object {
        const val HEADER = "X-Correlation-ID"
        const val MDC_KEY = "correlationId"

        init {
            ContextRegistry.getInstance().removeThreadLocalAccessor(MDC_KEY)
            ContextRegistry.getInstance().registerThreadLocalAccessor(
                MDC_KEY,
                { MDC.get(MDC_KEY) },
                { value -> MDC.put(MDC_KEY, value) },
                { MDC.remove(MDC_KEY) }
            )
            Hooks.enableAutomaticContextPropagation()
        }
    }
}