"""PySide6 交互图表窗口与多图仪表盘。"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.container import BarContainer
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QGridLayout, QScrollArea, QVBoxLayout, QWidget

from ..analysis.charts import _force_init_font, get_cjk_font, setup_font
from ..models.schema import auto_unit
from .theme import palette


def _dark(parent) -> bool:
    window = parent.window() if parent else None
    return bool(getattr(window, "is_dark", False))


def _colors(parent) -> dict[str, str]:
    return palette(_dark(parent))


def _font_info():
    fp = _force_init_font()
    if fp is None: return None, None
    path = fp.get_file()
    if path and path != fp.get_name():
        try:
            resolved = FontProperties(fname=path)
            return resolved, resolved.get_name()
        except (OSError, RuntimeError):
            pass
    return fp, fp.get_name()


def style_figure(fig, parent) -> None:
    c = _colors(parent)
    fig.patch.set_facecolor(c["surface"])
    for ax in fig.axes:
        ax.set_facecolor(c["surface"])
        ax.tick_params(colors=c["muted"])
        ax.xaxis.label.set_color(c["muted"])
        ax.yaxis.label.set_color(c["muted"])
        ax.title.set_color(c["text"])
        for spine in ax.spines.values():
            spine.set_color(c["line"])
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.grid(color=c["line"], alpha=0.42, linewidth=0.7)


def _compact_number(value: float) -> str:
    number, unit = auto_unit(abs(value))
    sign = "-" if value < 0 else ""
    if unit == "个": return f"{value:,.0f}"
    return f"{sign}{number:,.1f}{unit}"


class BarHover:
    def __init__(self, canvas, parent):
        self.canvas = canvas; self._entries = []; self._annotations = {}; self._active = None
        c = _colors(parent); self._colors = c; fp = get_cjk_font()
        for ax in canvas.figure.axes:
            for container in ax.containers:
                if not isinstance(container, BarContainer) or not container.patches: continue
                orientation = getattr(container, "orientation", "vertical")
                labels = self._labels(ax, container, orientation)
                for index, bar in enumerate(container.patches):
                    value = bar.get_width() if orientation == "horizontal" else bar.get_height()
                    label = labels[index] if index < len(labels) else f"第 {index + 1} 项"
                    self._entries.append((ax, bar, label, float(value), orientation))
                self._modernize(ax, orientation, c)
            if any(entry[0] is ax for entry in self._entries):
                self._annotations[ax] = ax.annotate(
                    "", xy=(0, 0), xytext=(12, 12), textcoords="offset points", visible=False,
                    bbox=dict(boxstyle="round,pad=0.45", fc=c["surface"], ec=c["primary"], alpha=0.97),
                    color=c["text"], fontproperties=fp, zorder=20,
                )
        self.connection_id = canvas.mpl_connect("motion_notify_event", self._on_hover) if self._entries else None

    @staticmethod
    def _labels(ax, container, orientation):
        ticks = ax.get_yticklabels() if orientation == "horizontal" else ax.get_xticklabels()
        labels = [tick.get_text() for tick in ticks]
        if len(labels) == len(container.patches) and any(labels): return labels
        if orientation == "vertical":
            return [f"{bar.get_x():,.0f}–{bar.get_x() + bar.get_width():,.0f}" for bar in container.patches]
        return []

    @staticmethod
    def _modernize(ax, orientation, colors):
        ax.set_axisbelow(True); ax.grid(False); ax.tick_params(length=0)
        numeric_axis = ax.xaxis if orientation == "horizontal" else ax.yaxis
        numeric_axis.grid(True, color=colors["line"], alpha=0.42, linewidth=0.7)
        numeric_axis.set_major_formatter(FuncFormatter(lambda value, _position: _compact_number(value)))
        font = get_cjk_font()
        for label in numeric_axis.get_ticklabels():
            label.set_fontproperties(font)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

    def _restore_active(self):
        if self._active is None: return
        bar, edgecolor, linewidth = self._active
        bar.set_edgecolor(edgecolor); bar.set_linewidth(linewidth); self._active = None

    def _hide(self):
        changed = self._active is not None or any(item.get_visible() for item in self._annotations.values())
        self._restore_active()
        for annotation in self._annotations.values(): annotation.set_visible(False)
        if changed: self.canvas.draw_idle()

    def _on_hover(self, event):
        if event.inaxes not in self._annotations:
            self._hide(); return
        for ax, bar, label, value, orientation in self._entries:
            if ax is not event.inaxes or not bar.contains(event)[0]: continue
            self._restore_active()
            self._active = (bar, bar.get_edgecolor(), bar.get_linewidth())
            bar.set_edgecolor(self._colors["warning"]); bar.set_linewidth(2)
            annotation = self._annotations[ax]
            if orientation == "horizontal":
                end_x = bar.get_x() + bar.get_width()
                annotation.xy = (end_x, bar.get_y() + bar.get_height() / 2)
                if end_x >= sum(ax.get_xlim()) / 2:
                    annotation.set_position((-12, 12)); annotation.set_horizontalalignment("right")
                else:
                    annotation.set_position((12, 12)); annotation.set_horizontalalignment("left")
                annotation.set_verticalalignment("bottom")
            else:
                end_y = bar.get_y() + bar.get_height()
                annotation.xy = (bar.get_x() + bar.get_width() / 2, end_y)
                annotation.set_horizontalalignment("left")
                if end_y >= sum(ax.get_ylim()) / 2:
                    annotation.set_position((12, -12)); annotation.set_verticalalignment("top")
                else:
                    annotation.set_position((12, 12)); annotation.set_verticalalignment("bottom")
            annotation.set_text(f"{label}\n精确值  {_compact_number(value)}")
            annotation.set_visible(True); self.canvas.draw_idle(); return
        self._hide()


def attach_bar_hover(canvas, parent):
    canvas._bar_hover = BarHover(canvas, parent)
    canvas.draw_idle()
    return canvas._bar_hover


class ChartDialog(QDialog):
    def __init__(self, parent, title: str, fig):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(title)
        self.resize(940, 680)
        self.setMinimumSize(680, 480)
        self._fig = fig
        style_figure(fig, parent)
        box = QVBoxLayout(self)
        box.setContentsMargins(10, 10, 10, 10)
        self._canvas = FigureCanvasQTAgg(fig)
        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        box.addWidget(self._toolbar)
        box.addWidget(self._canvas, 1)
        self._canvas.draw()
        self.show()

    def closeEvent(self, event):
        plt.close(self._fig)
        super().closeEvent(event)


class BarChartWindow(ChartDialog):
    def __init__(self, parent, df, col="fans_base", n=15, title="TOP N", highlight_name=None):
        setup_font(); c = _colors(parent); fp = get_cjk_font()
        top = df.nlargest(n, col).sort_values(col, ascending=True)
        names = top["name"].values; values = top[col].values
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = [c["danger"] if highlight_name and name == highlight_name else c["primary"] for name in names]
        self._bars = ax.barh(range(len(top)), values, color=colors)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(names, fontsize=9, fontproperties=fp)
        ax.set_title(title, fontsize=15, fontweight="bold", fontproperties=fp)
        fig.tight_layout()
        super().__init__(parent, title, fig)
        attach_bar_hover(self._canvas, parent)


class HistogramWindow(ChartDialog):
    def __init__(self, parent, df, col="fans_base", title="Distribution", bins=20,
                 highlight_name=None, highlight_value=None):
        setup_font(); c = _colors(parent); fp = get_cjk_font(); data = df[col].dropna()
        fig, ax = plt.subplots(figsize=(10, 6))
        self._counts, self._bins, self._patches = ax.hist(
            data, bins=bins, color=c["primary"], edgecolor=c["surface"], alpha=0.88)
        ax.axvline(data.median(), color=c["muted"], linestyle="--", label=f"中位数 {data.median():,.0f}")
        ax.axvline(data.mean(), color=c["warning"], linestyle="--", label=f"平均值 {data.mean():,.0f}")
        if highlight_name and highlight_value and highlight_value > 0:
            ax.axvline(highlight_value, color=c["danger"], linewidth=2.5,
                       label=f"{highlight_name} {highlight_value:,.0f}")
        ax.set_title(title, fontsize=15, fontweight="bold", fontproperties=fp)
        ax.legend(prop=fp)
        self._annot = ax.annotate(
            "", xy=(0, 0), xytext=(14, 14), textcoords="offset points", visible=False,
            bbox=dict(boxstyle="round,pad=0.4", fc=c["surface"], ec=c["line"], alpha=0.96),
            color=c["text"], fontproperties=fp)
        fig.tight_layout()
        super().__init__(parent, title, fig)
        self._canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _on_hover(self, event):
        if event.inaxes is None:
            self._annot.set_visible(False); self._canvas.draw_idle(); return
        for patch, count in zip(self._patches, self._counts):
            if patch.contains(event)[0]:
                lo = patch.get_x(); hi = lo + patch.get_width()
                self._annot.xy = (event.xdata, event.ydata)
                self._annot.set_text(f"{lo:,.0f} – {hi:,.0f}\n{int(count)} 个账号")
                self._annot.set_visible(True); self._canvas.draw_idle(); return
        self._annot.set_visible(False); self._canvas.draw_idle()


class ScatterWindow(ChartDialog):
    def __init__(self, parent, df, x="fans_base", y="play_base",
                 xl="Fans", yl="Plays", title="Fans vs Plays", highlight_name=None):
        setup_font(); c = _colors(parent); fp, _ = _font_info()
        self._names = df["name"].values
        self._xv = df[x].fillna(0).values; self._yv = df[y].fillna(0).values
        colors = np.full(len(df), c["primary"], dtype=object)
        sizes = np.full(len(df), 45.); alpha = np.full(len(df), 0.55)
        if highlight_name:
            mask = self._names == highlight_name
            colors[mask] = c["danger"]; sizes[mask] = 145; alpha[mask] = 1
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(self._xv, self._yv, c=colors, s=sizes, alpha=alpha,
                   edgecolors=c["surface"], linewidth=0.6)
        if len(df) > 2:
            fit = np.poly1d(np.polyfit(self._xv, self._yv, 1))
            line_x = np.linspace(self._xv.min(), self._xv.max(), 100)
            ax.plot(line_x, fit(line_x), "--", color=c["warning"], alpha=0.7)
        ax.set_xlabel(xl, fontproperties=fp); ax.set_ylabel(yl, fontproperties=fp)
        ax.set_title(title, fontsize=15, fontweight="bold", fontproperties=fp)
        self._annot = ax.annotate(
            "", xy=(0, 0), xytext=(14, 14), textcoords="offset points", visible=False,
            bbox=dict(boxstyle="round,pad=0.4", fc=c["surface"], ec=c["line"], alpha=0.96),
            color=c["text"], fontproperties=fp)
        fig.tight_layout()
        super().__init__(parent, title, fig)
        self._canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _nearest(self, x, y):
        xr = np.ptp(self._xv) or 1; yr = np.ptp(self._yv) or 1
        distances = ((self._xv - x) / xr) ** 2 + ((self._yv - y) / yr) ** 2
        index = int(np.argmin(distances))
        return index if distances[index] < 0.006 else None

    def _on_hover(self, event):
        if event.inaxes is None or event.xdata is None:
            self._annot.set_visible(False); self._canvas.draw_idle(); return
        index = self._nearest(event.xdata, event.ydata)
        if index is None:
            self._annot.set_visible(False); self._canvas.draw_idle(); return
        self._annot.xy = (self._xv[index], self._yv[index])
        self._annot.set_text(f"{self._names[index]}\n粉丝 {self._xv[index]:,.0f}\n播放 {self._yv[index]:,.0f}")
        self._annot.set_visible(True); self._canvas.draw_idle()


class DashboardWindow(QDialog):
    def __init__(self, parent, df, charts_config, highlight_name=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("分析仪表盘")
        self.resize(1220, 820)
        self._figures = []
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); grid = QGridLayout(content)
        grid.setContentsMargins(12, 12, 12, 12); grid.setSpacing(12)
        for index, cfg in enumerate(charts_config):
            fig = _dashboard_figure(parent, df, cfg, highlight_name)
            self._figures.append(fig)
            canvas = FigureCanvasQTAgg(fig); attach_bar_hover(canvas, parent); canvas.draw()
            grid.addWidget(canvas, index // 2, index % 2)
        scroll.setWidget(content)
        box = QVBoxLayout(self); box.addWidget(scroll)
        self.show()

    def closeEvent(self, event):
        for fig in self._figures: plt.close(fig)
        super().closeEvent(event)


def _dashboard_figure(parent, df, cfg, highlight_name):
    setup_font(); c = _colors(parent); fp = get_cjk_font()
    fig, ax = plt.subplots(figsize=(5.8, 4.1), dpi=100)
    kind = cfg.get("type", "bar")
    if kind == "bar":
        col = cfg.get("col", "fans_base"); count = cfg.get("n", 15)
        top = df.nlargest(count, col).sort_values(col)
        names = top["name"].values
        colors = [c["danger"] if highlight_name and name == highlight_name else c["primary"] for name in names]
        ax.barh(range(len(top)), top[col].values, color=colors)
        ax.set_yticks(range(len(top))); ax.set_yticklabels(names, fontsize=7, fontproperties=fp)
    elif kind == "hist":
        data = df[cfg.get("col", "fans_base")].dropna()
        ax.hist(data, bins=cfg.get("bins", 20), color=c["primary"], edgecolor=c["surface"])
        ax.axvline(data.median(), color=c["muted"], linestyle="--")
    else:
        x = cfg.get("x", "fans_base"); y = cfg.get("y", "play_base")
        names = df["name"].values; colors = np.full(len(df), c["primary"], dtype=object)
        if highlight_name: colors[names == highlight_name] = c["danger"]
        ax.scatter(df[x].fillna(0), df[y].fillna(0), c=colors, s=24, alpha=0.65)
    ax.set_title(cfg.get("title", "图表"), fontsize=11, fontweight="bold", fontproperties=fp)
    style_figure(fig, parent); fig.tight_layout(pad=1.4)
    return fig
