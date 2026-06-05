import importlib
import sys
import types
import unittest


class FaceEngineInitializationTests(unittest.TestCase):
    def setUp(self):
        self._saved_modules = {
            name: sys.modules.get(name)
            for name in ("onnxruntime", "insightface", "insightface.app", "face_engine")
        }

    def tearDown(self):
        for name, module in self._saved_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def load_face_engine_module(self, prepare_error=None, providers=None):
        providers = providers or ["CPUExecutionProvider"]

        fake_onnxruntime = types.ModuleType("onnxruntime")
        fake_onnxruntime.get_available_providers = lambda: providers

        fake_insightface = types.ModuleType("insightface")
        fake_app_module = types.ModuleType("insightface.app")

        class FakeFaceAnalysis:
            def __init__(self, name=None, providers=None):
                self.name = name
                self.providers = providers

            def prepare(self, ctx_id=None, det_size=None):
                if prepare_error:
                    raise prepare_error

            def get(self, image):
                return []

        fake_app_module.FaceAnalysis = FakeFaceAnalysis
        fake_insightface.app = fake_app_module

        sys.modules["onnxruntime"] = fake_onnxruntime
        sys.modules["insightface"] = fake_insightface
        sys.modules["insightface.app"] = fake_app_module
        sys.modules.pop("face_engine", None)

        return importlib.import_module("face_engine")

    def test_engine_defaults_to_cpu_even_when_cuda_is_available(self):
        module = self.load_face_engine_module(providers=["CUDAExecutionProvider", "CPUExecutionProvider"])

        engine = module.FaceEngine(model_name="buffalo_l", det_size=(640, 640))

        self.assertEqual(engine.selected_provider_names, ["CPUExecutionProvider"])
        self.assertEqual(engine.device, "CPU")

    def test_engine_uses_gpu_when_explicitly_allowed(self):
        module = self.load_face_engine_module(providers=["CUDAExecutionProvider", "CPUExecutionProvider"])

        engine = module.FaceEngine(model_name="buffalo_l", det_size=(640, 640), use_gpu=True)

        self.assertEqual(engine.selected_provider_names, ["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(engine.device, "GPU (CUDA)")

    def test_initialization_failure_includes_runtime_context(self):
        module = self.load_face_engine_module(prepare_error=RuntimeError("prepare failed"))

        with self.assertRaises(RuntimeError) as exc_info:
            module.FaceEngine(model_name="buffalo_l", det_size=(640, 640), force_cpu=False)

        text = str(exc_info.exception)
        self.assertIn("FaceEngine initialization failed", text)
        self.assertIn("model=buffalo_l", text)
        self.assertIn("det_size=(640, 640)", text)
        self.assertIn("force_cpu=False", text)
        self.assertIn("CPUExecutionProvider", text)
        self.assertIn("prepare failed", text)

    def test_engine_exposes_provider_context_after_success(self):
        module = self.load_face_engine_module(providers=["CUDAExecutionProvider", "CPUExecutionProvider"])

        engine = module.FaceEngine(model_name="buffalo_l", det_size=(640, 640), force_cpu=False, use_gpu=True)

        self.assertEqual(engine.model_name, "buffalo_l")
        self.assertEqual(engine.det_size, (640, 640))
        self.assertEqual(engine.available_providers, ["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(engine.selected_provider_names, ["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(engine.device, "GPU (CUDA)")


if __name__ == "__main__":
    unittest.main()
