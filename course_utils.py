#!/usr/bin/env python3
"""
course_utils.py
------------------
A command-line toolkit for common course administration workflows:

- Slice scanned student exams into per-question PDFs.
- Generate project peer-review groups from a roster CSV.
- Rename Gradescope submission files based on review pairing metadata.

Usage:
    python course_utils.py <command> [options]

Commands:
    slice      Slice scanned exam PDFs by question.
    gen-groups Generate project group assignments for peer review.
    rename     Rename submission files according to peer-review assignments.

Requires:
    Python 3.8+
    pip install pypdf pytesseract opencv-python pillow tqdm pdf2image pyyaml
    brew install tesseract poppler      # macOS
    sudo apt-get install tesseract-ocr poppler-utils  # Debian/Ubuntu
"""

import argparse
import csv
import logging
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import numpy as np
import pytesseract
import yaml
from pdf2image import convert_from_bytes
from pypdf import PdfReader, PdfWriter
from PIL import ImageFilter
from tqdm import tqdm
import cv2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Default settings for slicing
QUESTION_REGEX = r"(Question\s*\d+|Problem\s*\d+|Q\s*\d+)"
EDGE_DETECT_THRESHOLD = 1000  # Edge count above which page is flagged as drawing
DEFAULT_DPI = 300


def check_tesseract() -> None:
    """
    Exit if the Tesseract OCR binary is not found in PATH.
    """
    if not shutil.which('tesseract'):
        logger.error(
            "Tesseract OCR not found. "
            "Install via 'brew install tesseract' or 'apt-get install tesseract-ocr'."
        )
        sys.exit(1)


def pdf_page_to_image(page, dpi: int = DEFAULT_DPI):
    """
    Render a PDF page to a PIL Image using Poppler via pdf2image.

    Args:
        page: A single PyPDF page object.
        dpi:  The resolution in dots per inch for rendering.

    Returns:
        A PIL Image of the rendered page.
    """
    writer = PdfWriter()
    writer.add_page(page)
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    images = convert_from_bytes(buffer.getvalue(), dpi=dpi)
    return images[0]


def detect_question(text: str) -> bool:
    """
    Determine if OCR-extracted text indicates the start of a new question.

    Args:
        text: The string result from OCR on a page image.

    Returns:
        True if a question header is found, False otherwise.
    """
    import re
    return bool(re.search(QUESTION_REGEX, text, flags=re.IGNORECASE))


def detect_drawing(image) -> bool:
    """
    Heuristically classify a page as drawing-heavy based on edge density.
    Falls back to PIL FIND_EDGES if OpenCV fails.

    Args:
        image: A PIL Image or array representing the page.

    Returns:
        True if detected edges exceed threshold, indicating drawings.
    """
    try:
        arr = np.array(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_count = cv2.countNonZero(edges)
    except Exception:
        # Fallback: use PIL's FIND_EDGES
        gray = image.convert('L')
        edges_img = gray.filter(ImageFilter.FIND_EDGES)
        arr = np.array(edges_img)
        edge_count = int((arr > 0).sum())

    return edge_count > EDGE_DETECT_THRESHOLD


def process_student_folder(student_folder: Path, output_root: Path):
    """
    Merge scanned PDFs for a student, split into per-question chunks,
    detect drawing-heavy pages, and write outputs.

    Args:
        student_folder: Directory containing one or more PDF scans.
        output_root:    Root directory where outputs are saved.

    Returns:
        Tuple[str, List[Tuple[Path, bool]]]: student_id and list of (file_path, drawing_flag).
    """
    student_id = student_folder.name
    pdf_paths = sorted(student_folder.glob('*.pdf'))

    if not pdf_paths:
        logger.warning("No PDF scans found for '%s'.", student_id)
        return student_id, []

    # Merge all input PDFs
    merged_writer = PdfWriter()
    for path in pdf_paths:
        reader = PdfReader(str(path))
        for pg in reader.pages:
            merged_writer.add_page(pg)

    # Read merged PDF into memory
    merged_buffer = BytesIO()
    merged_writer.write(merged_buffer)
    merged_buffer.seek(0)
    merged_reader = PdfReader(merged_buffer)

    # Split pages by detected question headers
    chunks = []
    current_pages = []
    current_flags = []
    for page in merged_reader.pages:
        img = pdf_page_to_image(page)
        text = pytesseract.image_to_string(img)

        if detect_question(text) and current_pages:
            chunks.append((current_pages, current_flags))
            current_pages, current_flags = [], []

        current_pages.append(page)
        current_flags.append(detect_drawing(img))

    if current_pages:
        chunks.append((current_pages, current_flags))

    # Write out per-question PDFs
    output_entries = []
    student_output_dir = output_root / student_id
    student_output_dir.mkdir(parents=True, exist_ok=True)
    for idx, (pages, flags) in enumerate(chunks, start=1):
        writer = PdfWriter()
        for pg in pages:
            writer.add_page(pg)
        suffix = '_drawing' if any(flags) else ''
        filename = f"{student_id}_Q{idx}{suffix}.pdf"
        filepath = student_output_dir / filename
        with open(filepath, 'wb') as f:
            writer.write(f)
        output_entries.append((filepath, any(flags)))

    return student_id, output_entries


def cmd_slice(args):
    """
    Command to slice scanned exam PDFs by question boundaries.
    """
    check_tesseract()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    student_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
    results = []

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_student_folder, sd, output_dir): sd.name
            for sd in student_dirs
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc='Slicing'):
            results.append(future.result())

    # Write drawing log
    log_path = output_dir / 'drawing_detection_log.txt'
    with open(log_path, 'w') as log_file:
        for sid, entries in results:
            for path, is_draw in entries:
                if is_draw:
                    log_file.write(f"{sid}: {path.name} [DRAWING]\n")

    logger.info("Slice complete. Outputs saved to %s", output_dir)


