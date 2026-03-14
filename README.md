# montage_auto

Automatically assemble a video montage from a folder of raw rushes:

1. **Sort** the rushes by filename (alphabetical) or by modification date.
2. **Remove silences** from each rush (configurable threshold and minimum duration).
3. **Concatenate** the processed clips into a single output video.

---

## Requirements

* Python ≥ 3.8
* [FFmpeg](https://ffmpeg.org/) installed and available on your `PATH`
  (required by MoviePy).

---

## Installation

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install -r requirements.txt
```

---

## Usage

### Command line

```bash
python -m montage_auto <input_dir> <output_file> [options]
```

| Argument / Option | Description |
|---|---|
| `input_dir` | Directory containing the raw video rush files. |
| `output` | Output video file path (e.g. `montage.mp4`). |
| `--sort {name,date}` | Sort rushes alphabetically (`name`, default) or by modification time (`date`). |
| `--no-silence-removal` | Disable silence removal and keep all audio as-is. |
| `--threshold FLOAT` | Normalised amplitude threshold for silence detection (default: `0.01`). |
| `--min-silence SECONDS` | Minimum continuous silence length to remove (default: `0.5` s). |

**Example:**

```bash
python -m montage_auto ./rushes output/montage.mp4 --sort name --threshold 0.02 --min-silence 1.0
```

### Python API

```python
from montage_auto import create_montage

create_montage(
    input_directory="./rushes",
    output_path="montage.mp4",
    sort_method="name",          # or "date"
    remove_silences=True,
    silence_threshold=0.01,
    min_silence_duration=0.5,
)
```

---

## Running the tests

```bash
pip install pytest
pytest
```

---

## Project structure

```
montage_auto/
├── montage_auto/
│   ├── __init__.py          # Public API
│   ├── __main__.py          # python -m montage_auto entry point
│   ├── _cli.py              # Argument parsing and CLI logic
│   ├── montage.py           # Main orchestration (sort → remove silence → concat)
│   ├── rush_sorter.py       # Collect and sort video files
│   └── silence_remover.py   # Detect and remove silent portions
├── tests/
│   ├── test_rush_sorter.py
│   └── test_silence_remover.py
├── requirements.txt
├── pyproject.toml
└── README.md
```