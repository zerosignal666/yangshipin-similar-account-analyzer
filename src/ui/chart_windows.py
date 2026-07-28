"""交互式图表窗口 —— 悬停中文、点击标注、仪表盘自适应"""
import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.font_manager import FontProperties

from ..analysis.charts import (_force_init_font, get_cjk_font, setup_font,
                                C_DANGER, C_BLUE, C_ORANGE)


def _resolve_cjk_font():
    fp = _force_init_font()
    if fp is None: return None, None
    name = fp.get_name(); fname = fp.get_file()
    if fname and fname != name:
        try: fp2 = FontProperties(fname=fname); name2 = fp2.get_name(); return fp2, name2
        except: pass
    return fp, name


class _Base(tk.Toplevel):
    def __init__(self, parent, title="Chart", figsize=(10, 7)):
        super().__init__(parent)
        self.title(title); self.geometry("900x700"); self.minsize(600, 450)
        self.transient(parent)
        self._font_prop, self._font_name = _resolve_cjk_font()
        self._fig = plt.figure(figsize=figsize)
        self._build()
        self._canvas = FigureCanvasTkAgg(self._fig, self); self._canvas.draw()
        self._tb = NavigationToolbar2Tk(self._canvas, self); self._tb.update()
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._canvas.mpl_connect("scroll_event", self._on_scroll)
        self._canvas.get_tk_widget().bind("<MouseWheel>", self._on_mw)
        self._canvas.get_tk_widget().bind("<Button-4>", lambda e: self._zoom(0.85))
        self._canvas.get_tk_widget().bind("<Button-5>", lambda e: self._zoom(1.15))

    def _build(self): raise NotImplementedError

    def _on_scroll(self, event):
        if event.inaxes is None: return
        s = 0.85 if event.button == "up" else 1.15
        xl = event.inaxes.get_xlim(); yl = event.inaxes.get_ylim()
        xd, yd = event.xdata, event.ydata
        if xd is None: return
        event.inaxes.set_xlim([xd - (xd - xl[0]) * s, xd + (xl[1] - xd) * s])
        event.inaxes.set_ylim([yd - (yd - yl[0]) * s, yd + (yl[1] - yd) * s])
        self._canvas.draw_idle()

    def _on_mw(self, event):
        if self._fig.gca() is None: return
        self._zoom(0.85 if event.delta > 0 else 1.15)

    def _zoom(self, scale):
        ax = self._fig.gca()
        if ax is None: return
        xl = ax.get_xlim(); yl = ax.get_ylim()
        xm = (xl[0] + xl[1]) / 2; ym = (yl[0] + yl[1]) / 2
        ax.set_xlim([xm - (xm - xl[0]) * scale, xm + (xl[1] - xm) * scale])
        ax.set_ylim([ym - (ym - yl[0]) * scale, ym + (yl[1] - ym) * scale])
        self._canvas.draw_idle()


