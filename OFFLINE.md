# Offline Installation

The normal source repository stays small and public. For a machine with no
internet, create an ignored local offline bundle that contains all required
wheels.

## Build the Bundle

Run this on a machine with internet:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_offline_bundle.ps1 -Python python
```

This creates:

```text
offline-bundle/
  install_offline.ps1
  requirements.lock.txt
  wheelhouse/
    thai_bank_parser-*.whl
    rapidocr_onnxruntime-*.whl
    onnxruntime-*.whl
    ...
```

The folder is ignored by git because it contains large binary wheels.

## Install Without Internet

Copy `offline-bundle/` to the target machine, then run:

```powershell
cd offline-bundle
powershell -ExecutionPolicy Bypass -File .\install_offline.ps1 -Python python
```

No network access is used. The installer runs:

```powershell
python -m pip install --no-index --find-links .\wheelhouse thai-bank-parser
```

## OCR Models

`rapidocr-onnxruntime` ships the ONNX OCR models inside its wheel. The offline
bundle includes that wheel, so no model download is required at runtime.

## GPU Note

The default offline bundle uses CPU ONNX Runtime because it is the most portable.
GPU acceleration still works when a compatible GPU provider is installed in the
target environment, but the parser always falls back to CPU when GPU is not
available.

## Portable Windows Folder

If you also want to carry a Python runtime with the tool, build the portable
folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_portable_windows.ps1 -PythonHome "C:\Path\To\Python"
```

This creates an ignored `portable-windows/` folder with:

```text
portable-windows/
  python/
  offline-bundle/
  install.ps1
  tbp.ps1
```

On the target machine:

```powershell
cd portable-windows
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\tbp.ps1 start
```

This avoids downloading Python packages. The copied Python runtime should come
from a machine with the same OS/architecture as the target machine.
