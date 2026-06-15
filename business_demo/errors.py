class BusinessDemoError(Exception):
    def __init__(self, code, message, reason, status_code=400):
        super().__init__(reason)
        self.code = code
        self.message = message
        self.reason = reason
        self.status_code = status_code

    def detail(self):
        return {"code": self.code, "message": self.message, "reason": self.reason}


ERRORS = {
    "BUSINESS_USER_NOT_FOUND": (
        404,
        "业务用户不存在",
        "业务用户不存在，请先在业务系统中创建用户",
    ),
    "USER_DISABLED": (
        403,
        "业务用户已禁用",
        "该业务用户已禁用，不能登录",
    ),
    "FACE_ALREADY_BOUND": (
        409,
        "业务用户已绑定人脸",
        "该业务用户已经绑定过人脸，请先解绑或执行换脸",
    ),
    "FACE_NOT_BOUND": (
        403,
        "业务用户未绑定人脸",
        "该业务用户还没有绑定人脸，请先完成绑定后再登录",
    ),
    "TOKEN_INVALID": (
        401,
        "登录凭证无效",
        "登录凭证无效或已过期，请重新登录",
    ),
    "LIVENESS_CHALLENGE_REQUIRED": (
        403,
        "需要先完成活体挑战",
        "当前绑定策略要求先完成活体挑战，请完成动作后再绑定人脸",
    ),
    "FACE_API_UNAVAILABLE": (
        503,
        "人脸识别服务不可用",
        "人脸识别服务不可用，请检查 face_api 是否启动",
    ),
    "FACE_API_AUTH_FAILED": (
        502,
        "人脸识别服务认证失败",
        "人脸识别服务认证失败，请检查服务端 API Key 配置",
    ),
    "VALIDATION_ERROR": (
        422,
        "请求参数校验失败",
        "请求参数格式或取值不符合业务 demo 接口要求",
    ),
}


def raise_business_error(code, message=None, reason=None, status_code=None):
    default_status, default_message, default_reason = ERRORS.get(
        code,
        (400, "业务请求失败", "业务请求处理失败，请查看返回的错误码"),
    )
    raise BusinessDemoError(
        code=code,
        message=message or default_message,
        reason=reason or default_reason,
        status_code=status_code or default_status,
    )
