import base64
import binascii
import hmac
import json
import math
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, Header, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from .errors import BusinessDemoError, raise_business_error
from .face_api_client import FaceApiClient
from .schemas import (
    BusinessUserCreateReq,
    FaceBindingReq,
    FaceLoginReq,
    LivenessChallengeReq,
    LivenessSubmitReq,
    TerminalLoginEventReq,
)
from .storage import BusinessDB


@dataclass
class BusinessDemoSettings:
    environment: str = "development"
    db_path: str = "business-demo.db"
    face_api_base_url: str = "http://localhost:8000"
    face_api_key: str = ""
    binding_liveness_required: bool = False
    token_secret: str = "business-demo-dev-secret"
    token_ttl_seconds: int = 3600
    port: int = 8010
    seed_demo_users: bool = True


BusinessDemoError = BusinessDemoError


def env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default, minimum=None, maximum=None):
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数，当前值为 {raw}") from exc
    if minimum is not None and value < minimum:
        raise RuntimeError(f"{name} 必须大于等于 {minimum}，当前值为 {raw}")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} 必须小于等于 {maximum}，当前值为 {raw}")
    return value


def load_settings():
    environment = os.getenv("BUSINESS_DEMO_ENV", "development").strip().lower()
    token_secret = os.getenv("BUSINESS_DEMO_TOKEN_SECRET", "business-demo-dev-secret").strip()
    if environment in {"prod", "production"} and (
        not token_secret or token_secret == "business-demo-dev-secret"
    ):
        raise RuntimeError("BUSINESS_DEMO_TOKEN_SECRET 在 production 环境不能为空，且不能使用默认开发密钥")
    return BusinessDemoSettings(
        environment=environment,
        db_path=os.getenv("BUSINESS_DEMO_DB_PATH", "business-demo.db"),
        face_api_base_url=os.getenv("FACE_API_BASE_URL", "http://localhost:8000"),
        face_api_key=os.getenv("FACE_API_KEY", ""),
        binding_liveness_required=env_bool("BUSINESS_DEMO_BINDING_LIVENESS_REQUIRED", False),
        token_secret=token_secret,
        token_ttl_seconds=env_int("BUSINESS_DEMO_TOKEN_TTL_SECONDS", 3600, 1),
        port=env_int("BUSINESS_DEMO_PORT", 8010, 1, 65535),
        seed_demo_users=environment not in {"prod", "production"},
    )


def _b64url(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data):
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def issue_demo_token(user, secret, ttl_seconds=3600):
    payload = {
        "user_id": str(user["user_id"]),
        "username": user["username"],
        "exp": int(time.time()) + ttl_seconds,
        "iat": int(time.time()),
    }
    body = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), sha256).digest()
    return f"{body}.{_b64url(signature)}"


def verify_demo_token(token, secret):
    try:
        body, signature = token.split(".", 1)
        expected = _b64url(hmac.new(secret.encode("utf-8"), body.encode("ascii"), sha256).digest())
    except ValueError:
        raise_business_error("TOKEN_INVALID")
    except UnicodeEncodeError:
        raise_business_error("TOKEN_INVALID")
    if not hmac.compare_digest(signature, expected):
        raise_business_error("TOKEN_INVALID")
    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise_business_error("TOKEN_INVALID")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise_business_error("TOKEN_INVALID")
    return payload


def _value_to_text(value):
    if value is None:
        return ""
    return str(value)


def _login_match(face_result):
    if not isinstance(face_result, dict):
        return {}
    match = face_result.get("match")
    return match if isinstance(match, dict) else {}


def _login_similarity(face_result):
    if not isinstance(face_result, dict):
        return None
    similarity = face_result.get("similarity")
    if similarity is None and isinstance(face_result.get("face"), dict):
        similarity = face_result["face"].get("similarity")
    return similarity


def _matched_face_id(face_result):
    match = _login_match(face_result)
    return match.get("face_id") or match.get("id") or (
        face_result.get("face_id") if isinstance(face_result, dict) else None
    )