class BarChartWindow(_Base):
    def __init__(self, parent, df, col="fans_base", n=15, title="TOP N", highlight_name=None):
        self._df = df; self._col = col; self._n = n; self._t = title; self._hl = highlight_name
        super().__init__(parent, title)

    def _build(self):
        setup_font()
        top = self._df.nlargest(self._n, self._col).sort_values(self._col, ascending=True)
        names = top["name"].values; vals = top[self._col].values
        ax = self._fig.add_subplot(111)
        colors = [C_DANGER if self._hl and nm == self._hl else C_BLUE for nm in names]
        self._bars = ax.barh(range(len(top)), vals, color=colors)
        ax.set_yticks(range(len(top)))
        if self._font_prop:
            ax.set_yticklabels(names, fontsize=9, fontproperties=self._font_prop)
            ax.set_title(self._t, fontsize=14, fontweight="bold", fontproperties=self._font_prop)
        else:
            ax.set_yticklabels(names, fontsize=9)
            ax.set_title(self._t, fontsize=14, fontweight="bold")
        ann_kw = dict(xy=(0, 0), fontsize=11, fontweight="bold",
                      bbox=dict(boxstyle="round,pad=0.4", fc="yellow", alpha=0.95),
                      visible=False)
        if self._font_name: ann_kw["fontfamily"] = self._font_name
        if self._font_prop: ann_kw["fontproperties"] = self._font_prop
        self._annot = ax.annotate("", **ann_kw)
        self._names = names; self._vals = vals
        self._fig.tight_layout()
        self._fig.canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _on_hover(self, event):
        if event.inaxes is None or event.xdata is None:
            self._annot.set_visible(False); self._canvas.draw_idle(); return
        for bar, nm, v in zip(self._bars, self._names, self._vals):
            if bar.contains(event)[0]:
                xl = event.inaxes.get_xlim(); yl = event.inaxes.get_ylim()
                self._annot.xy = (event.xdata + (xl[1]-xl[0])*0.03, event.ydata + (yl[1]-yl[0])*0.03)
                self._annot.set_text(f"{nm}: {v:,.0f}")
                self._annot.set_visible(True)
                self._canvas.draw_idle(); return
        self._annot.set_visible(False); self._canvas.draw_idle()


class HistogramWindow(_Base):
    def __init__(self, parent, df, col="fans_base", title="Distribution", bins=20,
                 highlight_name=None, highlight_value=None):
        self._df = df; self._col = col; self._t = title; self._b = bins
        self._hn = highlight_name; self._hv = highlight_value
        super().__init__(parent, title)

    def _build(self):
        setup_font()
        data = self._df[self._col].dropna()
        ax = self._fig.add_subplot(111)
        n, bins_out, self._patches = ax.hist(data, bins=self._b, color=C_BLUE,
                                              edgecolor="white", alpha=0.85)
        ax.axvline(data.median(), color="#888", linestyle="--", lw=1.5,
                   label=f"Median: {data.median():,.0f}")
        ax.axvline(data.mean(), color=C_ORANGE, linestyle="--", lw=1.5,
                   label=f"Mean: {data.mean():,.0f}")
        if self._hn and self._hv and self._hv > 0:
            ax.axvline(self._hv, color=C_DANGER, linestyle="-", lw=2.5,
                       label=f"{self._hn}: {self._hv:,.0f}")
        if self._font_prop:
            ax.set_title(self._t, fontsize=14, fontweight="bold", fontproperties=self._font_prop)
            ax.legend(prop=self._font_prop)
        else:
            ax.set_title(self._t, fontsize=14, fontweight="bold"); ax.legend()
        ann_kw = dict(xy=(0, 0), fontsize=11, fontweight="bold",
                      bbox=dict(boxstyle="round,pad=0.4", fc="yellow", alpha=0.95),
                      visible=False)
        if self._font_name: ann_kw["fontfamily"] = self._font_name
        if self._font_prop: ann_kw["fontproperties"] = self._font_prop
        self._annot = ax.annotate("", **ann_kw)
        self._n = n; self._bins_out = bins_out
        self._fig.tight_layout()
        self._fig.canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _on_hover(self, event):
        if event.inaxes is None or event.xdata is None:
            self._annot.set_visible(False); self._canvas.draw_idle(); return
        for p, cnt in zip(self._patches, self._n):
            if p.contains(event)[0]:
                x0 = p.get_x(); x1 = x0 + p.get_width()
                xl = event.inaxes.get_xlim(); yl = event.inaxes.get_ylim()
                self._annot.xy = (event.xdata + (xl[1]-xl[0])*0.04, event.ydata + (yl[1]-yl[0])*0.04)
                self._annot.set_text(f"[{x0:,.0f} - {x1:,.0f}]\nCount: {int(cnt)}")
                self._annot.set_visible(True)
                self._canvas.draw_idle(); return
        self._annot.set_visible(False); self._canvas.draw_idle()