def cmd_gen_groups(args):
    """
    Command to generate peer-review group pairs from a roster CSV.

    Each CSV row should alternate between student name and email columns.
    """
    rows = list(csv.reader(open(args.csv_file_path)))
    header, data = rows[0], rows[1:]

    # Build group metadata
    group_info = {}
    for idx, row in enumerate(data, start=1):
        names = row[0::2]
        emails = row[1::2]
        group_info[f'group {idx}'] = {'names': names, 'emails': emails}

    num_projects = args.projects
    groups = list(group_info.keys())
    pairings = []

    # Rotational pairing for each project
    for p in range(num_projects):
        for g in groups:
            partner = groups[(groups.index(g) + p + 1) % len(groups)]
            pairings.append((p + 1, g, partner))

    # Write projgroups.csv
    out_file = Path('projgroups.csv')
    with open(out_file, 'w', newline='') as cf:
        writer = csv.writer(cf)
        writer.writerow([
            'Project', 'Group A', 'Group B',
            'Emails A', 'Emails B', 'Names A', 'Names B'
        ])
        for proj, ga, gb in pairings:
            info_a = group_info[ga]
            info_b = group_info[gb]
            writer.writerow([
                f'Project {proj}', ga, gb,
                ';'.join(info_a['emails']),
                ';'.join(info_b['emails']),
                ';'.join(info_a['names']),
                ';'.join(info_b['names'])
            ])

    logger.info("Project groups generated in %s", out_file)


def cmd_rename(args):
    """
    Command to rename Gradescope submission files based on review assignments.

    Relies on a CSV of group pairings and a YAML metadata file.
    """
    pairinfo = list(csv.DictReader(open(args.csv_file_path)))
    docs = yaml.safe_load_all(open(args.metadata_yaml))
    project_num = args.project

    log_path = Path('eval_sources.txt')
    with open(log_path, 'w') as logf:
        logf.write('Sources of eval by filename:\n')
        for doc in docs:
            for fname, data in doc.items():
                orig_path = Path(args.metadata_yaml).parent / fname
                for submitter in data.get(':submitters', []):
                    name = submitter.get(':name', '')
                    for row in pairinfo:
                        if row['Project'] != f'Project {project_num}':
                            continue
                        if name in row['Group A Names']:
                            target, source = row['Group B'], row['Group A']
                        elif name in row['Group B Names']:
                            target, source = row['Group A'], row['Group B']
                        else:
                            continue
                        new_name = (
                            f"P{project_num}PeerEval_sendto_"
                            f"{target.replace(' ', '_')}{orig_path.suffix}"
                        )
                        new_path = orig_path.with_name(new_name)
                        orig_path.rename(new_path)
                        logf.write(f"{orig_path} -> {new_path} (from {source})\n")
                        logger.info("Renamed %s to %s", orig_path, new_path)

    logger.info("Rename complete; see %s", log_path)


def main():
    """
    Parse CLI arguments and dispatch to the appropriate subcommand.
    """
    parser = argparse.ArgumentParser(
        description='Course utilities: slice, gen-groups, rename.'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # slice subcommand
    slice_parser = subparsers.add_parser(
        'slice', help='Slice scanned exam PDFs into per-question PDFs.'
    )
    slice_parser.add_argument(
        '--input_dir', required=True,
        help='Directory containing per-student folders with PDF scans.'
    )
    slice_parser.add_argument(
        '--output_dir', required=True,
        help='Directory to save sliced PDF outputs.'
    )
    slice_parser.add_argument(
        '--workers', type=int, default=None,
        help='Number of parallel workers (default = CPU count).'
    )
    slice_parser.set_defaults(func=cmd_slice)

    # gen-groups subcommand
    gen_parser = subparsers.add_parser(
        'gen-groups', help='Generate project peer-review group assignments.'
    )
    gen_parser.add_argument(
        'csv_file_path',
        help='CSV file with alternating name,email columns per group.'
    )
    gen_parser.add_argument(
        '--projects', type=int, default=4,
        help='Number of distinct review projects to generate.'
    )
    gen_parser.set_defaults(func=cmd_gen_groups)

    # rename subcommand
    rename_parser = subparsers.add_parser(
        'rename', help='Rename Gradescope submission files.'
    )
    rename_parser.add_argument(
        'csv_file_path',
        help='CSV file containing generated group pairings.'
    )
    rename_parser.add_argument(
        'metadata_yaml',
        help='YAML file with submission metadata (from Gradescope).'
    )
    rename_parser.add_argument(
        '--project', type=int, required=True,
        help='Project number corresponding to review pairing.'
    )
    rename_parser.set_defaults(func=cmd_rename)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()