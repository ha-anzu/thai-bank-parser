from thai_bank_parser.ocr import resolve_ocr_device


def test_auto_prefers_cuda_provider():
    device, kwargs, reason = resolve_ocr_device(
        "auto", ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"]
    )
    assert device == "cuda"
    assert kwargs["det_use_cuda"]
    assert reason is None


def test_auto_uses_directml_before_cpu():
    device, kwargs, reason = resolve_ocr_device("auto", ["DmlExecutionProvider", "CPUExecutionProvider"])
    assert device == "dml"
    assert kwargs["rec_use_dml"]
    assert reason is None


def test_cuda_falls_back_to_cpu_when_provider_missing():
    device, kwargs, reason = resolve_ocr_device("cuda", ["CPUExecutionProvider"])
    assert device == "cpu"
    assert kwargs == {}
    assert "falling back to CPU" in reason


def test_cpu_forces_cpu_even_when_gpu_exists():
    device, kwargs, reason = resolve_ocr_device("cpu", ["CUDAExecutionProvider", "CPUExecutionProvider"])
    assert device == "cpu"
    assert kwargs == {}
    assert reason is None
