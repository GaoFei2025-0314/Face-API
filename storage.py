"""
人脸库 - SQLite 实现
- 特征向量用 BLOB 存（numpy float32 二进制），比 JSON 数组省 4 倍空间
- 启用 WAL 模式 + 定期 checkpoint，避免长期运行 wal 文件膨胀
- 1:N 检索用 numpy 矩阵化运算
- 路径可通过环境变量 FACE_DB_PATH 配置
"""
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import numpy as np


logger = logging.getLogger("face_api")


class FaceDB:
    def __init__(self, db_path: Optional[str] = None):
        # 优先读环境变量，方便部署时切换路径
        self.db_path = db_path or os.getenv("FACE_DB_PATH", "faces.db")
        # 每个线程独立 connection
        self._local = threading.local()
        self._connections = set()
        self._connections_lock = threading.Lock()
        self._connection_generation = 0
        # 写入计数，每 N 次写入做一次 checkpoint
        self._write_count = 0
        self._checkpoint_threshold = 100
        self._search_cache = None
        self._search_cache_dirty = True

        self._init_schema()
        print(f"[FaceDB-SQLite] Ready at {os.path.abspath(self.db_path)}, {self.count()} faces loaded")

    # ---------- 连接管理（线程安全）----------
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        conn_generation = getattr(self._local, "conn_generation", None)
        if conn is not None and conn_generation != self._connection_generation:
            self._local.conn = None
            self._local.conn_generation = None
            conn = None
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # WAL 模式：多读单写并发友好
            conn.execute("PRAGMA journal_mode=WAL")
            # 同步等级 NORMAL：性能与安全的平衡（FULL 太慢，OFF 不安全）
            conn.execute("PRAGMA synchronous=NORMAL")
            # 缓存提到 64MB（你有 128GB 内存，绰绰有余）
            conn.execute("PRAGMA cache_size=-65536")
            with self._connections_lock:
                self._connections.add(conn)
                conn_generation = self._connection_generation
            self._local.conn = conn
            self._local.conn_generation = conn_generation
        return conn

    # ---------- 表结构 ----------
    def _init_schema(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS faces (
                    id          TEXT PRIMARY KEY,
                    user_id     INTEGER,
                    username    TEXT NOT NULL,
                    embedding   BLOB NOT NULL,
                    metadata    TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS face_login_audit (
                    id              TEXT PRIMARY KEY,
                    success         INTEGER NOT NULL DEFAULT 0,
                    matched_user_id INTEGER,
                    matched_username TEXT,
                    similarity      REAL,
                    threshold       REAL,
                    failure_reason  TEXT,
                    terminal_id     TEXT,
                    state           TEXT,
                    elapsed_ms      REAL,
                    liveness_status TEXT,
                    liveness_reason TEXT,
                    quality_metrics TEXT,
                    anti_spoof_risk TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS liveness_challenges (
                    id                    TEXT PRIMARY KEY,
                    purpose               TEXT NOT NULL,
                    terminal_id           TEXT NOT NULL,
                    action                TEXT NOT NULL,
                    status                TEXT NOT NULL,
                    result_reason         TEXT,
                    face_embedding        BLOB,
                    anti_spoof_risk       TEXT,
                    risk_retry_token_hash TEXT,
                    risk_retry_group_id   TEXT,
                    risk_retry_expires_at REAL,
                    risk_retry_used_at    REAL,
                    risk_retry_count      INTEGER NOT NULL DEFAULT 0,
                    action_window_seconds INTEGER NOT NULL,
                    created_at_epoch      REAL,
                    expires_at            REAL NOT NULL,
                    used_at               REAL,
                    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_face_login_audit_created_at ON face_login_audit(created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_face_login_audit_success ON face_login_audit(success)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_liveness_challenges_expires_at ON liveness_challenges(expires_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_liveness_challenges_terminal ON liveness_challenges(terminal_id)")
            columns = {row[1] for row in c.execute("PRAGMA table_info(faces)")}
            if "name" in columns and "username" not in columns:
                c.execute("ALTER TABLE faces RENAME COLUMN name TO username")
                columns = {row[1] for row in c.execute("PRAGMA table_info(faces)")}
            elif "name" in columns and "username" in columns:
                c.execute("""
                    UPDATE faces
                    SET username = name
                    WHERE username IS NULL OR TRIM(username) = ''
                """)
            if "user_id" not in columns:
                c.execute("ALTER TABLE faces ADD COLUMN user_id INTEGER")
            audit_columns = {row[1] for row in c.execute("PRAGMA table_info(face_login_audit)")}
            if "liveness_status" not in audit_columns:
                c.execute("ALTER TABLE face_login_audit ADD COLUMN liveness_status TEXT")
            if "liveness_reason" not in audit_columns:
                c.execute("ALTER TABLE face_login_audit ADD COLUMN liveness_reason TEXT")
            if "quality_metrics" not in audit_columns:
                c.execute("ALTER TABLE face_login_audit ADD COLUMN quality_metrics TEXT")
            if "anti_spoof_risk" not in audit_columns:
                c.execute("ALTER TABLE face_login_audit ADD COLUMN anti_spoof_risk TEXT")
            challenge_columns = {row[1] for row in c.execute("PRAGMA table_info(liveness_challenges)")}
            if "face_embedding" not in challenge_columns:
                c.execute("ALTER TABLE liveness_challenges ADD COLUMN face_embedding BLOB")
            if "created_at_epoch" not in challenge_columns:
                c.execute("ALTER TABLE liveness_challenges ADD COLUMN created_at_epoch REAL")
            if "anti_spoof_risk" not in challenge_columns:
                c.execute("ALTER TABLE liveness_challenges ADD COLUMN anti_spoof_risk TEXT")
            if "risk_retry_token_hash" not in challenge_columns:
                c.execute("ALTER TABLE liveness_challenges ADD COLUMN risk_retry_token_hash TEXT")
            if "risk_retry_group_id" not in challenge_columns:
                c.execute("ALTER TABLE liveness_challenges ADD COLUMN risk_retry_group_id TEXT")
            if "risk_retry_expires_at" not in challenge_columns:
                c.execute("ALTER TABLE liveness_challenges ADD COLUMN risk_retry_expires_at REAL")
            if "risk_retry_used_at" not in challenge_columns:
                c.execute("ALTER TABLE liveness_challenges ADD COLUMN risk_retry_used_at REAL")
            if "risk_retry_count" not in challenge_columns:
                c.execute("ALTER TABLE liveness_challenges ADD COLUMN risk_retry_count INTEGER NOT NULL DEFAULT 0")
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_liveness_challenges_retry_token_hash "
                "ON liveness_challenges(risk_retry_token_hash)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_liveness_challenges_retry_expires "
                "ON liveness_challenges(risk_retry_expires_at, risk_retry_used_at)"
            )
            c.execute("DROP INDEX IF EXISTS idx_name")
            c.execute("CREATE INDEX IF NOT EXISTS idx_username ON faces(username)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON faces(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON faces(created_at)")

    @staticmethod
    def _json_dumps(value: Optional[dict]) -> Optional[str]:
        return json.dumps(value, ensure_ascii=False) if value is not None else None

    @staticmethod
    def _json_loads(value: Optional[str]) -> Optional[dict]:
        if not value:
            return None
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            logger.error("SQLite JSON field decode failed", exc_info=True)
            return None

    def _mark_search_cache_dirty(self):
        self._search_cache_dirty = True

    def invalidate_search_cache(self):
        self._search_cache = None
        self._mark_search_cache_dirty()

    # ---------- 序列化辅助 ----------
    @staticmethod
    def _emb_to_blob(embedding) -> bytes:
        return np.asarray(embedding, dtype=np.float32).tobytes()

    @staticmethod
    def _blob_to_emb(blob: bytes) -> np.ndarray:
        return np.frombuffer(blob, dtype=np.float32)

    def _maybe_checkpoint(self):
        """达到阈值时触发 WAL checkpoint，避免 -wal 文件膨胀"""
        self._write_count += 1
        if self._write_count >= self._checkpoint_threshold:
            try:
                self._conn().execute("PRAGMA wal_checkpoint(PASSIVE)")
            except Exception:
                logger.exception("WAL checkpoint failed")
            self._write_count = 0

    # ---------- CRUD ----------
    def add(
        self,
        username: str,
        embedding: list,
        metadata: Optional[dict] = None,
        user_id: Optional[int] = None,
    ) -> str:
        face_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO faces (id, user_id, username, embedding, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    face_id,
                    user_id,
                    username,
                    self._emb_to_blob(embedding),
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
        self._maybe_checkpoint()
        self._mark_search_cache_dirty()
        return face_id

    def remove(self, face_id: str) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM faces WHERE id = ?", (face_id,))
            removed = cur.rowcount > 0
        if removed:
            self._maybe_checkpoint()
            self._mark_search_cache_dirty()
        return removed

    def remove_by_user_id(self, user_id: int) -> int:
        with self._conn() as c:
            cur = c.execute("DELETE FROM faces WHERE user_id = ?", (user_id,))
            removed = cur.rowcount
        if removed:
            self._maybe_checkpoint()
            self._mark_search_cache_dirty()
        return removed

    def list_all(self) -> list:
        rows = self._conn().execute(
            """
            SELECT id, user_id, username, metadata, created_at
            FROM faces
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "username": r["username"],
                "metadata": json.loads(r["metadata"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def list_by_user_id(self, user_id: int) -> list:
        rows = self._conn().execute(
            """
            SELECT id, user_id, username, metadata, created_at
            FROM faces
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "username": r["username"],
                "metadata": json.loads(r["metadata"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def count(self) -> int:
        return self._conn().execute("SELECT COUNT(*) FROM faces").fetchone()[0]

    # ---------- 1:N 搜索 ----------
    def _load_search_cache(self):
        if self._search_cache is not None and not self._search_cache_dirty:
            return self._search_cache

        rows = self._conn().execute(
            "SELECT id, user_id, username, embedding, metadata FROM faces"
        ).fetchall()

        if not rows:
            self._search_cache = {
                "ids": [],
                "user_ids": [],
                "usernames": [],
                "metas": [],
                "emb_matrix": None,
            }
            self._search_cache_dirty = False
            return self._search_cache

        emb_matrix = np.stack([self._blob_to_emb(r["embedding"]) for r in rows])
        emb_matrix = emb_matrix / (np.linalg.norm(emb_matrix, axis=1, keepdims=True) + 1e-8)
        self._search_cache = {
            "ids": [r["id"] for r in rows],
            "user_ids": [r["user_id"] for r in rows],
            "usernames": [r["username"] for r in rows],
            "metas": [json.loads(r["metadata"] or "{}") for r in rows],
            "emb_matrix": emb_matrix,
        }
        self._search_cache_dirty = False
        return self._search_cache

    def get_search_cache_status(self) -> dict:
        cache = self._load_search_cache()
        return {
            "ready": cache["emb_matrix"] is not None or len(cache["ids"]) == 0,
            "dirty": self._search_cache_dirty,
            "record_count": len(cache["ids"]),
            "mode": "exact",
            "target_record_count": 50000,
            "target_latency_ms": 1000,
        }

    def get_search_cache_summary(self) -> dict:
        record_count = self.count()
        cache = self._search_cache
        cache_count = len(cache["ids"]) if cache else 0
        cache_ready = cache is not None and not self._search_cache_dirty and cache_count == record_count
        return {
            "ready": record_count == 0 or cache_ready,
            "dirty": self._search_cache_dirty,
            "record_count": record_count,
            "mode": "exact",
            "target_record_count": 50000,
            "target_latency_ms": 1000,
        }

    def get_search_index_status(self) -> dict:
        cache = self._load_search_cache()
        return {
            "enabled": False,
            "mode": "exact",
            "record_count": len(cache["ids"]),
            "fresh": True,
            "rebuild_required": False,
            "fallback": {
                "enabled": True,
                "mode": "exact",
                "reason": "默认保留 SQLite + NumPy 精确搜索，index 仅在 benchmark 证明必要后评估",
            },
            "enter_conditions": [
                "5 万人脸 benchmark 的 search 或 login P95 连续超过 1000ms",
                "优化图片尺寸、缓存预热和硬件配置后仍不达标",
                "index 结果必须与精确搜索抽样对比，top-1 一致率达到验收阈值",
                "新增、删除和恢复数据库后必须能标记 index 新鲜度或回退精确搜索",
            ],
            "candidate_backends": ["faiss-cpu", "faiss-gpu"],
        }

    def get_search_benchmark_summary(self) -> dict:
        cache = self._load_search_cache()
        return {
            "mode": "exact",
            "record_count": len(cache["ids"]),
            "target_record_count": 50000,
            "target_latency_ms": 1000,
            "approximate_search_enabled": False,
            "metrics": ["avg_ms", "p95_ms", "min_ms", "max_ms", "failure_count", "failure_reasons"],
            "report_format": {
                "version": "1.0",
                "record_count": "int",
                "target_record_count": "int",
                "runtime": {
                    "python": "str",
                    "platform": "str",
                    "device": "CPU|GPU",
                    "providers": "list[str]",
                    "model": "str",
                    "db_path": "str",
                },
                "search": {
                    "samples": "int",
                    "avg_ms": "float",
                    "p95_ms": "float",
                    "failure_count": "int",
                    "failure_reasons": "dict[str,int]",
                },
                "conclusion": "str",
            },
            "index_decision": self.get_search_index_status(),
            "recommendation": "当前使用精确搜索；仅当 5 万人脸记录下超过 1 秒目标时，再评估近似搜索",
        }

    def search(self, query_embedding: list, top_k: int = 5, threshold: float = 0.5) -> list:
        """
        线性扫描全表 + 矩阵化余弦相似度
        - 1k 人：~3ms
        - 1w 人：~20ms
        - 10w 人：~200ms（建议接 Faiss）
        """
        cache = self._load_search_cache()
        if not cache["ids"]:
            return []

        q = np.asarray(query_embedding, dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-8)

        # 一次矩阵乘法搞定所有相似度
        sims = cache["emb_matrix"] @ q

        # 过滤 + 排序 + 取 top_k
        mask = sims >= threshold
        candidates = [
            (sims[i], cache["ids"][i], cache["user_ids"][i], cache["usernames"][i], cache["metas"][i])
            for i in np.where(mask)[0]
        ]
        candidates.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "id": cid,
                "user_id": user_id,
                "username": username,
                "similarity": float(sim),
                "metadata": cmeta,
            }
            for sim, cid, user_id, username, cmeta in candidates[:top_k]
        ]

    # ---------- 活体 challenge ----------
    def add_liveness_challenge(
        self,
        *,
        purpose: str,
        terminal_id: str,
        action: str,
        expires_at: float,
        action_window_seconds: int,
    ) -> str:
        challenge_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO liveness_challenges (
                    id, purpose, terminal_id, action, status,
                    action_window_seconds, created_at_epoch, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    challenge_id,
                    purpose,
                    terminal_id,
                    action,
                    "pending",
                    action_window_seconds,
                    time.time(),
                    expires_at,
                ),
            )
        return challenge_id

    def get_liveness_challenge(self, challenge_id: str) -> Optional[dict]:
        row = self._conn().execute(
            """
            SELECT id, purpose, terminal_id, action, status, result_reason,
                   face_embedding, anti_spoof_risk, action_window_seconds, created_at_epoch, expires_at, used_at, created_at
            FROM liveness_challenges
            WHERE id = ?
            """,
            (challenge_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "purpose": row["purpose"],
            "terminal_id": row["terminal_id"],
            "action": row["action"],
            "status": row["status"],
            "result_reason": row["result_reason"],
            "face_embedding": (
                np.frombuffer(row["face_embedding"], dtype=np.float32).tolist()
                if row["face_embedding"] is not None
                else None
            ),
            "anti_spoof_risk": self._json_loads(row["anti_spoof_risk"]),
            "action_window_seconds": row["action_window_seconds"],
            "created_at_epoch": row["created_at_epoch"],
            "expires_at": row["expires_at"],
            "used_at": row["used_at"],
            "created_at": row["created_at"],
        }

    def mark_liveness_challenge_result(
        self,
        challenge_id: str,
        *,
        passed: bool,
        result_reason: str,
        face_embedding=None,
        anti_spoof_risk: Optional[dict] = None,
    ) -> bool:
        status = "passed" if passed else "failed"
        embedding_blob = None
        if face_embedding is not None:
            embedding_blob = np.asarray(face_embedding, dtype=np.float32).tobytes()
        anti_spoof_risk_text = self._json_dumps(anti_spoof_risk)
        with self._conn() as c:
            cur = c.execute(
                """
                UPDATE liveness_challenges
                SET status = ?, result_reason = ?, face_embedding = ?, anti_spoof_risk = ?
                WHERE id = ? AND status = 'pending'
                """,
                (status, result_reason, embedding_blob, anti_spoof_risk_text, challenge_id),
            )
            return cur.rowcount > 0

    def consume_liveness_challenge(
        self,
        *,
        challenge_id: str,
        purpose: str,
        terminal_id: str,
        now: float,
    ) -> tuple[bool, str, Optional[dict]]:
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute(
                """
                SELECT id, purpose, terminal_id, action, status, result_reason,
                       face_embedding, anti_spoof_risk, action_window_seconds, created_at_epoch, expires_at, used_at, created_at
                FROM liveness_challenges
                WHERE id = ?
                """,
                (challenge_id,),
            ).fetchone()
            if not row:
                return False, "not_found", None
            challenge = {
                "id": row["id"],
                "purpose": row["purpose"],
                "terminal_id": row["terminal_id"],
                "action": row["action"],
                "status": row["status"],
                "result_reason": row["result_reason"],
                "face_embedding": (
                    np.frombuffer(row["face_embedding"], dtype=np.float32).tolist()
                    if row["face_embedding"] is not None
                    else None
                ),
                "anti_spoof_risk": self._json_loads(row["anti_spoof_risk"]),
                "action_window_seconds": row["action_window_seconds"],
                "created_at_epoch": row["created_at_epoch"],
                "expires_at": row["expires_at"],
                "used_at": row["used_at"],
                "created_at": row["created_at"],
            }
            if row["used_at"] is not None or row["status"] == "used":
                return False, "already_used", challenge
            if now > float(row["expires_at"]):
                c.execute(
                    "UPDATE liveness_challenges SET status = 'expired' WHERE id = ? AND status != 'used'",
                    (challenge_id,),
                )
                return False, "expired", challenge
            if row["purpose"] != purpose:
                return False, "purpose_mismatch", challenge
            if row["terminal_id"] != terminal_id:
                return False, "terminal_mismatch", challenge
            if row["status"] != "passed":
                return False, "not_passed", challenge
            cur = c.execute(
                """
                UPDATE liveness_challenges
                SET status = 'used', used_at = ?
                WHERE id = ?
                  AND purpose = ?
                  AND terminal_id = ?
                  AND status = 'passed'
                  AND used_at IS NULL
                  AND expires_at >= ?
                """,
                (now, challenge_id, purpose, terminal_id, now),
            )
            if cur.rowcount != 1:
                return False, "already_used", challenge
            challenge["status"] = "used"
            challenge["used_at"] = now
            return True, "ok", challenge

    def add_risk_retry_token(
        self,
        *,
        token_hash: str,
        terminal_id: str,
        retry_group_id: str,
        expires_at: float,
        now: Optional[float] = None,
    ) -> bool:
        with self._conn() as c:
            cur = c.execute(
                """
                UPDATE liveness_challenges
                SET risk_retry_token_hash = ?,
                    risk_retry_group_id = ?,
                    risk_retry_expires_at = ?,
                    risk_retry_used_at = NULL,
                    risk_retry_count = 1
                WHERE id = ?
                  AND terminal_id = ?
                """,
                (token_hash, retry_group_id, expires_at, retry_group_id, terminal_id),
            )
            stored = cur.rowcount == 1
        if stored:
            self._maybe_checkpoint()
        return stored

    def consume_risk_retry_token(
        self,
        *,
        token_hash: str,
        terminal_id: str,
        now: float,
    ) -> tuple[bool, str, Optional[dict]]:
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute(
                """
                SELECT id, terminal_id, risk_retry_group_id, risk_retry_expires_at,
                       risk_retry_used_at, risk_retry_count
                FROM liveness_challenges
                WHERE risk_retry_token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
            if not row:
                return False, "not_found", None
            token = {
                "challenge_id": row["id"],
                "terminal_id": row["terminal_id"],
                "retry_group_id": row["risk_retry_group_id"],
                "expires_at": row["risk_retry_expires_at"],
                "used_at": row["risk_retry_used_at"],
                "retry_count": row["risk_retry_count"],
            }
            if row["terminal_id"] != terminal_id:
                return False, "terminal_mismatch", token
            if row["risk_retry_used_at"] is not None:
                return False, "already_used", token
            if row["risk_retry_expires_at"] is None or now > float(row["risk_retry_expires_at"]):
                return False, "expired", token
            cur = c.execute(
                """
                UPDATE liveness_challenges
                SET risk_retry_used_at = ?
                WHERE risk_retry_token_hash = ?
                  AND terminal_id = ?
                  AND risk_retry_used_at IS NULL
                  AND risk_retry_expires_at >= ?
                """,
                (now, token_hash, terminal_id, now),
            )
            if cur.rowcount != 1:
                return False, "already_used", token
            token["used_at"] = now
            return True, "ok", token

    def backup_to(self, target_path: str | Path) -> str:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        source = self._conn()
        with sqlite3.connect(target) as dest:
            source.backup(dest)
        return str(target)

    def add_login_audit(
        self,
        *,
        success: bool,
        matched_user_id: Optional[int] = None,
        matched_username: Optional[str] = None,
        similarity: Optional[float] = None,
        threshold: Optional[float] = None,
        failure_reason: Optional[str] = None,
        terminal_id: Optional[str] = None,
        state: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
        liveness_status: Optional[str] = None,
        liveness_reason: Optional[str] = None,
        quality_metrics: Optional[dict] = None,
        anti_spoof_risk: Optional[dict] = None,
    ) -> str:
        audit_id = str(uuid.uuid4())
        quality_metrics_text = self._json_dumps(quality_metrics)
        anti_spoof_risk_text = self._json_dumps(anti_spoof_risk)
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO face_login_audit (
                    id, success, matched_user_id, matched_username, similarity,
                    threshold, failure_reason, terminal_id, state, elapsed_ms,
                    liveness_status, liveness_reason, quality_metrics, anti_spoof_risk
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    1 if success else 0,
                    matched_user_id,
                    matched_username,
                    similarity,
                    threshold,
                    failure_reason,
                    terminal_id,
                    state,
                    elapsed_ms,
                    liveness_status,
                    liveness_reason,
                    quality_metrics_text,
                    anti_spoof_risk_text,
                ),
            )
        self._maybe_checkpoint()
        return audit_id

    def list_login_audits(self, limit: int = 20, success: Optional[bool] = None, terminal_id: Optional[str] = None) -> list:
        safe_limit = min(max(int(limit), 1), 100)
        where = []
        params = []
        if success is not None:
            where.append("success = ?")
            params.append(1 if success else 0)
        if terminal_id:
            where.append("terminal_id = ?")
            params.append(terminal_id)
        # 安全约束：where 只能追加硬编码的 "column = ?" 片段；外部输入必须通过 params 参数化传入。
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = self._conn().execute(
            f"""
            SELECT id, success, matched_user_id, matched_username, similarity,
                   threshold, failure_reason, terminal_id, state, elapsed_ms,
                   liveness_status, liveness_reason, quality_metrics, anti_spoof_risk, created_at
            FROM face_login_audit
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (*params, safe_limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "success": bool(r["success"]),
                "matched_user_id": r["matched_user_id"],
                "matched_username": r["matched_username"],
                "similarity": r["similarity"],
                "threshold": r["threshold"],
                "failure_reason": r["failure_reason"],
                "terminal_id": r["terminal_id"],
                "state": r["state"],
                "elapsed_ms": r["elapsed_ms"],
                "liveness_status": r["liveness_status"],
                "liveness_reason": r["liveness_reason"],
                "quality_metrics": self._json_loads(r["quality_metrics"]),
                "anti_spoof_risk": self._json_loads(r["anti_spoof_risk"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def get_login_audit_summary(self, limit: int = 100, terminal_id: Optional[str] = None) -> dict:
        items = self.list_login_audits(limit, terminal_id=terminal_id)
        total = len(items)
        success_count = sum(1 for item in items if item["success"])
        failure_count = total - success_count
        return {
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / total if total else 0,
        }

    def close(self):
        conn = getattr(self._local, "conn", None)
        if conn:
            with self._connections_lock:
                self._connections.discard(conn)
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                logger.exception("WAL checkpoint failed while closing connection")
            try:
                conn.close()
            except Exception:
                logger.exception("SQLite connection close failed")
            self._local.conn = None
            self._local.conn_generation = None

    def close_all_connections(self):
        with self._connections_lock:
            self._connection_generation += 1
            connections = list(self._connections)
            self._connections.clear()
            for conn in connections:
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception:
                    logger.exception("WAL checkpoint failed while closing connection")
                try:
                    conn.close()
                except Exception:
                    logger.exception("SQLite connection close failed")
        self._local.conn = None
        self._local.conn_generation = None
