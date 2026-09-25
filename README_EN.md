[中文](README.md) | English

# Yangshipin Similar Account Analyzer

A modern desktop application that crawls public university account data from Yangshipin (央视频 / yspapp.cn), with visualization, snapshot comparison, and all-school breakout monitoring. The PySide6 interface defaults to light mode and includes a dark-mode toggle.

## Features

- **Batch Crawl** — Crawl follower count, play count, and video count from 100+ university accounts. Start / Pause / Resume / Stop with live progress.
- **Data Table** — Sortable, searchable table with unit switching (raw / 万 / 亿). Highlight any university (e.g. your own) in red.
- **Charts** — Ranking and comparison bars use compact axes, hover highlighting, and exact-value tooltips; histograms and scatter plots support zoom and point labels.
- **Dashboard** — Responsive multi-chart grid that adapts to window size.
- **Snapshot System** — Each crawl saves a timestamped snapshot. Compare any two snapshots to see growth. Auto-swaps snapshots by time to ensure correct comparison direction.
- **Snapshot Compare** — 4 growth ranking charts with quantization error intervals (confirmed / uncertain ±500). Autocomplete search: click to view detail, double-click to fill.
- **All-school Pulse Watch** — Scan every university in a selected snapshot range and rank play growth, video growth, plays gained per new video, and robust anomaly signals. A plain-language sensitivity control uses a fixed multiplier unit, gaps are excluded from breakout decisions, and each school can be opened for interval-level evidence.
- **Rate Limiting** — Configurable crawl frequency control to be respectful to the server.
- **Safer Settings** — Collection parameters use large minus/plus controls, a numeric-only field, and a fixed unit label.

## Requirements

- Windows 10/11 64-bit
- The code path is macOS-compatible; a signed Mac package still requires validation on real Mac hardware
- No Python installation needed if using the pre-built EXE

## Quick Start

### Option 1: Run the Pre-built EXE

1. Download `YSP-Analyzer.zip` from [Releases](../../releases)
2. Extract and double-click `YSP-Analyzer.exe`

### Option 2: Run from Source

```bash
# Clone the repo
git clone https://github.com/zerosignal666/yangshipin-similar-account-analyzer.git
cd yangshipin-similar-account-analyzer

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Project Structure

```
ysp-analyzer/
├── main.py                  # Entry point
├── requirements.txt         # Python dependencies
├── 同类账号.txt              # Account list (Name [TAB] URL)
├── src/
│   ├── crawler/             # Web crawling
│   │   ├── engine.py        # Crawl orchestration (thread pool, rate limit)
│   │   ├── fetcher.py       # HTTP client (httpx)
│   │   ├── parser.py        # HTML/JSON parser (extract __STATE_USER__)
│   │   └── url_parser.py    # Account file parser + CPID extractor
│   ├── models/
│   │   ├── schema.py        # SQL table definitions + unit normalization
│   │   └── database.py      # SQLite CRUD operations
│   ├── analysis/
│   │   ├── charts.py        # Matplotlib chart functions + CJK fonts
│   │   ├── stats.py         # Statistics + change intervals
│   │   └── burst.py         # School content pulses + robust threshold
│   └── ui/
│       ├── main_window.py   # PySide6 main window (6 sidebar workspaces)
│       ├── burst_page.py    # All-school pulse ranking and filtering
│       ├── theme.py         # Light/dark themes + cross-platform fonts
│       ├── widgets.py       # Shared cards, headers, and metric widgets
│       ├── chart_windows.py # Shared QtAgg interactive charts
│       ├── burst_window.py  # Content Pulse window
│       └── workers.py       # QThread crawl worker
└── data/                    # SQLite database (auto-created, gitignored)
```

## Custom Account List

Edit `同类账号.txt` to add or remove accounts. Format:

```
University Name[TAB]https://www.yspapp.cn/...
```

One account per line. The app reads this file on startup.

## Tech Stack

| Layer | Library |
|---|---|
| GUI | PySide6 (Qt 6) |
| Charts | Matplotlib (QtAgg backend) |
| Data | Pandas + NumPy |
| HTTP | httpx |
| Parser | BeautifulSoup4 + lxml |
| Database | SQLite |
| Packaging | PyInstaller |

## Data Source

All data comes from public profile pages on [yspapp.cn](https://www.yspapp.cn). The app parses the `window.__STATE_USER__` JSON embedded in the HTML source. No login or API key required.

## License

MIT License — see [LICENSE](LICENSE) for details.
