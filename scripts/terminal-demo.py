import argparse
import base64
import json
import sys
import time
from pathlib import Path
from urllib import error, request


def post_json(url, payload, api_key=None, timeout=30):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def format_error(exc):
    if isinstance(exc, error.HTTPError):
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError:
            parsed = {}
        detail = parsed.get("detail") if isinstance(parsed, dict) else None
        return {
            "type": "http_error",
            "status": exc.code,
            "message": str(exc),
            "detail": detail or parsed or raw,
        }
    return str(exc)


def format_anti_spoof_risk(risk):
    if not isinstance(risk, dict):
        return "防翻拍风险：未返回"
    label = {"low": "低", "medium": "中", "high": "高"}.get(risk.get("level"), risk.get("level") or "未知")
    message = risk.get("message") or "请按提示重新采集"
    reasons = risk.get("reasons") if isinstance(risk.get("reasons"), list) else []
    reason_text = f"（{', '.join(str(reason) for reason in reasons)}）" if reasons else ""
    return f"防翻拍风险：{label}，{message}{reason_text}"


def sanitize_result(value):
    if isinstance(value, list):
        return [sanitize_result(item) for item in value]
    if not isinstance(value, dict):
        return value
    clean = {}
    for key, item in value.items():
        if key == "metrics":
            continue
        clean[key] = sanitize_result(item)
    if isinstance(clean.get("anti_spoof_risk"), dict):
        clean["anti_spoof_summary"] = format_anti_spoof_risk(clean["anti_spoof_risk"])
    return clean


def image_to_data_url(path):
    data = Path(path).read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


def frame_to_data_url(frame):
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("摄像头采集需要 OpenCV，请先确认当前 Python 环境已安装 opencv-python") from exc

    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("摄像头画面编码失败")
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


def capture_camera_frames(camera_index, count, interval_ms):
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("摄像头采集需要 OpenCV，请先确认当前 Python 环境已安装 opencv-python") from exc

    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 index={camera_index}")
    frames = []
    try:
        for _ in range(count):
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("摄像头采集失败")
            frames.append(frame_to_data_url(frame))
            time.sleep(max(0, interval_ms) / 1000)
        ok, login_frame = cap.read()
        if not ok:
            raise RuntimeError("登录图片采集失败")
        return frames, frame_to_data_url(login_frame)
    finally:
        cap.release()


def create_liveness_challenge(face_api_url, api_key, terminal_id):
    return post_json(
        face_api_url.rstrip("/") + "/liveness/challenges",
        {"purpose": "login", "terminal_id": terminal_id, "action": "blink"},
        api_key=api_key,
    )


def submit_liveness_challenge(face_api_url, api_key, terminal_id, challenge, frames):
    return post_json(
        face_api_url.rstrip("/") + "/liveness/challenges/submit",
        {
            "challenge_id": challenge["challenge_id"],
            "purpose": challenge.get("purpose", "login"),
            "terminal_id": terminal_id,
            "frames": frames,
        },
        api_key=api_key,
    )


def collect_liveness_frames(args):
    if args.liveness_frame:
        if len(args.liveness_frame) < 10:
            raise RuntimeError("活体帧数量不足：文件模式至少 10 帧，请增加 --liveness-frame 或改用 --camera-index")
        return [image_to_data_url(path) for path in args.liveness_frame], None
    if args.camera_index is not None:
        return capture_camera_frames(
            args.camera_index,
            args.liveness_frame_count,
            args.liveness_frame_interval_ms,
        )
    raise RuntimeError("默认登录需要活体：请提供 --liveness-frame 或 --camera-index，或传入已有 --challenge-id")


def build_parser():
    parser = argparse.ArgumentParser(description="受控终端 demo：完成活体、调用 face_api 后上报 business-demo")
    parser.add_argument("--face-api-url", default="http://localhost:8000")
    parser.add_argument("--business-url", default="http://localhost:8010")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--terminal-id", required=True)
    parser.add_argument("--image", default=None, help="待识别图片路径；不传时使用 --camera-index 采集登录图片")
    parser.add_argument("--camera-index", type=int, default=None, help="从本机摄像头采集活体帧和登录图片")
    parser.add_argument(
        "--liveness-frame",
        action="append",
        default=[],
        help="活体连续帧图片路径，可重复传入；用于无摄像头的脚本验收",
    )
    parser.add_argument("--liveness-frame-count", type=int, default=24)
    parser.add_argument("--liveness-frame-interval-ms", type=int, default=180)
    parser.add_argument("--challenge-id", default=None, help="复用已通过且未消费的 login challenge")
    parser.add_argument("--skip-liveness", action="store_true", help="仅在 face_api 已关闭 login 活体时使用")
    parser.add_argument("--event-id", default=None, help="终端登录事件幂等 ID；不传时自动生成")
    parser.add_argument("--state", default=None)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.image and args.camera_index is None:
        parser.error("--image 或 --camera-index 必须至少提供一个")
    if args.skip_liveness and args.challenge_id:
        parser.error("--skip-liveness 和 --challenge-id 不能同时使用")

    liveness = None
    login_image = image_to_data_url(args.image) if args.image else None
    challenge_id = args.challenge_id
    event_id = args.event_id or f"{args.terminal_id}-{int(time.time() * 1000)}"
    state = args.state or event_id

    try:
        if not challenge_id and not args.skip_liveness:
            frames, camera_login_image = collect_liveness_frames(args)
            if not login_image:
                login_image = camera_login_image
            challenge = create_liveness_challenge(args.face_api_url, args.api_key, args.terminal_id)
            liveness = submit_liveness_challenge(
                args.face_api_url,
                args.api_key,
                args.terminal_id,
                challenge,
                frames,
            )
            if liveness.get("passed") is False:
                print(json.dumps(sanitize_result({"ok": False, "liveness": liveness}), ensure_ascii=False, indent=2))
                return 1
            challenge_id = liveness["challenge_id"]

        face = post_json(
            args.face_api_url.rstrip("/") + "/auth/face-login",
            {
                "image": login_image,
                "terminal_id": args.terminal_id,
                "challenge_id": challenge_id,
                "state": state,
            },
            api_key=args.api_key,
        )
        user_id = str((face.get("match") or {}).get("user_id") or "")
        report = post_json(
            args.business_url.rstrip("/") + "/api/terminal/login-events",
            {
                "event_id": event_id,
                "terminal_id": args.terminal_id,
                "matched_user_id": user_id,
                "similarity": face.get("similarity"),
                "recognized_at_epoch": time.time(),
                "state": state,
                "face_api_result": face,
            },
        )
    except (OSError, RuntimeError, error.HTTPError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": format_error(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            sanitize_result({"ok": True, "liveness": liveness, "face": face, "business": report}),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