class ScatterWindow(_Base):
    def __init__(self, parent, df, x="fans_base", y="play_base",
                 xl="Fans", yl="Plays", title="Fans vs Plays", highlight_name=None):
        self._df = df; self._x = x; self._y = y; self._xl = xl; self._yl = yl
        self._t = title; self._hl = highlight_name
        super().__init__(parent, title)

    def _build(self):
        setup_font()
        df = self._df
        nms = df["name"].values; xv = df[self._x].fillna(0).values; yv = df[self._y].fillna(0).values
        colors = np.full(len(df), C_BLUE, dtype=object)
        sz = np.full(len(df), 50.); al = np.full(len(df), 0.5)
        if self._hl:
            m = nms == self._hl; colors[m] = C_DANGER; sz[m] = 150; al[m] = 1.0
        ax = self._fig.add_subplot(111)
        ax.scatter(xv, yv, c=colors, s=sz, alpha=al, edgecolors="white", lw=0.5)
        for _, row in df.nlargest(5, self._y).iterrows():
            ih = self._hl and row["name"] == self._hl
            kw = dict(fontsize=8, color=C_DANGER if ih else "#333",
                      fontweight="bold" if ih else "normal", alpha=0.9,
                      xytext=(5, 5), textcoords="offset points",
                      bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))
            if self._font_prop: kw["fontproperties"] = self._font_prop
            ax.annotate(row["name"], (row[self._x], row[self._y]), **kw)
        if len(df) > 2:
            z = np.polyfit(xv, yv, 1); p = np.poly1d(z)
            xr = np.linspace(xv.min(), xv.max(), 100)
            ax.plot(xr, p(xr), "--", color=C_ORANGE, alpha=0.6)
        if self._font_prop:
            ax.set_xlabel(self._xl, fontproperties=self._font_prop)
            ax.set_ylabel(self._yl, fontproperties=self._font_prop)
            ax.set_title(self._t, fontsize=14, fontweight="bold", fontproperties=self._font_prop)
        else:
            ax.set_xlabel(self._xl); ax.set_ylabel(self._yl)
            ax.set_title(self._t, fontsize=14, fontweight="bold")

        self._nms = nms; self._xv = xv; self._yv = yv

        can_kw = dict(xy=(0, 0), fontsize=12, fontweight="bold", color=C_DANGER,
                      bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.95),
                      visible=False)
        if self._font_name: can_kw["fontfamily"] = self._font_name
        if self._font_prop: can_kw["fontproperties"] = self._font_prop
        self._can = ax.annotate("", **can_kw)

        hov_kw = dict(xy=(0, 0), fontsize=10,
                      bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", alpha=0.95),
                      visible=False)
        if self._font_name: hov_kw["fontfamily"] = self._font_name
        if self._font_prop: hov_kw["fontproperties"] = self._font_prop
        self._hover_ann = ax.annotate("", **hov_kw)

        self._fig.tight_layout()
        self._fig.canvas.mpl_connect("button_press_event", self._on_click)
        self._fig.canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _near(self, x, y):
        xr = max(self._xv) - min(self._xv) or 1
        yr = max(self._yv) - min(self._yv) or 1
        best, best_d = None, 1e9
        for i in range(len(self._xv)):
            d = ((self._xv[i] - x) / xr) ** 2 + ((self._yv[i] - y) / yr) ** 2
            if d < best_d: best_d = d; best = i
        if best is not None and best_d < 0.005: return best, self._nms[best]
        return None

    def _on_click(self, event):
        if event.inaxes is None or event.xdata is None:
            self._can.set_visible(False); self._canvas.draw_idle(); return
        r = self._near(event.xdata, event.ydata)
        if r is None:
            self._can.set_visible(False); self._canvas.draw_idle(); return
        i, nm = r
        self._can.xy = (self._xv[i], self._yv[i])
        self._can.set_text(nm)
        self._can.set_visible(True)
        self._canvas.draw_idle()

    def _on_hover(self, event):
        if event.inaxes is None or event.xdata is None:
            self._hover_ann.set_visible(False); self._canvas.draw_idle(); return
        r = self._near(event.xdata, event.ydata)
        if r is None:
            self._hover_ann.set_visible(False); self._canvas.draw_idle(); return
        i, nm = r
        xl = event.inaxes.get_xlim(); yl = event.inaxes.get_ylim()
        self._hover_ann.xy = (event.xdata + (xl[1]-xl[0])*0.03, event.ydata + (yl[1]-yl[0])*0.03)
        self._hover_ann.set_text(nm)
        self._hover_ann.set_visible(True)
        self._canvas.draw_idle()


