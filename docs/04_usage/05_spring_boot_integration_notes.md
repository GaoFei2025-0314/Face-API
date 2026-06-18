# Java / Spring Boot 接入说明

> 适用范围：真实 Java 业务后端替换 V2.0 `business-demo`，并处理 V2.3 中风险一次重试。

## 1. 职责边界

Spring Boot 业务系统负责：

- 业务用户表。
- 人脸绑定表。
- 登录态、session、JWT 或 SSO。
- 权限和角色。
- 业务登录 audit。
- 调用 `face_api` 并处理识别结果。

`face_api` 负责：

- 人脸注册。
- 活体 challenge。
- face login 匹配。
- 识别层 audit。
- 中文错误原因。

## 2. 推荐模块

```text
controller/
  FaceBindingController
  FaceAuthController
  TerminalLoginController

service/
  BusinessUserService
  FaceBindingService
  FaceLoginService
  BusinessAuditService

client/
  FaceApiClient

repository/
  BusinessUserRepository
  FaceBindingRepository
  BusinessLoginAuditRepository
```

## 3. FaceApiClient 伪代码

```java
class FaceApiClient {
    private String baseUrl;
    private String apiKey;

    FaceRegisterResponse registerFace(RegisterFaceRequest request) {
        // POST {baseUrl}/faces/register
        // Header: X-API-Key: apiKey
        // Body: user_id, username, terminal_id, image, challenge_id, metadata
        // On non-2xx: parse detail.code / detail.message / detail.reason
    }

    FaceLoginResponse faceLogin(FaceLoginRequest request) {
        // POST {baseUrl}/auth/face-login
        // Header: X-API-Key: apiKey
        // Body: image, terminal_id, challenge_id, threshold, state, risk_retry_token
        // Response: authenticated, match.face_id, match.user_id, match.username, similarity, threshold
        // On ANTI_SPOOF_MEDIUM_RETRY_REQUIRED: parse detail.retry and return retry instruction to browser/terminal
    }

    LivenessChallengeResponse createChallenge(String purpose, String terminalId) {
        // POST {baseUrl}/liveness/challenges
        // Header: X-API-Key: apiKey
    }

    LivenessSubmitResponse submitChallenge(String challengeId, List<String> frames) {
        // POST {baseUrl}/liveness/challenges/submit
        // Header: X-API-Key: apiKey
    }

    void deleteFace(String faceId) {
        // DELETE {baseUrl}/faces/{faceId}
        // Header: X-API-Key: apiKey
    }
}
```

V2.3 中风险错误必须按结构化对象解析，不要只取字符串 `message`：

```json
{
  "detail": {
    "code": "ANTI_SPOOF_MEDIUM_RETRY_REQUIRED",
    "message": "检测到中风险，请重试一次",
    "reason": "当前画面存在轻量防翻拍中风险，请重新面对摄像头完成一次采集",
    "retry": {
      "risk_retry_token": "<opaque-token>",
      "expires_at": "2026-06-17T12:00:00Z",
      "remaining_attempts": 1
    }
  }
}
```

Java 后端处理规则：

- `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED` 不是登录成功，不签发 session/JWT/SSO。
- 业务后端应把 `detail.retry.risk_retry_token`、`expires_at` 和 `remaining_attempts` 作为一次性重试指令返回给浏览器或受控终端。
- 浏览器或终端第二次必须重新完成 login challenge，并把新的 `challenge_id` 和原始 `risk_retry_token` 一起提交给业务后端。
- Java 后端第二次代理 `/auth/face-login` 时原样回传 `risk_retry_token`；不要解析 token 内容，不要写入业务 audit 明文。
- `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED` 和 `ANTI_SPOOF_RETRY_TOKEN_INVALID` 都应按登录失败处理，可提示重新开始或转人工。
- `ANTI_SPOOF_MEDIUM_BLOCKED` 表示当前策略直接拦截中风险，Java 后端应按登录失败处理，不要继续自动重试。
- `ANTI_SPOOF_CONFIG_INVALID` 表示服务端防翻拍策略配置异常，Java 后端应按失败处理并提示运维检查防翻拍策略配置。

## 4. 绑定 Service 伪代码

