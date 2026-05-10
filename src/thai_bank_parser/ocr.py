from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Callable

import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR

from .models import OcrBox


Progress = Callable[[str, int, int], None]


def render_table_pages(
    pdf_path: Path,
    work_dir: Path,
    table_crop: tuple[int, int, int, int],
    scale: float,
    progress: Progress | None = None,
) -> list[Path]:
    page_dir = work_dir / "rendered"
    page_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(pdf_path))
    image_paths: list[Path] = []

    for page_index in range(len(pdf)):
        page_number = page_index + 1
        output_path = page_dir / f"page_{page_number:03d}.png"
        image_paths.append(output_path)
        if progress:
            progress("render", page_number, len(pdf))
        if output_path.exists():
            continue
        rendered = pdf[page_index].render(scale=scale).to_pil()
        rendered.crop(table_crop).save(output_path)

    return image_paths


def run_ocr(
    image_paths: list[Path],
    cache_path: Path,
    force: bool = False,
    debug_json: Path | None = None,
    progress: Progress | None = None,
) -> list[OcrBox]:
    if cache_path.exists() and not force:
        boxes = [OcrBox(**item) for item in json.loads(cache_path.read_text(encoding="utf-8"))]
        if debug_json:
            debug_json.parent.mkdir(parents=True, exist_ok=True)
            debug_json.write_text(cache_path.read_text(encoding="utf-8"), encoding="utf-8")
        return boxes

    ocr = RapidOCR()
    boxes: list[OcrBox] = []
    for index, image_path in enumerate(image_paths, start=1):
        if progress:
            progress("ocr", index, len(image_paths))
        page_match = re.search(r"(\d+)", image_path.stem)
        page = int(page_match.group(1)) if page_match else index
        result, _ = ocr(str(image_path))
        for box, text, confidence in result or []:
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            boxes.append(
                OcrBox(
                    page=page,
                    text=str(text).strip(),
                    confidence=float(confidence),
                    x0=float(min(xs)),
                    y0=float(min(ys)),
                    x1=float(max(xs)),
                    y1=float(max(ys)),
                )
            )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([asdict(box) for box in boxes], ensure_ascii=False, indent=2)
    cache_path.write_text(payload, encoding="utf-8")
    if debug_json:
        debug_json.parent.mkdir(parents=True, exist_ok=True)
        debug_json.write_text(payload, encoding="utf-8")
    return boxes