class TrendWindow(_Base):
    """趋势分析窗口：Theil-Sen 稳健回归 + OLS 对比 + 异常点标注"""
    def __init__(self, parent, school_name, timestamps, values, labels,
                 robust_slope, ols_slope, intercept, spikes, time_span_days):
        self._sname = school_name
        self._ts = timestamps; self._vs = values; self._ls = labels
        self._rs = robust_slope; self._os = ols_slope; self._ic = intercept
        self._spikes = spikes; self._td = time_span_days
        super().__init__(parent, f"Trend: {school_name}")

    def _build(self):
        setup_font()
        ax = self._fig.add_subplot(111)

        # 原始数据散点
        ax.scatter(self._ts, self._vs, s=80, c="#4472C4", zorder=5,
                   edgecolors="white", linewidth=0.8)
        # 数据点标签
        for i, lbl in enumerate(self._ls):
            akw = dict(fontsize=7, xytext=(0, -12), textcoords="offset points",
                       ha="center", alpha=0.7)
            if self._font_prop: akw["fontproperties"] = self._font_prop
            ax.annotate(lbl, (self._ts[i], self._vs[i]), **akw)

        t_min, t_max = min(self._ts), max(self._ts)
        x_line = np.array([t_min, t_max])
        ts_arr = np.array(self._ts)
        vs_arr = np.array(self._vs)

        # Theil-Sen 稳健线
        if self._rs is not None:
            intercept_rs = np.median(vs_arr) - self._rs * np.median(ts_arr)
            y_line_rs = intercept_rs + self._rs * x_line
            ax.plot(x_line, y_line_rs, "-", color="#C00000", linewidth=2.5,
                    label=f"Theil-Sen (robust): {self._rs*86400:+.1f}/day", zorder=3)

        # OLS 线（虚线对比）
        if self._os is not None:
            y_line_ols = np.median(vs_arr) - self._os * np.median(ts_arr) + self._os * x_line
            ax.plot(x_line, y_line_ols, "--", color="#E67E22", linewidth=1.8,
                    label=f"OLS (nominal): {self._os*86400:+.1f}/day", zorder=3)

        # 异常点标注
        if self._spikes:
            spike_indices = [s[0] for s in self._spikes[:5]]
            spike_ts = [self._ts[i] for i in spike_indices]
            spike_vs = [self._vs[i] for i in spike_indices]
            ax.scatter(spike_ts, spike_vs, s=180, marker="D", c="#FF6B00",
                       edgecolors="#C00000", linewidth=1.5, zorder=6,
                       label=f"Spikes ({len(self._spikes)})")

        # 标签
        title_str = (f"Trend: {self._sname}  ({self._td:.0f} days, "
                     f"{len(self._ts)} snapshots)")
        if self._font_prop:
            ax.set_title(title_str, fontsize=14, fontweight="bold",
                         fontproperties=self._font_prop)
            ax.set_ylabel("Fans (base unit)", fontproperties=self._font_prop)
        else:
            ax.set_title(title_str, fontsize=14, fontweight="bold")
            ax.set_ylabel("Fans (base unit)")

        # X 轴用日期标签
        from datetime import datetime
        date_labels = [datetime.fromtimestamp(t).strftime("%m/%d") for t in self._ts]
        ax.set_xticks(self._ts)
        if self._font_prop:
            ax.set_xticklabels(date_labels, fontsize=8, rotation=30, ha="right",
                               fontproperties=self._font_prop)
        else:
            ax.set_xticklabels(date_labels, fontsize=8, rotation=30, ha="right")

        ax.legend(fontsize=9)
        self._fig.tight_layout()
        self._fig.canvas.mpl_connect("motion_notify_event", self._on_hover)

        # 悬停标注
        ann_kw = dict(xy=(0, 0), fontsize=10, fontweight="bold",
                      bbox=dict(boxstyle="round,pad=0.4", fc="yellow", alpha=0.95),
                      visible=False)
        if self._font_name: ann_kw["fontfamily"] = self._font_name
        if self._font_prop: ann_kw["fontproperties"] = self._font_prop
        self._annot = ax.annotate("", **ann_kw)

    def _on_hover(self, event):
        if event.inaxes is None or event.xdata is None:
            self._annot.set_visible(False); self._canvas.draw_idle(); return
        # 搜索最近数据点
        best, best_d = None, 1e9
        xr = max(self._ts) - min(self._ts) or 1
        yr = max(self._vs) - min(self._vs) or 1
        for i in range(len(self._ts)):
            d = ((self._ts[i] - event.xdata) / xr) ** 2 + ((self._vs[i] - event.ydata) / yr) ** 2
            if d < best_d: best_d = d; best = i
        if best is not None and best_d < 0.01:
            from datetime import datetime
            dt_str = datetime.fromtimestamp(self._ts[best]).strftime("%Y-%m-%d")
            xl = event.inaxes.get_xlim(); yl = event.inaxes.get_ylim()
            self._annot.xy = (event.xdata + (xl[1]-xl[0])*0.03,
                              event.ydata + (yl[1]-yl[0])*0.03)
            self._annot.set_text(f"{self._ls[best]}\n{dt_str}\n{self._vs[best]:,.0f}")
            self._annot.set_visible(True)
            self._canvas.draw_idle()
        else:
            self._annot.set_visible(False)
            self._canvas.draw_idle()


