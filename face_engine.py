"""
InsightFace 引擎封装
- 优先使用 GPU (CUDA)，不可用时回落到 CPU
- 默认 buffalo_l 模型（检测 + 识别 + 关键点 + 性别年龄）
- 针对 GTX 1080 Ti 11GB 显存优化，det_size=640 是精度/速度最优点
"""
import os
import numpy as np
from insightface.app import FaceAnalysis
import onnxruntime as ort


class FaceEngine:
    def __init__(
        self,
        model_name: str = None,
        det_size: tuple = None,
        force_cpu: bool = False,
        use_gpu: bool = False,
    ):
        # 支持环境变量配置（方便部署时调整）
        model_name = model_name or os.getenv("FACE_MODEL", "buffalo_l")
        if det_size is None:
            size = int(os.getenv("FACE_DET_SIZE", "640"))
            det_size = (size, size)

        # 检测可用的推理后端
        available = ort.get_available_providers()
        if use_gpu and "CUDAExecutionProvider" in available and not force_cpu:
            providers = [
                ("CUDAExecutionProvider", {
                    "device_id": 0,
                    "arena_extend_strategy": "kNextPowerOfTwo",
                    # 1080 Ti 有 11GB，给 ONNX 用 4GB 足够 buffalo_l 运行
                    "gpu_mem_limit": 4 * 1024 * 1024 * 1024,
                    "cudnn_conv_algo_search": "EXHAUSTIVE",
                    "do_copy_in_default_stream": True,
                }),
                "CPUExecutionProvider",
            ]
            ctx_id = 0
            self.device = "GPU (CUDA)"
        else:
            providers = ["CPUExecutionProvider"]
            ctx_id = -1
            self.device = "CPU"

        self.model_name = model_name
        self.det_size = det_size
        self.force_cpu = force_cpu
        self.use_gpu = use_gpu
        self.available_providers = available
        self.selected_provider_names = [p if isinstance(p, str) else p[0] for p in providers]

        print(f"[FaceEngine] Available providers: {available}")
        print(f"[FaceEngine] Using providers: {self.selected_provider_names}")
        print(f"[FaceEngine] Model: {model_name}, det_size: {det_size}")

        try:
            self.app = FaceAnalysis(name=model_name, providers=providers)
            self.app.prepare(ctx_id=ctx_id, det_size=det_size)
        except Exception as exc:
            raise RuntimeError(
                "FaceEngine initialization failed: "
                f"model={model_name}, det_size={det_size}, force_cpu={force_cpu}, use_gpu={use_gpu}, "
                f"available_providers={available}, selected_providers={self.selected_provider_names}. "
                f"Original error: {exc}"
            ) from exc
        print(f"[FaceEngine] Ready. Running on {self.device}")

    def analyze(self, image: np.ndarray):
        """检测图像中所有人脸，返回 bbox、关键点、512 维特征、属性等"""
        faces = self.app.get(image)
        results = []
        for face in faces:
            results.append({
                "bbox": [float(x) for x in face.bbox.tolist()],
                "det_score": float(face.det_score),
                "landmarks": face.kps.tolist() if face.kps is not None else None,
                "embedding": face.embedding.tolist(),
                "gender": "M" if int(face.gender) == 1 else "F",
                "age": int(face.age),
            })
        return results

    @staticmethod
    def cosine_similarity(emb1, emb2) -> float:
        """计算两个特征向量的余弦相似度，取值 [-1, 1]，一般 >0.5 视为同人"""
        a = np.asarray(emb1, dtype=np.float32)
        b = np.asarray(emb2, dtype=np.float32)
        a = a / (np.linalg.norm(a) + 1e-8)
        b = b / (np.linalg.norm(b) + 1e-8)
        return float(np.dot(a, b))
