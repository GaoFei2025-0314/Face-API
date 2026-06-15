import json
from urllib import error, request

from .errors import raise_business_error


class FaceApiClient:
    def __init__(self, base_url, api_key="", timeout=30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method, path, payload=None):
        body = None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw or "{}")
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw).get("detail", {})
            except json.JSONDecodeError:
                detail = {}
            if exc.code == 401:
                raise_business_error("FACE_API_AUTH_FAILED")
            if isinstance(detail, dict) and detail.get("code"):
                raise_business_error(
                    detail["code"],
                    message=detail.get("message"),
                    reason=detail.get("reason"),
                    status_code=exc.code,
                )
            raise_business_error("FACE_API_UNAVAILABLE")
        except OSError:
            raise_business_error("FACE_API_UNAVAILABLE")

    def register_face(self, payload):
        return self._request("POST", "/faces/register", payload)

    def delete_face(self, face_id):
        return self._request("DELETE", f"/faces/{face_id}")

    def create_liveness_challenge(self, payload):
        return self._request("POST", "/liveness/challenges", payload)

    def submit_liveness_challenge(self, payload):
        return self._request("POST", "/liveness/challenges/submit", payload)

    def face_login(self, payload):
        return self._request("POST", "/auth/face-login", payload)
