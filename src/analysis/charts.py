"""图表 —— matplotlib，Tkinter 嵌入，多平台中文字体"""
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.font_manager import FontProperties
import numpy as np
import os, warnings, glob, urllib.request, shutil, sys
warnings.filterwarnings("ignore", category=UserWarning, message=".*Glyph.*missing.*")

_CJK_FONT = None
_CJK_NAME = None

CJK_CANDIDATES = [
    "SimHei", "Microsoft YaHei", "Noto Sans SC", "Source Han Sans CN",
    "Noto Sans CJK SC", "SimSun", "DengXian", "KaiTi", "FangSong",
    "PingFang SC", "PingFang HK", "PingFang TC",
    "Heiti SC", "Heiti TC", "STHeiti", "STKaiti", "STSong", "STFangsong",
    "WenQuanYi Micro Hei", "WenQuanYi Zen Hei",
    "Noto Serif SC", "Noto Serif CJK SC",
    "AR PL UMing CN", "AR PL UKai CN",
    "Microsoft JhengHei", "Microsoft JhengHei UI", "Arial Unicode MS",
]

FONT_FILES = {
    "simhei": ["simhei.ttf", "SimHei.ttf"],
    "msyh": ["msyh.ttc", "msyh.ttf"],
    "simsun": ["simsun.ttc", "SimSun.ttc"],
    "noto": ["NotoSansSC-VF.ttf", "NotoSansCJKsc-VF.ttf", "NotoSansSC-Regular.ttf"],
}

FONT_DIR = os.path.join(os.path.expanduser("~"), ".ysp-analyzer", "fonts")


