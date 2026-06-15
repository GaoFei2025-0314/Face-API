# V2.0 业务系统接入说明

> 适用范围：业务前端、业务后端、受控终端接入 `face_api` 的标准流程。

## 1. 接入原则

`face_api` 只做人脸识别服务，不做业务用户系统。正式业务系统必须自己管理：

- 用户主表。
- 登录态、session、JWT 或 SSO。
- 权限和角色。
- 业务登录 audit。
- 最终是否允许登录、开门、签到或执行业务动作。

`face_api` 返回的是识别证据，包括 `user_id`、`username`、`similarity`、`threshold`、活体状态和失败原因。业务系统根据这些证据做最终判断。

## 2. Web 业务系统推荐链路

正式 Web 链路：

```text
业务浏览器页面
  -> 业务后端
  -> face_api
```

这样做的原因：

- 浏览器不直接持有 `face_api` 的 `X-API-Key`。
- 业务后端可以统一处理用户状态、登录态、权限和 audit。
- 真实 Java / Spring Boot 后端可以替换 V2.0 的 `business-demo`。

V2.0 demo 中：

```text
http://localhost:8010
```

是业务接入页面入口。它只调用 `business-demo`，不直接调用 `face_api`。

## 3. 业务用户和人脸绑定

推荐流程：

```text
业务系统先有用户
  -> 选择用户
  -> 采集人脸
  -> 业务后端调用 face_api /faces/register
  -> 业务后端保存 user_id 和 face_id 绑定
```

约束：

- 一个业务用户只允许一个有效人脸绑定。
- 已绑定用户再次绑定时，应提示先解绑或执行换脸。
- 换脸流程是“删除旧 face_id -> 注册新 face_id -> 更新绑定”。
- 业务用户资料不要写入 `face_api`，只传必要的 `user_id`、`username` 和 metadata。

## 4. Web 人脸登录

推荐流程：

```text
业务页面请求创建 login challenge
  -> 业务后端调用 face_api /liveness/challenges
  -> 页面采集连续帧
  -> 业务后端调用 face_api /liveness/challenges/submit
  -> 页面采集登录图片
  -> 业务后端调用 face_api /auth/face-login
  -> 业务后端查询自己的用户表
  -> 业务后端签发自己的 token/session
```

登录规则：

- 登录必须启用活体。
- `face_api` 不签发业务 token。
- `matched_user_id` 必须回到业务用户表校验。
- 用户不存在、禁用、未绑定或绑定不一致时，业务后端必须拒绝登录。

## 5. 受控终端链路

受控终端包括一体机、闸机、Windows 客户端、自助机等。它们由项目方管理，可以配置 `face_api` 的 `X-API-Key`。

推荐流程：

```text
受控终端
  -> 直接调用 face_api 完成活体和 face login
  -> 得到 matched_user_id / similarity / terminal_id
  -> 上报业务后端
  -> 业务后端确认用户状态并写业务 audit
```

终端要求：

- 每台终端使用稳定 `terminal_id`。
- 终端不要把 API Key 打印到界面、日志或错误信息里。
- 终端失败时展示中文原因。
- 终端上报业务后端时要带上 trace/state，便于排障。

## 6. 业务层错误码建议

| code | 中文原因 |
|---|---|
| `BUSINESS_USER_NOT_FOUND` | 业务用户不存在，请先在业务系统中创建用户 |
| `USER_DISABLED` | 该业务用户已禁用，不能登录 |
| `FACE_ALREADY_BOUND` | 该业务用户已经绑定过人脸，请先解绑或执行换脸 |
| `FACE_NOT_BOUND` | 该业务用户还没有绑定人脸 |
| `TOKEN_INVALID` | 登录凭证无效或已过期，请重新登录 |
| `FACE_API_UNAVAILABLE` | 人脸识别服务不可用，请检查 face_api 是否启动 |
| `FACE_API_AUTH_FAILED` | 人脸识别服务认证失败，请检查服务端 API Key 配置 |

业务页面应优先展示业务层中文原因；如果错误来自 `face_api`，展示 `detail.reason`。

## 7. 上线检查清单

- [ ] 浏览器不直接访问 `face_api` 受保护接口。
- [ ] 浏览器不保存、不展示、不打印 `face_api` 的 `X-API-Key`。
- [ ] 业务后端能访问 `face_api /health`。
- [ ] 业务后端已配置 `face_api` 地址和 API Key。
- [ ] 业务用户先存在，再绑定人脸。
- [ ] 一个业务用户只有一个有效人脸绑定。
- [ ] 登录必须完成活体 challenge。
- [ ] 登录成功后由业务系统签发 token/session。
- [ ] 业务登录成功和失败都写入业务 audit。
- [ ] 终端使用稳定 `terminal_id`。
- [ ] 终端密钥只放在受控设备配置中。
- [ ] Java / Spring Boot 生产接入已替换 demo JWT。
