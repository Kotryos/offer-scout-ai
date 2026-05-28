package com.github.constantinet.offerscoutai.agent

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class ScoutAgentApplication

fun main(args: Array<String>) {
    runApplication<ScoutAgentApplication>(*args)
}