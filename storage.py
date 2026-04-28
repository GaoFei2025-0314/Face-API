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
                    name        TEXT NOT NULL,
                    embedding   BLOB NOT NULL,
                    metadata    TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_name ON faces(name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON faces(created_at)")

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
    def add(self, name: str, embedding: list, metadata: Optional[dict] = None) -> str:
        face_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                "INSERT INTO faces (id, name, embedding, metadata) VALUES (?, ?, ?, ?)",
                (
                    face_id,
                    name,
                    self._emb_to_blob(embedding),
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
        self._maybe_checkpoint()
        return face_id

    def remove(self, face_id: str) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM faces WHERE id = ?", (face_id,))
            removed = cur.rowcount > 0
        if removed:
            self._maybe_checkpoint()
        return removed

    def list_all(self) -> list:
        rows = self._conn().execute(
            "SELECT id, name, metadata, created_at FROM faces ORDER BY created_at DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "metadata": json.loads(r["metadata"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def count(self) -> int:
        return self._conn().execute("SELECT COUNT(*) FROM faces").fetchone()[0]

    # ---------- 1:N 搜索 ----------
    def search(self, query_embedding: list, top_k: int = 5, threshold: float = 0.5) -> list:
        """
        线性扫描全表 + 矩阵化余弦相似度
        - 1k 人：~3ms
        - 1w 人：~20ms
        - 10w 人：~200ms（建议接 Faiss）
        """
        rows = self._conn().execute(
            "SELECT id, name, embedding, metadata FROM faces"
        ).fetchall()

        if not rows:
            return []

        ids = [r["id"] for r in rows]
        names = [r["name"] for r in rows]
        metas = [json.loads(r["metadata"] or "{}") for r in rows]
        emb_matrix = np.stack([self._blob_to_emb(r["embedding"]) for r in rows])

        # 归一化
        emb_matrix = emb_matrix / (np.linalg.norm(emb_matrix, axis=1, keepdims=True) + 1e-8)
        q = np.asarray(query_embedding, dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-8)

        # 一次矩阵乘法搞定所有相似度
        sims = emb_matrix @ q

        # 过滤 + 排序 + 取 top_k
        mask = sims >= threshold
        candidates = [
            (sims[i], ids[i], names[i], metas[i])
            for i in np.where(mask)[0]
        ]
        candidates.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "id": cid,
                "name": cname,
                "similarity": float(sim),
                "metadata": cmeta,
            }
            for sim, cid, cname, cmeta in candidates[:top_k]
        ]

    def close(self):
        conn = getattr(self._local, "conn", None)
        if conn:
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            conn.close()
            self._local.conn = None
