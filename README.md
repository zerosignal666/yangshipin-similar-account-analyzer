# Yangshipin Similar Account Analyzer

A desktop application that crawls public university account data from the Yangshipin (央视频 / yspapp.cn) platform, with built-in data visualization and snapshot comparison.

## Features

- **Batch Crawl** — Crawl follower count, play count, and video count from 100+ university accounts. Start / Pause / Resume / Stop with live progress.
- **Data Table** — Sortable, searchable table with unit switching (raw / 万 / 亿). Highlight any university (e.g. your own) in red.
- **Charts** — Interactive bar charts, histograms, and scatter plots with hover tooltips and scroll zoom.
- **Dashboard** — Responsive multi-chart grid that adapts to window size.
- **Snapshot System** — Each crawl saves a timestamped snapshot. Compare any two snapshots to see growth.
- **Rate Limiting** — Configurable crawl frequency control to be respectful to the server.

## Screenshots

*Coming soon*

## Requirements

- Windows 10/11 64-bit (macOS support planned)
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
│   │   ├── charts.py        # Matplotlib + seaborn chart functions
│   │   └── stats.py         # Pandas statistics + PandaTools
│   └── ui/
│       ├── main_window.py   # Tkinter main window (3-tab layout)
│       ├── chart_windows.py # Interactive chart popups (zoom, hover, click)
│       └── workers.py       # Background thread for crawl operations
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
| GUI | Tkinter (built-in) |
| Charts | Matplotlib + Seaborn (TkAgg backend) |
| Data | Pandas + NumPy |
| HTTP | httpx |
| Parser | BeautifulSoup4 + lxml |
| Database | SQLite |
| Packaging | PyInstaller |

## Data Source

All data comes from public profile pages on [yspapp.cn](https://www.yspapp.cn). The app parses the `window.__STATE_USER__` JSON embedded in the HTML source. No login or API key required.

## License

MIT License — see [LICENSE](LICENSE) for details.