def _anti_spoof_risk(face_result):
    if not isinstance(face_result, dict):
        return {}
    risk = face_result.get("anti_spoof_risk")
    return risk if isinstance(risk, dict) else {}


def _validate_face_login_result(face_result, expected_user_id=None, active_binding=None):
    risk = _anti_spoof_risk(face_result)
    if risk.get("level") == "high" or risk.get("action") == "block":
        return "FACE_API_ANTI_SPOOF_HIGH_RISK"
    if not isinstance(face_result, dict) or face_result.get("authenticated") is not True:
        return "FACE_API_LOGIN_REJECTED"
    match = _login_match(face_result)
    matched_user_id = _value_to_text(match.get("user_id"))
    if expected_user_id is not None and matched_user_id != _value_to_text(expected_user_id):
        return "FACE_API_MATCH_MISMATCH"
    face_id = _matched_face_id(face_result)
    if active_binding and face_id and face_id != active_binding["face_id"]:
        return "FACE_API_MATCH_MISMATCH"
    return None


def create_app(settings=None, face_api_client=None):
    settings = settings or load_settings()
    app = FastAPI(title="face_api Business Demo", version="2.0")
    db = BusinessDB(settings.db_path, seed_users=settings.seed_demo_users)
    client = face_api_client or FaceApiClient(settings.face_api_base_url, settings.face_api_key)
    app.state.settings = settings
    app.state.db = db
    app.state.face_api = client

    @app.exception_handler(BusinessDemoError)
    async def business_error_handler(_request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail()})

    @app.exception_handler(ValidationError)
    async def validation_error_handler(_request, _exc):
        try:
            raise_business_error("VALIDATION_ERROR")
        except BusinessDemoError as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail()})

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(_request, _exc):
        try:
            raise_business_error("VALIDATION_ERROR")
        except BusinessDemoError as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail()})

    @app.get("/")
    def index():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/terminal.html")
    def terminal_page():
        return FileResponse(Path(__file__).parent / "static" / "terminal.html")

    @app.get("/api/users")
    def list_users(status: str | None = None):
        return {"users": db.list_users(status=status)}

    @app.post("/api/users")
    def create_user(req: BusinessUserCreateReq):
        return {"user": db.add_user(req.user_id, req.username, req.display_name, req.department)}

    def register_face_for_user(user_id, req: FaceBindingReq):
        user = db.require_active_user(user_id)
        if settings.binding_liveness_required and not req.challenge_id:
            raise_business_error("LIVENESS_CHALLENGE_REQUIRED")
        payload = {
            "user_id": int(user["user_id"]) if str(user["user_id"]).isdigit() else user["user_id"],
            "username": user["username"],
            "terminal_id": req.terminal_id,
            "challenge_id": req.challenge_id,
            "image": req.image,
            "metadata": {"source": "business-demo", "business_user_id": user["user_id"]},
        }
        result = client.register_face(payload)
        face_id = result.get("id") or result.get("face_id")
        return face_id, result

    @app.post("/api/users/{user_id}/face-binding")
    def bind_face(user_id: str, req: FaceBindingReq):
        if db.get_active_binding(user_id):
            raise_business_error("FACE_ALREADY_BOUND")
        face_id, face_result = register_face_for_user(user_id, req)
        binding = db.create_binding(user_id, face_id, source="web_demo", metadata={"face_api": face_result})
        return {"binding": binding}

    @app.delete("/api/users/{user_id}/face-binding")
    def unbind_face(user_id: str, confirm: bool = Query(False)):
        if not confirm:
            raise_business_error("VALIDATION_ERROR", reason="解绑需要 confirm=true")
        removed = db.remove_binding(user_id)
        cleanup_status = "deleted"
        cleanup_error = None
        try:
            client.delete_face(removed["face_id"])
        except BusinessDemoError as exc:
            db.mark_binding_pending_cleanup(removed["id"], reason=exc.code)
            cleanup_status = "pending_cleanup"
            cleanup_error = exc.detail()
        return {
            "ok": True,
            "removed_face_id": removed["face_id"],
            "cleanup_status": cleanup_status,
            "cleanup_error": cleanup_error,
        }

    @app.post("/api/users/{user_id}/face-binding/replace")
    def replace_face(user_id: str, req: FaceBindingReq):
        old = db.get_active_binding(user_id)
        face_id, face_result = register_face_for_user(user_id, req)
        old_binding, new_binding = db.replace_binding(
            user_id,
            face_id,
            source="web_demo",
            metadata={"face_api": face_result, "replace": True},
        )
        old_cleanup_status = None
        old_cleanup_error = None
        if old_binding:
            old_cleanup_status = "deleted"
            try:
                client.delete_face(old_binding["face_id"])
            except BusinessDemoError as exc:
                db.mark_binding_pending_cleanup(old_binding["id"], reason=exc.code)
                old_cleanup_status = "pending_cleanup"
                old_cleanup_error = exc.detail()
        return {
            "binding": new_binding,
            "old_face_id": old["face_id"] if old else None,
            "old_face_cleanup_status": old_cleanup_status,
            "old_face_cleanup_error": old_cleanup_error,
        }

    @app.post("/api/auth/liveness/challenge")
    def create_liveness(req: LivenessChallengeReq):
        return client.create_liveness_challenge({"purpose": req.purpose, "terminal_id": req.terminal_id})

    @app.post("/api/auth/liveness/submit")
    def submit_liveness(req: LivenessSubmitReq):
        return client.submit_liveness_challenge(
            {
                "challenge_id": req.challenge_id,
                "purpose": req.purpose,
                "terminal_id": req.terminal_id,
                "frames": req.frames,
            }
        )

    def reject_login(user_id, terminal_id, source, code, state=None, similarity=None, anti_spoof_risk=None):
        audit_id = db.add_audit(
            user_id=user_id,
            terminal_id=terminal_id,
            source=source,
            success=False,
            failure_reason=code,
            face_similarity=similarity,
            anti_spoof_risk=anti_spoof_risk,
            state=state,
        )
        return audit_id

    @app.post("/api/auth/face-login")
    def face_login(req: FaceLoginReq):
        face_result = client.face_login(
            {
                "image": req.image,
                "terminal_id": req.terminal_id,
                "challenge_id": req.challenge_id,
                "state": req.state,
                "threshold": req.threshold,
            }
        )
        match = _login_match(face_result)
        user_id = str(match.get("user_id") or "")
        similarity = _login_similarity(face_result)
        anti_spoof_risk = _anti_spoof_risk(face_result) or None
        validation_failure = _validate_face_login_result(face_result)
        if validation_failure:
            reject_login(user_id, req.terminal_id, "web", validation_failure, req.state, similarity, anti_spoof_risk)
            raise_business_error(validation_failure)
        user = db.get_user(user_id)
        if not user:
            reject_login(user_id, req.terminal_id, "web", "BUSINESS_USER_NOT_FOUND", req.state, similarity, anti_spoof_risk)
            raise_business_error("BUSINESS_USER_NOT_FOUND")
        if user["status"] != "active":
            reject_login(user_id, req.terminal_id, "web", "USER_DISABLED", req.state, similarity, anti_spoof_risk)
            raise_business_error("USER_DISABLED")
        binding = db.get_active_binding(user_id)
        if not binding:
            reject_login(user_id, req.terminal_id, "web", "FACE_NOT_BOUND", req.state, similarity, anti_spoof_risk)
            raise_business_error("FACE_NOT_BOUND")
        validation_failure = _validate_face_login_result(face_result, expected_user_id=user_id, active_binding=binding)
        if validation_failure:
            reject_login(user_id, req.terminal_id, "web", validation_failure, req.state, similarity, anti_spoof_risk)
            raise_business_error(validation_failure)
        token = issue_demo_token(user, settings.token_secret, settings.token_ttl_seconds)
        audit_id = db.add_audit(
            user_id=user_id,
            terminal_id=req.terminal_id,
            source="web",
            success=True,
            face_similarity=similarity,
            face_liveness_status="passed",
            face_liveness_reason="ok",
            anti_spoof_risk=anti_spoof_risk,
            issued_token_id=uuid.uuid4().hex,
            state=req.state,
        )
        return {
            "authenticated": True,
            "token": token,
            "user": user,
            "face": {"binding": binding, "face_api": face_result},
            "audit_id": audit_id,
        }

    @app.get("/api/auth/me")
    def auth_me(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise_business_error("TOKEN_INVALID")
        payload = verify_demo_token(authorization.split(" ", 1)[1], settings.token_secret)
        user = db.require_active_user(payload["user_id"])
        return {"authenticated": True, "user": user}

    @app.post("/api/terminal/login-events")
    def terminal_login_event(req: TerminalLoginEventReq):
        existing = db.get_audit_by_terminal_event_id(req.event_id)
        if existing:
            return {
                "accepted": False,
                "duplicate": True,
                "user": None,
                "failure_reason": "DUPLICATE_TERMINAL_EVENT",
                "audit_id": existing["id"],
            }
        user_id = str(req.matched_user_id)
        user = db.get_user(user_id)
        failure_reason = None
        accepted = True
        if not isinstance(req.face_api_result, dict) or not req.face_api_result:
            failure_reason = "FACE_API_LOGIN_REJECTED"
            accepted = False
        else:
            recognized_delta = time.time() - float(req.recognized_at_epoch)
            if not math.isfinite(float(req.recognized_at_epoch)) or recognized_delta < -5:
                failure_reason = "TERMINAL_EVENT_TIME_INVALID"
                accepted = False
            elif recognized_delta > 120:
                failure_reason = "TERMINAL_EVENT_EXPIRED"
                accepted = False
            else:
                result_failure = _validate_face_login_result(req.face_api_result, expected_user_id=user_id)
                if result_failure:
                    failure_reason = result_failure
                    accepted = False
        if accepted:
            if not user:
                failure_reason = "BUSINESS_USER_NOT_FOUND"
                accepted = False
            elif user["status"] != "active":
                failure_reason = "USER_DISABLED"
                accepted = False
        if accepted:
            binding = db.get_active_binding(user_id)
            if not binding:
                failure_reason = "FACE_NOT_BOUND"
                accepted = False
            else:
                binding_failure = _validate_face_login_result(
                    req.face_api_result,
                    expected_user_id=user_id,
                    active_binding=binding,
                )
                if binding_failure:
                    failure_reason = binding_failure
                    accepted = False
        try:
            audit_id = db.add_audit(
                terminal_event_id=req.event_id,
                user_id=user_id,
                terminal_id=req.terminal_id,
                source="terminal",
                success=accepted,
                failure_reason=failure_reason,
                face_similarity=req.similarity,
                anti_spoof_risk=_anti_spoof_risk(req.face_api_result) or None,
                state=req.state,
            )
        except sqlite3.IntegrityError:
            existing = db.get_audit_by_terminal_event_id(req.event_id)
            if not existing:
                raise
            return {
                "accepted": False,
                "duplicate": True,
                "user": None,
                "failure_reason": "DUPLICATE_TERMINAL_EVENT",
                "audit_id": existing["id"],
            }
        return {
            "accepted": accepted,
            "user": user if accepted else None,
            "failure_reason": failure_reason,
            "audit_id": audit_id,
        }

    @app.get("/api/audit/login")
    def list_audit(limit: int = 20, terminal_id: str | None = None, success: bool | None = None):
        items = db.list_audits(limit=limit, terminal_id=terminal_id, success=success)
        return {"items": items, "count": len(items)}

    return app


app = create_app()
