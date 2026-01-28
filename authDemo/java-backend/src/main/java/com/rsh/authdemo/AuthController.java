package com.rsh.authdemo;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.server.ResponseStatusException;
import com.auth0.jwt.JWT;
import com.auth0.jwt.interfaces.DecodedJWT;
import org.casbin.casdoor.service.AuthService;
import org.casbin.casdoor.service.UserService;
import org.casbin.casdoor.entity.User;

import java.util.Map;
import java.util.HashMap;
import java.util.List;

@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = "*") // Allow Vue app to call
public class AuthController {

    @Autowired
    private AuthService casdoorAuthService;

    @Autowired
    private UserService casdoorUserService;

    @Value("${casdoor.endpoint}")
    private String casdoorEndpoint;

    @Value("${casdoor.client-id}")
    private String clientId;

    @Value("${casdoor.redirect-uri}")
    private String redirectUri;

    @GetMapping("/login-url")
    public Map<String, String> getLoginUrl() {
        // 使用 SDK 获取登录链接
        String authorizeUrl = casdoorAuthService.getSigninUrl(redirectUri);
        return Map.of("login_url", authorizeUrl);
    }

    @GetMapping("/logout-url")
    public Map<String, String> getLogoutUrl(@RequestParam(required = false) String redirectUri, @RequestParam(required = false) String id_token_hint) {
        // 构造 Casdoor 登出 URL
        // 默认跳回登录回调地址的根路径（即前端首页），如果前端传了 redirectUri 则使用传入的
        String targetUrl = this.redirectUri;
        if (redirectUri != null && !redirectUri.isEmpty()) {
            targetUrl = redirectUri;
        } else {
             // 尝试从配置的回调地址中提取首页地址 (去除 /callback)
             if (targetUrl.endsWith("/callback")) {
                 targetUrl = targetUrl.substring(0, targetUrl.length() - "/callback".length());
             }
        }

        try {
            StringBuilder logoutUrl = new StringBuilder(String.format("%s/api/logout?post_logout_redirect_uri=%s",
                    casdoorEndpoint,
                    java.net.URLEncoder.encode(targetUrl, java.nio.charset.StandardCharsets.UTF_8.toString())));
            
            if (id_token_hint != null && !id_token_hint.isEmpty()) {
                logoutUrl.append("&id_token_hint=").append(id_token_hint);
            }
            
            return Map.of("logout_url", logoutUrl.toString());
        } catch (Exception e) {
            throw new RuntimeException("Failed to encode logout url", e);
        }
    }

    @PostMapping("/sso-logout")
    public Map<String, Object> ssoLogout(@RequestHeader("Authorization") String authHeader) {
        try {
            RestTemplate restTemplate = new RestTemplate();
            HttpHeaders headers = new HttpHeaders();
            headers.set("Authorization", authHeader);
            HttpEntity<Void> entity = new HttpEntity<>(headers);
            ResponseEntity<String> response = restTemplate.exchange(
                casdoorEndpoint + "/api/sso-logout",
                HttpMethod.POST,
                entity,
                String.class
            );

            Map<String, Object> result = new HashMap<>();
            result.put("status", response.getStatusCode().value());
            result.put("body", response.getBody());
            return result;
        } catch (Exception e) {
            throw new RuntimeException("SSO logout failed: " + e.getMessage());
        }
    }

    @PostMapping("/token")
    public Map<String, Object> getToken(@RequestBody Map<String, String> body) {
        String code = body.get("code");
        // 使用 SDK 换取 Token (SDK 内部处理了 token 请求)
        // 注意：Casdoor SDK 的 getOAuthToken 返回的是 Access Token 字符串
        try {
            String token = casdoorAuthService.getOAuthToken(code, "demo"); // state="demo" needs to match login url state if verified
            // Casdoor SDK 目前没有直接返回完整 Token 响应 (包含 refresh token, expires_in) 的公开方法
            // 但 getOAuthToken 会请求 /api/login/oauth/access_token
            
            // 为了保持兼容性，我们构造一个返回结构
            DecodedJWT jwt = JWT.decode(token);
            long expiresIn = (jwt.getExpiresAt().getTime() - System.currentTimeMillis()) / 1000;
            
            Map<String, Object> response = new HashMap<>();
            response.put("access_token", token);
            response.put("token_type", "Bearer");
            response.put("expires_in", expiresIn);
            return response;
        } catch (Exception e) {
            e.printStackTrace();
            throw new RuntimeException("SDK Failed to get token: " + e.getMessage());
        }
    }

    @GetMapping("/userinfo")
    public Map<String, Object> getUserInfo(@RequestHeader("Authorization") String authHeader) {
        try {
            RestTemplate restTemplate = new RestTemplate();
            HttpHeaders headers = new HttpHeaders();
            headers.set("Authorization", authHeader);
            HttpEntity<Void> entity = new HttpEntity<>(headers);
            ResponseEntity<Map> response = restTemplate.exchange(
                casdoorEndpoint + "/api/userinfo",
                HttpMethod.GET,
                entity,
                Map.class
            );
            return response.getBody();
        } catch (HttpClientErrorException e) {
            throw new ResponseStatusException(e.getStatusCode(), e.getStatusText());
        } catch (Exception e) {
             throw new RuntimeException("Failed to fetch userinfo: " + e.getMessage());
        }
    }

    @GetMapping("/users")
    public List<User> getAllUsers() {
        // 展示 SDK 的用户管理能力
        try {
            return casdoorUserService.getUsers();
        } catch (Exception e) {
            e.printStackTrace();
            // 如果 SDK 失败，尝试手动调用
            // 这里为了演示简单，直接抛出异常
            throw new RuntimeException("Failed to get users: " + e.getMessage());
        }
    }

    @GetMapping("/user/{name}")
    public User getUser(@PathVariable String name) {
        try {
            return casdoorUserService.getUser(name);
        } catch (Exception e) {
            throw new RuntimeException("Failed to get user: " + e.getMessage());
        }
    }
}
