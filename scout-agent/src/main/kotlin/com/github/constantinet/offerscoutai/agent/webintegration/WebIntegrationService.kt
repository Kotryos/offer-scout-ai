package com.github.constantinet.offerscoutai.agent.webintegration

import reactor.core.publisher.Mono

interface WebIntegrationService {
    fun searchWeb(query: String): Mono<String>
    fun fetchPage(url: String): Mono<String>
}