# Pdf Apocalypse

`pdf_apocalypse.py` is a command-line tool to batch-slice scanned student exams into per-question PDFs using OCR-based question detection and edge-density heuristics for drawing-heavy pages. It merges multiple PDF scans per student, splits on question headers, and logs drawing-heavy responses.

## Features

- **Merge & Split**: Combines multiple scanned PDFs per student and splits into question-based chunks.
- **OCR Question Detection**: Uses Tesseract OCR to locate question headers (configurable regex).
- **Drawing Detection**: Identifies pages heavy in drawings via OpenCV edge-density analysis.
- **Parallel Processing**: Utilizes all available CPU cores for high-speed processing.
- **Logging**: Detailed INFO logs and separate `drawing_detection_log.txt` for flagged pages.
- **Configurable**: Easily tweak regex patterns, DPI, edge thresholds, and worker count.

## Requirements

- Python 3.8+
- Homebrew (macOS) or apt (Linux)

### Python Packages

```bash
pip install   pypdf pytesseract opencv-python pillow tqdm pdf2image
```

### System Dependencies

- **Tesseract OCR**
  - macOS: `brew install tesseract`
  - Ubuntu: `sudo apt-get install tesseract-ocr`
- **Poppler (for `pdf2image`)**
  - macOS: `brew install poppler`
  - Ubuntu: `sudo apt-get install poppler-utils`

## Usage

```bash
python pdf_apocalypse.py   --input_dir /path/to/student_folders   --output_dir /path/to/output   [--workers N]
```

- `--input_dir`: Root folder containing one subfolder per student (named by Student ID).
- `--output_dir`: Destination folder for sliced PDFs and logs.
- `--workers`: (Optional) Number of parallel processes (default = number of CPU cores).

## Examples

```bash
# Basic usage
python pdf_apocalypse.py --input_dir ./scans --output_dir ./sliced

# Limit to 8 parallel workers
python pdf_apocalypse.py   --input_dir ./scans   --output_dir ./sliced   --workers 8
```

After running, you'll see:

```
/sliced/
  ├ drawing_detection_log.txt
  ├ student1234/
  │   ├ student1234_Q1.pdf
  │   └ student1234_Q2_drawing.pdf
  └ student5678/
      ├ student5678_Q1.pdf
      └ student5678_Q2.pdf
```

## Configuration

- `QUESTION_REGEX` (in script)
  - Default: `(Question\s*\d+|Problem\s*\d+|Q\s*\d+)`
  - Adjust to match your exam's question headings.

- `EDGE_DENSITY_THRESHOLD`
  - Default: `1000`
  - Lower value = more pages flagged as drawings.

- `DEFAULT_DPI`
  - Default: `300`
  - Reduce for faster processing or increase for clarity.

## Troubleshooting

- **Tesseract not found**
  - Ensure `tesseract` is in your PATH after installation.

- **OCR/spurious splits**
  - Adjust `QUESTION_REGEX` or preprocess scans for better consistency.

- **Slow performance**
  - Increase `--workers`; lower DPI in `pdf_page_to_image`.

- **Corrupt PDF error**
  - Verify scans; script will skip pages it cannot render.

## License & Attribution

This tool was developed for educational use by cybersecurity researchers and instructors. Feel free to adapt and extend as needed.

Happy grading! 🚀
