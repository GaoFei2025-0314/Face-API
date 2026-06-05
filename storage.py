"""
人脸库 - SQLite 实现
- 特征向量用 BLOB 存（numpy float32 二进制），比 JSON 数组省 4 倍空间
- 启用 WAL 模式 + 定期 checkpoint，避免长期运行 wal 文件膨胀
- 1:N 检索用 numpy 矩阵化运算
- 路径可通过环境变量 FACE_DB_PATH 配置
"""
import json
import os
import sqlite3
import threading
import uuid
from typing import Optional

import numpy as np


class FaceDB:
    def __init__(self, db_path: str = None):
        # 优先读环境变量，方便部署时切换路径
        self.db_path = db_path or os.getenv("FACE_DB_PATH", "faces.db")
        # 每个线程独立 connection
        self._local = threading.local()
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
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # WAL 模式：多读单写并发友好
            conn.execute("PRAGMA journal_mode=WAL")
            # 同步等级 NORMAL：性能与安全的平衡（FULL 太慢，OFF 不安全）
            conn.execute("PRAGMA synchronous=NORMAL")
            # 缓存提到 64MB（你有 128GB 内存，绰绰有余）
            conn.execute("PRAGMA cache_size=-65536")
            self._local.conn = conn
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
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_face_login_audit_created_at ON face_login_audit(created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_face_login_audit_success ON face_login_audit(success)")
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
            c.execute("DROP INDEX IF EXISTS idx_name")
            c.execute("CREATE INDEX IF NOT EXISTS idx_username ON faces(username)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON faces(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON faces(created_at)")

    def _mark_search_cache_dirty(self):
        self._search_cache_dirty = True

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
                pass
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
    ) -> str:
        audit_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO face_login_audit (
                    id, success, matched_user_id, matched_username, similarity,
                    threshold, failure_reason, terminal_id, state, elapsed_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = self._conn().execute(
            f"""
            SELECT id, success, matched_user_id, matched_username, similarity,
                   threshold, failure_reason, terminal_id, state, elapsed_ms, created_at
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
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            conn.close()
            self._local.conn = None
