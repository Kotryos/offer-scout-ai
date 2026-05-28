package com.github.constantinet.offerscoutai.agent.evaluation

import org.springframework.ai.chat.client.ChatClient
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class EvaluationConfiguration {

    @Bean
    fun chatClient(builder: ChatClient.Builder): ChatClient = builder.build()
}