def _search_font_dirs():
    dirs = []
    windir = os.environ.get("WINDIR", r"C:\Windows")
    dirs.append(windir + r"\Fonts")
    dirs.append(os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\Fonts"))
    dirs.append("/System/Library/Fonts")
    dirs.append("/System/Library/Fonts/Supplemental")
    dirs.append(os.path.expanduser("~/Library/Fonts"))
    dirs.append("/usr/share/fonts")
    dirs.append("/usr/local/share/fonts")
    dirs.append(os.path.expanduser("~/.fonts"))
    dirs.append(os.path.expanduser("~/.local/share/fonts"))
    for base in ["/usr/share/fonts", "/usr/local/share/fonts"]:
        if os.path.isdir(base):
            for root, _, _ in os.walk(base):
                dirs.append(root)
    return dirs


def _download_font():
    os.makedirs(FONT_DIR, exist_ok=True)
    font_path = os.path.join(FONT_DIR, "NotoSansSC-Regular.ttf")
    if os.path.exists(font_path): return font_path
    urls = [
        "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                with open(font_path, "wb") as f:
                    f.write(resp.read())
            if os.path.getsize(font_path) > 100_000: return font_path
            else: os.remove(font_path)
        except: continue
    return None


def _force_init_font():
    global _CJK_FONT, _CJK_NAME
    if _CJK_FONT is not None: return _CJK_FONT
    try:
        cache_dir = matplotlib.get_cachedir()
        for pattern in ["fontlist-v*.json", "fonts-*.json", "*font*"]:
            for f in glob.glob(os.path.join(cache_dir, pattern)):
                try: os.remove(f)
                except: pass
    except: pass

    found_path = None
    for d in _search_font_dirs():
        if not os.path.isdir(d): continue
        for _, names in FONT_FILES.items():
            for name in names:
                fp = os.path.join(d, name)
                if os.path.isfile(fp): found_path = fp; break
            if found_path: break
        if found_path: break

    if not found_path:
        dl = os.path.join(FONT_DIR, "NotoSansSC-Regular.ttf")
        if os.path.exists(dl) and os.path.getsize(dl) > 100_000: found_path = dl

    if found_path:
        try:
            _CJK_FONT = FontProperties(fname=found_path)
            _CJK_NAME = _CJK_FONT.get_name()
        except: _CJK_FONT = None

    if _CJK_FONT is None:
        try: fm._load_fontmanager(try_read_cache=False)
        except: pass
        available = {f.name for f in fm.fontManager.ttflist}
        for name in CJK_CANDIDATES:
            if name in available:
                try: _CJK_FONT = FontProperties(family=name); _CJK_NAME = name; break
                except: pass

    if _CJK_FONT is None:
        try:
            dl_path = _download_font()
            if dl_path: _CJK_FONT = FontProperties(fname=dl_path); _CJK_NAME = _CJK_FONT.get_name()
        except: pass

    if _CJK_NAME:
        plt.rcParams["font.sans-serif"] = [_CJK_NAME, "DejaVu Sans"]
        plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 100
    return _CJK_FONT


def setup_font():
    _force_init_font()
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except Exception:
        plt.style.use('ggplot')  # matplotlib < 3.6 fallback


def get_cjk_font():
    return _CJK_FONT


C_DANGER = "#C00000"
C_BLUE = "#4472C4"
C_ORANGE = "#ED7D31"


def bar_top_n(df, col="fans_base", n=15, title="TOP N", highlight_name=None):
    setup_font(); cjk = get_cjk_font()
    top = df.nlargest(n, col).sort_values(col, ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    names, values = top["name"].values, top[col].values
    colors = [C_DANGER if highlight_name and nm == highlight_name else C_BLUE for nm in names]
    ax.barh(range(len(top)), values, color=colors)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(names, fontsize=9, fontproperties=cjk)
    ax.set_title(title, fontsize=14, fontweight="bold", fontproperties=cjk)
    fig.tight_layout(); return fig


def histogram(df, col="fans_base", title="Distribution", bins=20,
              highlight_name=None, highlight_value=None):
    setup_font(); cjk = get_cjk_font()
    data = df[col].dropna()
    fig, ax = plt.subplots(figsize=(9, 5))
    n, bins_out, patches = ax.hist(data, bins=bins, color=C_BLUE, edgecolor="white", alpha=0.85)
    ax.axvline(data.median(), color="#888888", linestyle="--", linewidth=1.5,
               label=f"Median: {data.median():,.0f}")
    ax.axvline(data.mean(), color=C_ORANGE, linestyle="--", linewidth=1.5,
               label=f"Mean: {data.mean():,.0f}")
    if highlight_name and highlight_value and highlight_value > 0:
        ax.axvline(highlight_value, color=C_DANGER, linestyle="-", linewidth=2.5,
                   label=f"{highlight_name}: {highlight_value:,.0f}")
    ax.set_title(title, fontsize=14, fontweight="bold", fontproperties=cjk)
    ax.legend(prop=cjk)
    fig.tight_layout(); return fig


def scatter(df, x="fans_base", y="play_base", xl="Fans", yl="Plays",
            title="Fans vs Plays", highlight_name=None):
    setup_font(); cjk = get_cjk_font()
    fig, ax = plt.subplots(figsize=(9, 6))
    names = df["name"].values; xv = df[x].fillna(0).values; yv = df[y].fillna(0).values
    colors = np.full(len(df), C_BLUE, dtype=object)
    sizes = np.full(len(df), 50.); alphas = np.full(len(df), 0.5)
    if highlight_name:
        m = names == highlight_name; colors[m] = C_DANGER; sizes[m] = 140; alphas[m] = 1.0
    ax.scatter(xv, yv, c=colors, s=sizes, alpha=alphas, edgecolors="white", linewidth=0.5)
    for _, row in df.nlargest(5, y).iterrows():
        ishl = highlight_name and row["name"] == highlight_name
        ax.annotate(row["name"], (row[x], row[y]), fontsize=8,
                    color=C_DANGER if ishl else "#333333",
                    fontweight="bold" if ishl else "normal", alpha=0.9,
                    fontproperties=cjk, xytext=(5, 5), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))
    if len(df) > 2:
        z = np.polyfit(xv, yv, 1); p = np.poly1d(z)
        xr = np.linspace(xv.min(), xv.max(), 100)
        ax.plot(xr, p(xr), "--", color=C_ORANGE, alpha=0.6)
    ax.set_xlabel(xl); ax.set_ylabel(yl)
    ax.set_title(title, fontsize=14, fontweight="bold", fontproperties=cjk)
    fig.tight_layout(); return fig
