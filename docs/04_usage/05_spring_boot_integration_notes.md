# Java / Spring Boot 接入说明

> 适用范围：真实 Java 业务后端替换 V2.0 `business-demo`。

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
        // Body: image, terminal_id, challenge_id, threshold, state
    }

    LivenessChallengeResponse createChallenge(String purpose, String terminalId) {
        // POST {baseUrl}/liveness/challenges
    }

    LivenessSubmitResponse submitChallenge(String challengeId, List<String> frames) {
        // POST {baseUrl}/liveness/challenges/submit
    }

    void deleteFace(String faceId) {
        // DELETE {baseUrl}/faces/{faceId}
    }
}
```

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

    LoginResult loginByFace(String imageBase64, String challengeId, String terminalId, String state) {
        try {
            FaceLoginResponse faceResult = faceApi.faceLogin(new FaceLoginRequest(
                imageBase64,
                challengeId,
                terminalId,
                state
            ));

            String userId = faceResult.getMatchedUserId();
            BusinessUser user = users.findActiveByUserId(userId)
                .orElseThrow(() -> new BusinessException("BUSINESS_USER_NOT_FOUND"));

            if (!bindings.hasActiveBinding(userId)) {
                throw new BusinessException("FACE_NOT_BOUND");
            }

            String token = tokenService.issue(user);
            audit.recordSuccess(userId, terminalId, faceResult.getSimilarity(), token);
            return LoginResult.success(user, token);
        } catch (BusinessException ex) {
            audit.recordFailure(null, terminalId, ex.getCode());
            throw ex;
        } catch (FaceApiException ex) {
            audit.recordFailure(null, terminalId, ex.getCode());
            throw new BusinessException(ex.getCode(), ex.getReason());
        }
    }
}
```

## 6. Controller 伪代码

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
            request.getState()
        );
    }
}
```

## 7. 生产注意事项

- `face_api` 的 `X-API-Key` 只能放在后端配置或受控终端配置中。
- Web 浏览器不要直接调用 `face_api` 受保护接口。
- Java 后端应设置调用超时，避免摄像头页面长时间等待。
- Java 后端必须解析 `detail.code`、`detail.message`、`detail.reason`。
- 登录成功后由 Java 后端签发自己的 session、JWT 或 SSO token。
- 业务 audit 和 `face_api` audit 是两层记录，不要混为一张表。
- 换脸流程要考虑删除旧 `face_id` 成功但注册新脸失败的补偿策略。