class DashboardWindow(tk.Toplevel):
    def __init__(self, parent, df, charts_config, highlight_name=None):
        super().__init__(parent)
        self.title("Dashboard"); self.geometry("1200x800"); self.minsize(800, 600)
        self.transient(parent)
        fp, fn = _resolve_cjk_font()
        self._fp = fp; self._fn = fn
        self._df = df; self._cfgs = charts_config; self._hl = highlight_name
        outer = ttk.Frame(self); outer.pack(fill="both", expand=True)
        self._cv = tk.Canvas(outer, bg="#ffffff", highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=self._cv.yview)
        self._inner = ttk.Frame(self._cv)
        self._inner.bind("<Configure>",
            lambda e: self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.create_window((0, 0), window=self._inner, anchor="nw")
        self._cv.configure(yscrollcommand=sb.set)
        self._cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._cv.bind("<MouseWheel>", lambda e: self._cv.yview_scroll(-1 * (e.delta // 120), "units"))
        self._cv.bind("<Button-4>", lambda e: self._cv.yview_scroll(-1, "units"))
        self._cv.bind("<Button-5>", lambda e: self._cv.yview_scroll(1, "units"))
        self._build_grid()
        self.bind("<Configure>", self._on_resize)

    def _build_grid(self):
        for w in self._inner.winfo_children(): w.destroy()
        n = len(self._cfgs)
        if n == 0: return
        ww = self.winfo_width()
        cols = 1 if ww < 700 else 2 if ww < 1100 else 3
        rows = (n + cols - 1) // cols
        for r in range(rows): self._inner.rowconfigure(r, weight=1)
        for c in range(cols): self._inner.columnconfigure(c, weight=1)
        cw = max(380, (ww - 40) // cols)
        fig_w = cw / 100; fig_h = fig_w * 0.75
        setup_font()
        for i, cfg in enumerate(self._cfgs):
            r, c = i // cols, i % cols
            fig = plt.figure(figsize=(fig_w, fig_h), dpi=100)
            ax = fig.add_subplot(111)
            ct = cfg.get("type", "bar")
            if ct == "bar":
                col = cfg.get("col", "fans_base"); nn = cfg.get("n", 15)
                top = self._df.nlargest(nn, col).sort_values(col, ascending=True)
                nms, vls = top["name"].values, top[col].values
                colors = [C_DANGER if self._hl and nm == self._hl else C_BLUE for nm in nms]
                ax.barh(range(len(top)), vls, color=colors)
                ax.set_yticks(range(len(top)))
                if self._fp:
                    ax.set_yticklabels(nms, fontsize=7, fontproperties=self._fp)
                    ax.set_title(cfg.get("title", "TOP N"), fontsize=10, fontweight="bold", fontproperties=self._fp)
                else:
                    ax.set_yticklabels(nms, fontsize=7)
                    ax.set_title(cfg.get("title", "TOP N"), fontsize=10, fontweight="bold")
            elif ct == "hist":
                col = cfg.get("col", "fans_base"); bins = cfg.get("bins", 20)
                data = self._df[col].dropna()
                ax.hist(data, bins=bins, color=C_BLUE, edgecolor="white", alpha=0.85)
                ax.axvline(data.median(), color="#888", linestyle="--", lw=1)
                ax.axvline(data.mean(), color=C_ORANGE, linestyle="--", lw=1)
                if self._hl:
                    wust = self._df[self._df["name"] == self._hl]
                    if len(wust) > 0: ax.axvline(wust.iloc[0][col], color=C_DANGER, linestyle="-", lw=2)
                if self._fp:
                    ax.set_title(cfg.get("title", "Dist"), fontsize=10, fontweight="bold", fontproperties=self._fp)
                else:
                    ax.set_title(cfg.get("title", "Dist"), fontsize=10, fontweight="bold")
            elif ct == "scatter":
                xc = cfg.get("x", "fans_base"); yc = cfg.get("y", "play_base")
                nms = self._df["name"].values
                xv = self._df[xc].fillna(0).values; yv = self._df[yc].fillna(0).values
                colors = np.full(len(self._df), C_BLUE, dtype=object)
                sz = np.full(len(self._df), 15.); al = np.full(len(self._df), 0.4)
                if self._hl:
                    m = nms == self._hl; colors[m] = C_DANGER; sz[m] = 60; al[m] = 1.0
                ax.scatter(xv, yv, c=colors, s=sz, alpha=al, edgecolors="white", lw=0.2)
                if self._fp:
                    ax.set_xlabel(cfg.get("xl", "Fans"), fontsize=8, fontproperties=self._fp)
                    ax.set_ylabel(cfg.get("yl", "Plays"), fontsize=8, fontproperties=self._fp)
                    ax.set_title(cfg.get("title", "Scatter"), fontsize=10, fontweight="bold", fontproperties=self._fp)
                else:
                    ax.set_xlabel(cfg.get("xl", "Fans"), fontsize=8)
                    ax.set_ylabel(cfg.get("yl", "Plays"), fontsize=8)
                    ax.set_title(cfg.get("title", "Scatter"), fontsize=10, fontweight="bold")
            fig.tight_layout(pad=1.5)
            frm = ttk.Frame(self._inner)
            frm.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            frm.columnconfigure(0, weight=1); frm.rowconfigure(0, weight=1)
            cw = FigureCanvasTkAgg(fig, frm); cw.draw()
            cw.get_tk_widget().pack(fill="both", expand=True)

    def _on_resize(self, event):
        if event.widget != self: return
        if not hasattr(self, '_lw'): self._lw = 0
        if abs(self.winfo_width() - self._lw) > 50:
            self._lw = self.winfo_width()
            self._build_grid()