```java
class FaceBindingService {
    BusinessUserRepository users;
    FaceBindingRepository bindings;
    FaceApiClient faceApi;

    FaceBinding bindFace(String userId, String imageBase64, String terminalId) {
        BusinessUser user = users.findActiveByUserId(userId)
            .orElseThrow(() -> new BusinessException("BUSINESS_USER_NOT_FOUND"));

        if (bindings.hasActiveBinding(userId)) {
            throw new BusinessException("FACE_ALREADY_BOUND");
        }

        FaceRegisterResponse response = faceApi.registerFace(new RegisterFaceRequest(
            userId,
            user.getUsername(),
            terminalId,
            imageBase64
        ));

        return bindings.create(userId, response.getFaceId(), "web_demo");
    }

    void unbindFace(String userId) {
        FaceBinding binding = bindings.findActiveByUserId(userId)
            .orElseThrow(() -> new BusinessException("FACE_NOT_BOUND"));

        faceApi.deleteFace(binding.getFaceId());
        bindings.markRemoved(binding.getId());
    }

    FaceBinding replaceFace(String userId, String imageBase64, String terminalId) {
        BusinessUser user = users.findActiveByUserId(userId)
            .orElseThrow(() -> new BusinessException("BUSINESS_USER_NOT_FOUND"));

        FaceBinding oldBinding = bindings.findActiveByUserId(userId).orElse(null);
        FaceRegisterResponse response = faceApi.registerFace(new RegisterFaceRequest(
            userId,
            user.getUsername(),
            terminalId,
            imageBase64
        ));

        FaceBinding newBinding = bindings.replaceActiveBinding(userId, response.getFaceId(), "web_demo");
        if (oldBinding != null) {
            faceApi.deleteFace(oldBinding.getFaceId());
        }
        return newBinding;
    }
}
```

## 5. 登录 Service 伪代码

```java
class FaceLoginService {
    BusinessUserRepository users;
    FaceBindingRepository bindings;
    BusinessAuditService audit;
    FaceApiClient faceApi;
    TokenService tokenService;

    LoginResult loginByFace(String imageBase64, String challengeId, String terminalId, String state, String riskRetryToken) {
        try {
            FaceLoginResponse faceResult = faceApi.faceLogin(new FaceLoginRequest(
                imageBase64,
                challengeId,
                terminalId,
                state,
                riskRetryToken
            ));

            if (!faceResult.isAuthenticated()) {
                throw new BusinessException("FACE_API_LOGIN_REJECTED");
            }

            String userId = faceResult.getMatchedUserId();
            BusinessUser user = users.findActiveByUserId(userId)
                .orElseThrow(() -> new BusinessException("BUSINESS_USER_NOT_FOUND"));

            FaceBinding binding = bindings.findActiveByUserId(userId)
                .orElseThrow(() -> new BusinessException("FACE_NOT_BOUND"));

            if (faceResult.getMatchedFaceId() != null
                    && !faceResult.getMatchedFaceId().equals(binding.getFaceId())) {
                throw new BusinessException("FACE_API_MATCH_MISMATCH");
            }

            String token = tokenService.issue(user);
            audit.recordSuccess(userId, terminalId, faceResult.getSimilarity(), token);
            return LoginResult.success(user, token);
        } catch (BusinessException ex) {
            audit.recordFailure(null, terminalId, ex.getCode());
            throw ex;
        } catch (FaceApiException ex) {
            audit.recordFailure(null, terminalId, ex.getCode());
            if ("ANTI_SPOOF_MEDIUM_RETRY_REQUIRED".equals(ex.getCode())) {
                return LoginResult.retry(
                    ex.getMessage(),
                    ex.getReason(),
                    ex.getRetry().getRiskRetryToken(),
                    ex.getRetry().getExpiresAt(),
                    ex.getRetry().getRemainingAttempts()
                );
            }
            throw new BusinessException(ex.getCode(), ex.getReason());
        }
    }
}
```

## 6. 终端上报 Service 伪代码

