package com.rsh.authdemo;

import org.casbin.casdoor.config.Config;
import org.casbin.casdoor.service.AuthService;
import org.casbin.casdoor.service.UserService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class CasdoorConfiguration {

    @Value("${casdoor.endpoint}")
    private String endpoint;

    @Value("${casdoor.client-id}")
    private String clientId;

    @Value("${casdoor.client-secret}")
    private String clientSecret;

    @Value("${casdoor.certificate}")
    private String certificate;

    @Value("${casdoor.organization-name}")
    private String organizationName;

    @Value("${casdoor.application-name}")
    private String applicationName;

    @Bean
    public Config casdoorConfig() {
        return new Config(endpoint, clientId, clientSecret, certificate, organizationName, applicationName);
    }

    @Bean
    public AuthService casdoorAuthService(Config casdoorConfig) {
        return new AuthService(casdoorConfig);
    }

    @Bean
    public UserService casdoorUserService(Config casdoorConfig) {
        return new UserService(casdoorConfig);
    }
}
