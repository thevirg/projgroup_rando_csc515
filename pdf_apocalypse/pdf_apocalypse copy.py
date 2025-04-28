#!/usr/bin/env python3
"""
pdf_apocalypse.py
------------------
Batch-slice scanned student exams into per-question PDFs using OCR and drawing detection.

Features:
- Merges multiple scanned PDFs per student
- OCR-based question boundary detection (regex configurable)
- Edge-density heuristic for drawing-heavy pages
- Parallel processing to utilize all CPU cores
- Detailed logging and separate drawing detection log

Requirements:
    pip install pypdf pytesseract opencv-python pillow tqdm pdf2image
    brew install tesseract poppler  # macOS
    sudo apt-get install tesseract-ocr poppler-utils  # Debian/Ubuntu

Usage:
    python pdf_apocalypse.py \
        --input_dir /path/to/student_folders \
        --output_dir /path/to/output \
        [--workers N]

Examples:
    python pdf_apocalypse.py --input_dir ./scans --output_dir ./sliced
"""
import sys
import shutil
import argparse
import logging
from pathlib import Path
from io import BytesIO
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pytesseract
import cv2
from tqdm import tqdm
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_bytes

# ---- Configuration ----
QUESTION_REGEX = r"(Question\s*\d+|Problem\s*\d+|Q\s*\d+)"
EDGE_DENSITY_THRESHOLD = 1000  # edges above this => drawing-heavy
DEFAULT_DPI = 300

# ---- Setup logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def check_tesseract():
    """Ensure Tesseract OCR binary is available."""
    if not shutil.which("tesseract"):
        logger.error("Tesseract not found. Install via 'brew install tesseract' or 'apt-get install tesseract-ocr'.")
        sys.exit(1)

def pdf_page_to_image(page, dpi: int = DEFAULT_DPI):
    """
    Render a single PDF page to a PIL image via poppler.
    """
    writer = PdfWriter()
    writer.add_page(page)
    pdf_bytes = BytesIO()
    writer.write(pdf_bytes)
    pdf_bytes.seek(0)
    images = convert_from_bytes(pdf_bytes.getvalue(), dpi=dpi)
    return images[0]

def detect_question(text: str) -> bool:
    """
    Detect if OCR text contains a question header.
    """
    import re
    return bool(re.search(QUESTION_REGEX, text, flags=re.IGNORECASE))

def detect_drawing(image) -> bool:
    """
    Heuristic: if edge density exceeds threshold, assume drawing.
    """
    arr = np.array(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_count = cv2.countNonZero(edges)
    return edge_count > EDGE_DENSITY_THRESHOLD

def process_student_folder(student_folder: Path, output_root: Path) -> tuple[str, list[tuple[Path, bool]]]:
    """
    Merge all PDFs in a student folder, split into question-based chunks,
    detect drawings, and write output files.
    Returns student_id and list of (file_path, drawing_flag).
    """
    student_id = student_folder.name
    pdf_paths = sorted(student_folder.glob("*.pdf"))
    if not pdf_paths:
        logger.warning("No PDF found for %s", student_id)
        return student_id, []

    merged = PdfWriter()
    for pdf in pdf_paths:
        reader = PdfReader(str(pdf))
        for p in reader.pages:
            merged.add_page(p)

    merged_bytes = BytesIO()
    merged.write(merged_bytes)
    merged_bytes.seek(0)
    merged_reader = PdfReader(merged_bytes)

    chunks, flags = [], []
    current_pages, current_flags = [], []

    for page in merged_reader.pages:
        try:
            img = pdf_page_to_image(page)
            text = pytesseract.image_to_string(img)
        except Exception as e:
            logger.error("OCR error on %s page %d: %s", student_id, merged_reader.pages.index(page), e)
            text = ""

        if detect_question(text) and current_pages:
            chunks.append((current_pages, current_flags))
            current_pages, current_flags = [], []

        current_pages.append(page)
        current_flags.append(detect_drawing(img))

    if current_pages:
        chunks.append((current_pages, current_flags))

    output_entries = []
    student_out = output_root / student_id
    student_out.mkdir(parents=True, exist_ok=True)
    for idx, (pages, drawing_marks) in enumerate(chunks, start=1):
        writer = PdfWriter()
        for p in pages:
            writer.add_page(p)
        label = "_drawing" if any(drawing_marks) else ""
        fname = f"{student_id}_Q{idx}{label}.pdf"
        out_path = student_out / fname
        with open(out_path, "wb") as f:
            writer.write(f)
        output_entries.append((out_path, any(drawing_marks)))

    return student_id, output_entries

def main():
    parser = argparse.ArgumentParser(description="Slice scanned exams by question with OCR & drawing detection.")
    parser.add_argument("--input_dir", required=True, type=Path, help="Directory of student folders.")
    parser.add_argument("--output_dir", required=True, type=Path, help="Directory to save outputs.")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers (default: CPU count)")
    args = parser.parse_args()

    check_tesseract()
    input_root, output_root = args.input_dir, args.output_dir
    output_root.mkdir(parents=True, exist_ok=True)

    folders = [d for d in input_root.iterdir() if d.is_dir()]
    total = len(folders)
    workers = args.workers or None

    results = []
    with ProcessPoolExecutor(max_workers=workers) as exec:
        futures = {exec.submit(process_student_folder, sf, output_root): sf for sf in folders}
        for f in tqdm(as_completed(futures), total=total, desc="Processing students"):
            results.append(f.result())

    log_file = output_root / "drawing_detection_log.txt"
    with open(log_file, "w") as logf:
        for sid, entries in results:
            for path, is_draw in entries:
                if is_draw:
                    logf.write(f"{sid}: {path.name} [DRAWING DETECTED]\n")
    logger.info("Processing complete. Outputs in %s", output_root)

if __name__ == "__main__":
    main()