```java
class TerminalLoginService {
    BusinessUserRepository users;
    FaceBindingRepository bindings;
    BusinessAuditService audit;

    TerminalLoginResult acceptTerminalEvent(TerminalLoginEvent event) {
        BusinessLoginAudit existing = audit.findByTerminalEventId(event.getEventId()).orElse(null);
        if (existing != null) {
            return TerminalLoginResult.duplicate(existing.getId());
        }
        if (event.isExpired()) {
            String auditId = audit.recordFailure(
                event.getMatchedUserId(),
                event.getTerminalId(),
                "TERMINAL_EVENT_EXPIRED",
                event.getEventId()
            );
            return TerminalLoginResult.reject("TERMINAL_EVENT_EXPIRED", auditId);
        }
        if (!event.getFaceApiResult().isAuthenticated()
                || !event.getMatchedUserId().equals(event.getFaceApiResult().getMatchedUserId())) {
            audit.recordFailure(event.getMatchedUserId(), event.getTerminalId(), "FACE_API_MATCH_MISMATCH", event.getEventId());
            return TerminalLoginResult.reject("FACE_API_MATCH_MISMATCH");
        }
        BusinessUser user = users.findByUserId(event.getMatchedUserId()).orElse(null);
        if (user == null) {
            audit.recordFailure(event.getMatchedUserId(), event.getTerminalId(), "BUSINESS_USER_NOT_FOUND", event.getEventId());
            return TerminalLoginResult.reject("BUSINESS_USER_NOT_FOUND");
        }
        if (!user.isActive()) {
            audit.recordFailure(user.getUserId(), event.getTerminalId(), "USER_DISABLED", event.getEventId());
            return TerminalLoginResult.reject("USER_DISABLED");
        }
        FaceBinding binding = bindings.findActiveByUserId(user.getUserId()).orElse(null);
        if (binding == null) {
            audit.recordFailure(user.getUserId(), event.getTerminalId(), "FACE_NOT_BOUND", event.getEventId());
            return TerminalLoginResult.reject("FACE_NOT_BOUND");
        }
        if (event.getFaceApiResult().getMatchedFaceId() != null
                && !event.getFaceApiResult().getMatchedFaceId().equals(binding.getFaceId())) {
            audit.recordFailure(user.getUserId(), event.getTerminalId(), "FACE_API_MATCH_MISMATCH", event.getEventId());
            return TerminalLoginResult.reject("FACE_API_MATCH_MISMATCH");
        }
        audit.recordSuccess(user.getUserId(), event.getTerminalId(), event.getSimilarity(), null, event.getEventId());
        return TerminalLoginResult.accept(user);
    }
}
```

## 7. Controller 伪代码

```java
@RestController
class FaceAuthController {
    FaceLoginService faceLoginService;

    @PostMapping("/api/auth/face-login")
    LoginResult faceLogin(@RequestBody FaceLoginRequest request) {
        return faceLoginService.loginByFace(
            request.getImage(),
            request.getChallengeId(),
            request.getTerminalId(),
            request.getState(),
            request.getRiskRetryToken()
        );
    }
}

@RestController
class TerminalLoginController {
    TerminalLoginService terminalLoginService;

    @PostMapping("/api/terminal/login-events")
    TerminalLoginResult loginEvent(@RequestBody TerminalLoginEvent event) {
        return terminalLoginService.acceptTerminalEvent(event);
    }
}
```

## 8. 错误分层

推荐分三层处理：

| 层级 | 示例 code | 处理方式 |
|---|---|---|
| `face_api` 识别层 | `NO_FACE`、`NO_MATCH`、`LIVENESS_CHALLENGE_INVALID` | Java 后端解析 `detail.code/message/reason`，原样转成业务可展示原因 |
| `face_api` 中风险策略 | `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED`、`ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED`、`ANTI_SPOOF_MEDIUM_BLOCKED`、`ANTI_SPOOF_RETRY_TOKEN_INVALID` | 第一次重试策略返回 `detail.retry`；耗尽、直接拦截或无效时按失败处理 |
| 业务规则层 | `BUSINESS_USER_NOT_FOUND`、`USER_DISABLED`、`FACE_NOT_BOUND` | Java Service 根据用户表、绑定表和状态自行判断 |
| 接入配置层 | `FACE_API_AUTH_FAILED`、`FACE_API_UNAVAILABLE`、`VALIDATION_ERROR`、`ANTI_SPOOF_CONFIG_INVALID` | 运维或后端配置问题，写 audit 并提示检查服务地址、API Key、请求字段或防翻拍策略配置 |
| 登录态层 | `TOKEN_INVALID` | 替换成生产系统自己的 session、JWT 或 SSO 过期处理 |

## 9. 生产注意事项

- `face_api` 的 `X-API-Key` 只能放在后端配置或受控终端配置中。
- Web 浏览器不要直接调用 `face_api` 受保护接口。
- Java 后端应设置调用超时，避免摄像头页面长时间等待。
- Java 后端必须解析 `detail.code`、`detail.message`、`detail.reason`。
- Java 后端必须解析 V2.3 的 `detail.retry`，但不要把原始 `risk_retry_token` 明文写入业务 audit 或日志。
- 登录成功后由 Java 后端签发自己的 session、JWT 或 SSO token。
- 业务 audit 和 `face_api` audit 是两层记录，不要混为一张表。
- 换脸流程要考虑删除旧 `face_id` 成功但注册新脸失败的补偿策略。
- V2.0 demo token 可用 Python 标准库 HMAC 实现；Java 生产系统应替换为自己的 session、JWT 或 SSO。
- 如果启用绑定活体，Java 后端应在绑定前完成 register challenge，并把 `challenge_id` 传给 `face_api /faces/register`。
