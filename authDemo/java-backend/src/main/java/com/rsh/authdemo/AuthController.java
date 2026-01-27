package com.rsh.authdemo;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
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
        String token = authHeader.replace("Bearer ", "");
        
        // 使用 SDK 解析 Token 获取用户信息 (本地解析 Claims)
        try {
            User user = casdoorAuthService.parseJwtToken(token);
            // 转换为 Map 返回给前端
            Map<String, Object> userMap = new HashMap<>();
            userMap.put("name", user.name);
            userMap.put("username", user.name); // SDK uses name as username usually
            userMap.put("displayName", user.displayName);
            userMap.put("email", user.email);
            userMap.put("avatar", user.avatar);
            userMap.put("id", user.id);
            userMap.put("organization", user.owner);
            userMap.put("roles", user.roles);
            return userMap;
        } catch (Exception e) {
             throw new RuntimeException("SDK failed to parse token: " + e.getMessage());
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
