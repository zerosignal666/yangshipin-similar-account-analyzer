"""Tkinter GUI —— Python 内置，零额外依赖，完整版"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading, queue, csv, os, time
from datetime import datetime
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from ..models.database import (init_db, get_all_snapshots, get_snapshot_data,
    get_snapshot, delete_snapshot, get_setting, set_setting, can_crawl,
    get_last_crawl_time, reset_crawl_log)
from ..models.schema import format_value, DISPLAY_UNITS, auto_unit
from ..crawler.url_parser import parse_account_file
from ..analysis.stats import to_dataframe, compute_stats, compare_snapshots
from ..analysis.charts import bar_top_n, setup_font, get_cjk_font
from .workers import CrawlThread

CBG = "#f5f5f5"; CPRI = "#4472C4"; CRED = "#C00000"; CGRN = "#2E7D32"
CWR = "#E67E22"; CWHT = "#ffffff"; CPUR = "#7B1FA2"

# ═══════════════════════════════════════════════════════
#  Crawl Tab
# ═══════════════════════════════════════════════════════
class CrawlTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent); self.app = app
        self._thread = None; self._accounts = []
        self._build(); self._load_accounts()

    def _build(self):
        self.columnconfigure(0, weight=1)
        info = ttk.LabelFrame(self, text="Crawl Info", padding=10)
        info.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,5))
        info.columnconfigure(1, weight=1)
        ttk.Label(info, text="Accounts:").grid(row=0, column=0, sticky="w")
        self.lbl_total = ttk.Label(info, text="--", font=("",12,"bold"), foreground=CPRI)
        self.lbl_total.grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(info, text="Last crawl:").grid(row=1, column=0, sticky="w")
        self.lbl_last = ttk.Label(info, text="--")
        self.lbl_last.grid(row=1, column=1, sticky="w", padx=10)
        ttk.Label(info, text="Rate limit:").grid(row=0, column=2, sticky="w")
        self.lbl_limit = ttk.Label(info, text="--")
        self.lbl_limit.grid(row=0, column=3, sticky="w", padx=10)
        ttk.Label(info, text="Interval:").grid(row=1, column=2, sticky="w")
        self.lbl_interval = ttk.Label(info, text="--")
        self.lbl_interval.grid(row=1, column=3, sticky="w", padx=10)

        btn = ttk.Frame(self); btn.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.btn_start = tk.Button(btn, text="Start Crawl", bg=CPRI, fg="white",
            font=("",11,"bold"), relief="flat", padx=20, pady=4, command=self._start)
        self.btn_start.pack(side="left", padx=(0,8))
        self.btn_pause = tk.Button(btn, text="Pause", state="disabled", padx=12, command=self._toggle_pause)
        self.btn_pause.pack(side="left", padx=4)
        self.btn_stop = tk.Button(btn, text="Stop", state="disabled", fg=CRED, padx=12, command=self._stop)
        self.btn_stop.pack(side="left", padx=4)
        tk.Button(btn, text="Reset Limit", padx=12, command=self._reset_limit).pack(side="right", padx=4)

        frm = ttk.Frame(self); frm.grid(row=2, column=0, sticky="ew", padx=10, pady=(5,0))
        self.progress = ttk.Progressbar(frm, mode="determinate"); self.progress.pack(fill="x")
        self.lbl_progress = ttk.Label(frm, text=""); self.lbl_progress.pack(anchor="w", pady=(2,0))

        ttk.Label(self, text="Log:", font=("",10,"bold")).grid(row=3, column=0, sticky="w", padx=10, pady=(8,0))
        self.log = scrolledtext.ScrolledText(self, height=18, font=("Consolas",10), state="disabled", wrap="word")
        self.log.grid(row=4, column=0, sticky="nsew", padx=10, pady=(2,10))
        self.rowconfigure(4, weight=1)
        for t,c in [("ok",CGRN),("error",CRED),("warn",CWR),("info","black")]:
            self.log.tag_config(t, foreground=c)

    def _load_accounts(self):
        self._accounts = parse_account_file()
        self.lbl_total.config(text=str(len(self._accounts)))

    def refresh(self):
        self._load_accounts()
        last = get_last_crawl_time()
        self.lbl_last.config(text=last[:19] if last else "never")
        d = get_setting("rate_limit_days","7"); c = get_setting("rate_limit_count","2")
        self.lbl_limit.config(text=f"{d}d max {c} times")
        self.lbl_interval.config(text=f"{get_setting('request_interval','3')}s/req")

    def _log(self, msg, level="info"):
        self.log.config(state="normal")
        self.log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n", level)
        self.log.see("end"); self.log.config(state="disabled")

    def _start(self):
        if not self._accounts: messagebox.showwarning("Warning","No accounts found."); return
        d=int(get_setting("rate_limit_days","7")); c=int(get_setting("rate_limit_count","2"))
        ok,reason=can_crawl(d,c)
        if not ok:
            if not messagebox.askyesno("Rate Limit",f"{reason}\n\nForce start?"): return
        self.log.config(state="normal"); self.log.delete("1.0","end"); self.log.config(state="disabled")
        self._log("Starting crawl...","info")
        snap_name = f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._thread = CrawlThread(self._accounts, snap_name)
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="Pause")
        self.btn_stop.config(state="normal")
        self.progress["maximum"]=len(self._accounts); self.progress["value"]=0
        self._thread.start(); self._poll()

    def _poll(self):
        if self._thread is None: return
        t=self._thread
        try:
            while True:
                kind,data=t.mq.get_nowait()
                if kind=="log": self._log(data[0],data[1])
                elif kind=="progress":
                    c,total,name,status,msg=data
                    self.progress["value"]=c
                    self.lbl_progress.config(text=f"[{c}/{total}] {'OK' if status=='ok' else 'FAIL'}: {name}  {msg}")
                elif kind=="done":
                    sid,total,ok,fail=data
                    self._log("="*50,"info")
                    self._log(f"CRAWL DONE: {ok} ok, {fail} fail, {total} total","ok" if fail==0 else "warn")
                    self.btn_start.config(state="normal")
                    self.btn_pause.config(state="disabled", text="Pause")
                    self.btn_stop.config(state="disabled")
                    self.progress["value"]=0; self.lbl_progress.config(text="")
                    self.refresh(); self.app.on_crawl_done(sid)
                    self._thread=None; return
        except queue.Empty: pass
        if t.is_alive(): self.after(100, self._poll)
        else: self._thread=None

    def _toggle_pause(self):
        if self._thread is None: return
        if self.btn_pause.cget("text")=="Pause":
            self._thread.pause(); self.btn_pause.config(text="Resume")
            self._log("-- PAUSED --","warn")
        else:
            self._thread.resume(); self.btn_pause.config(text="Pause")
            self._log("-- RESUMED --","info")

    def _stop(self):
        if self._thread: self._thread.stop()
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled", text="Pause")
        self.btn_stop.config(state="disabled")
        self._log("-- STOPPED --","warn"); self.refresh()

    def _reset_limit(self):
        if messagebox.askyesno("Confirm","Reset rate limit counter?"):
            reset_crawl_log(); self._log("Rate limit reset","warn"); self.refresh()

# ═══════════════════════════════════════════════════════
#  Data Table Tab
# ═══════════════════════════════════════════════════════
class DataTableTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent); self.app = app
        self._data = []; self._visible = []
        self._unit = tk.StringVar(value="万"); self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        bar = ttk.Frame(self); bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,5))
        ttk.Label(bar, text="Snapshot:").pack(side="left")
        self.cb_snap = ttk.Combobox(bar, state="readonly", width=35)
        self.cb_snap.pack(side="left", padx=5)
        self.cb_snap.bind("<<ComboboxSelected>>", self._on_snap)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=15)
        ttk.Label(bar, text="Unit:").pack(side="left")
        cb = ttk.Combobox(bar, textvariable=self._unit, values=DISPLAY_UNITS, state="readonly", width=5)
        cb.pack(side="left", padx=5)
        cb.bind("<<ComboboxSelected>>", lambda e: self._reload())
        ttk.Label(bar, text="Search:").pack(side="left", padx=(15,5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._apply_filter())
        ttk.Entry(bar, textvariable=self.search_var, width=18).pack(side="left")
        tk.Button(bar, text="Export CSV", padx=12, command=self._export).pack(side="right", padx=4)

        self.lbl_status = ttk.Label(self, text="")
        self.lbl_status.grid(row=1, column=0, sticky="w", padx=10)

        ft = ttk.Frame(self); ft.grid(row=2, column=0, sticky="nsew", padx=10, pady=(2,10))
        ft.columnconfigure(0, weight=1); ft.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        cols = ("rank","name","fans","plays","videos","desc")
        self.tree = ttk.Treeview(ft, columns=cols, show="headings", selectmode="extended")
        headings = [("rank","#",lambda:self._sort("fans_base",True)),
                    ("name","Name",lambda:self._sort("name",False)),
                    ("fans","Fans",lambda:self._sort("fans_base",True)),
                    ("plays","Plays",lambda:self._sort("play_base",True)),
                    ("videos","Videos",lambda:self._sort("video_cnt",True)),
                    ("desc","Description")]
        for item in headings:
            if len(item)==3:
                self.tree.heading(item[0], text=item[1], command=item[2])
            else:
                self.tree.heading(item[0], text=item[1])
        self.tree.column("rank", width=45, anchor="center")
        self.tree.column("name", width=150); self.tree.column("fans", width=100, anchor="center")
        self.tree.column("plays", width=100, anchor="center")
        self.tree.column("videos", width=70, anchor="center")
        self.tree.column("desc", width=280)

        vsb = ttk.Scrollbar(ft, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns")

        # WUST 红色高亮标签
        self.tree.tag_configure("hl", foreground=CRED, font=("",10,"bold"))
        self._sort_col = "fans_base"; self._sort_desc = True

    def refresh_snapshots(self):
        snaps = get_all_snapshots()
        items = [f"{s['name']} ({s['created_at'][:16]}) - {s['success_count']}/{s['total_count']}" for s in snaps]
        self.cb_snap["values"] = items; self._snapshots = snaps
        if snaps: self.cb_snap.current(0); self._on_snap()

    def _on_snap(self, event=None):
        idx = self.cb_snap.current()
        if idx<0 or idx>=len(self._snapshots): return
        self._data = get_snapshot_data(self._snapshots[idx]["id"]); self._apply_filter()

    def _reload(self): self._apply_filter()

    def _fmt(self, base_val, orig_unit=""):
        if base_val is None or base_val==0: return "-"
        v,u = format_value(base_val, self._unit.get())
        if v>=10000: return f"{v:,.0f} {u}"
        if v>=100: return f"{v:,.1f} {u}"
        if v>=1: return f"{v:,.2f} {u}"
        return f"{v:,.4f} {u}"

    def _apply_filter(self):
        txt = self.search_var.get().strip().lower()
        for item in self.tree.get_children(): self.tree.delete(item)
        visible = self._data
        if txt: visible = [d for d in visible if txt in d.get("name","").lower()]
        H="武汉科技大学"
        for i,d in enumerate(visible):
            tags = ("hl",) if d.get("name","")==H else ()
            self.tree.insert("","end",iid=str(i), values=(
                i+1, d["name"],
                self._fmt(d["fans_base"], d.get("fans_unit","")),
                self._fmt(d["play_base"], d.get("play_unit","")),
                str(d.get("video_cnt",0)),
                d.get("description",""),
            ), tags=tags)
        self.lbl_status.config(text=f"{len(visible)} records")
        self._visible = visible

    def _sort(self, col, numeric):
        if self._sort_col==col: self._sort_desc = not self._sort_desc
        else: self._sort_col=col; self._sort_desc=numeric
        if numeric: self._data.sort(key=lambda x: x.get(col,0) or 0, reverse=self._sort_desc)
        else: self._data.sort(key=lambda x: str(x.get(col,"")).lower(), reverse=self._sort_desc)
        self._apply_filter()

    def _export(self):
        idx = self.cb_snap.current()
        if idx<0: return
        snap = get_snapshot(self._snapshots[idx]["id"])
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")],
                                            initialfile=f"ysp_{snap['name']}.csv")
        if not path: return
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                w=csv.writer(f)
                w.writerow(["#","Name","Fans","Plays","Videos","Description","CPID"])
                for i,d in enumerate(self._data):
                    w.writerow([i+1,d["name"],self._fmt(d["fans_base"],d.get("fans_unit","")),
                        self._fmt(d["play_base"],d.get("play_unit","")),d["video_cnt"],
                        d.get("description",""),d["cp_id"]])
            messagebox.showinfo("OK",f"Exported to:\n{path}")
        except Exception as e: messagebox.showerror("Error",str(e))

# ═══════════════════════════════════════════════════════
#  Analysis Tab
# ═══════════════════════════════════════════════════════
class AnalysisTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent); self.app = app
        self._snapshots = []; self._chart_vars = {}; self._chart_cfgs = {}
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        nb = ttk.Notebook(self); nb.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.rowconfigure(0, weight=1)
        f1 = ttk.Frame(nb); nb.add(f1, text="Single Snapshot"); self._build_single(f1)
        f2 = ttk.Frame(nb); nb.add(f2, text="Compare Snapshots"); self._build_compare(f2)

    # ── Single ────────────────────────────────────
    def _build_single(self, p):
        p.columnconfigure(0, weight=1); p.rowconfigure(2, weight=1)

        bar = ttk.Frame(p); bar.grid(row=0, column=0, sticky="ew", pady=(8,5), padx=8)
        ttk.Label(bar, text="Snapshot:").pack(side="left")
        self.cb_s1 = ttk.Combobox(bar, state="readonly", width=25)
        self.cb_s1.pack(side="left", padx=3)
        ttk.Label(bar, text="TOP N:").pack(side="left", padx=(10,2))
        self.sv_topn = tk.StringVar(value="15")
        ttk.Spinbox(bar, textvariable=self.sv_topn, from_=5, to=100, width=4).pack(side="left")
        ttk.Label(bar, text="Highlight:").pack(side="left", padx=(10,2))
        self.sv_hl = tk.StringVar(value="武汉科技大学")
        ttk.Entry(bar, textvariable=self.sv_hl, width=13).pack(side="left")
        tk.Button(bar, text="Analyze", bg=CPRI, fg="white",
            font=("",10,"bold"), padx=16, command=self._run_single).pack(side="left", padx=10)

        self.txt_stats = tk.Text(p, height=6, font=("Consolas",10), state="disabled", wrap="word", bg="#fafafa")
        self.txt_stats.grid(row=1, column=0, sticky="ew", padx=8, pady=(0,5))

        self._chart_panel = ttk.LabelFrame(p, text="Charts", padding=8)
        self._chart_panel.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0,8))
        self._chart_panel.columnconfigure(0, weight=1)
        # 初始提示
        ttk.Label(self._chart_panel, text="Click [Analyze] to generate chart options.",
                  foreground="#888").pack(pady=20)

    # ── Compare ───────────────────────────────────
    def _build_compare(self, p):
        p.columnconfigure(0, weight=1); p.rowconfigure(4, weight=1)
        bar = ttk.Frame(p); bar.grid(row=0, column=0, sticky="ew", pady=(8,5), padx=8)
        ttk.Label(bar, text="A (base):").pack(side="left")
        self.cb_a = ttk.Combobox(bar, state="readonly", width=25)
        self.cb_a.pack(side="left", padx=3)
        ttk.Label(bar, text="B (compare):").pack(side="left", padx=(15,3))
        self.cb_b = ttk.Combobox(bar, state="readonly", width=25)
        self.cb_b.pack(side="left", padx=3)
        tk.Button(bar, text="Compare", bg=CRED, fg="white",
            font=("",10,"bold"), padx=16, command=self._run_compare).pack(side="left", padx=10)

        # 搜索栏
        sbar = ttk.Frame(p); sbar.grid(row=1, column=0, sticky="ew", pady=(2,5), padx=8)
        ttk.Label(sbar, text="Search School:").pack(side="left")
        self.sv_cmp_search = tk.StringVar()
        ttk.Entry(sbar, textvariable=self.sv_cmp_search, width=20).pack(side="left", padx=5)
        tk.Button(sbar, text="Search", padx=10, command=self._on_cmp_search).pack(side="left", padx=2)
        tk.Button(sbar, text="Clear", padx=8, command=self._clear_cmp_search).pack(side="left")
        # 搜索反馈标签
        self._cmp_status = ttk.Label(sbar, text="", foreground="#888")
        self._cmp_status.pack(side="left", padx=8)

        # 搜索结果列表（最多5条，点击可查看详情）
        self._cmp_result_lb = tk.Listbox(p, height=0, font=("",10),
                                          selectmode="single", exportselection=False,
                                          bg="#fffbe6", activestyle="none")
        self._cmp_result_lb.grid(row=2, column=0, sticky="ew", padx=8)
        self._cmp_result_lb.grid_remove()  # 初始隐藏
        self._cmp_result_lb.bind("<<ListboxSelect>>", self._on_cmp_select)
        self._cmp_last_result = None  # 缓存上次对比结果
        self._cmp_matches = []

        self.txt_compare = tk.Text(p, height=6, font=("Consolas",10), state="disabled", wrap="word", bg="#fafafa")
        self.txt_compare.grid(row=3, column=0, sticky="ew", padx=8, pady=(0,5))

        self._cmp_chart = ttk.Frame(p); self._cmp_chart.grid(row=4, column=0, sticky="nsew", padx=8, pady=(0,8))
        self._cmp_canvas = tk.Canvas(self._cmp_chart, bg=CWHT)
        self._cmp_scroll = ttk.Scrollbar(self._cmp_chart, orient="vertical", command=self._cmp_canvas.yview)
        self._cmp_inner = ttk.Frame(self._cmp_canvas)
        self._cmp_inner.bind("<Configure>",
            lambda e: self._cmp_canvas.configure(scrollregion=self._cmp_canvas.bbox("all")))
        self._cmp_canvas.create_window((0,0), window=self._cmp_inner, anchor="nw")
        self._cmp_canvas.configure(yscrollcommand=self._cmp_scroll.set)
        self._cmp_canvas.pack(side="left", fill="both", expand=True)
        self._cmp_scroll.pack(side="right", fill="y")

    # ── 公共 ──────────────────────────────────────
    def refresh_snapshots(self):
        self._snapshots = get_all_snapshots()
        items = [f"{s['name']} ({s['created_at'][:16]})" for s in self._snapshots]
        for cb in [self.cb_s1, self.cb_a, self.cb_b]:
            cb["values"] = items
        if items:
            self.cb_s1.current(0); self.cb_a.current(0)
            if len(items)>=2: self.cb_b.current(len(items)-1)

    def _get_snap(self, combo):
        idx = combo.current()
        if idx<0: return None,None
        s = self._snapshots[idx]; return s, get_snapshot_data(s["id"])

    def _clear(self, frm):
        for w in frm.winfo_children(): w.destroy()

    def _add_fig(self, fig, target):
        c = FigureCanvasTkAgg(fig, target); c.draw()
        c.get_tk_widget().pack(fill="x", pady=4)

    # ── 单快照分析 ──────────────────────────────
    def _run_single(self):
        snap, data = self._get_snap(self.cb_s1)
        if not data: return
        df = to_dataframe(data); st = compute_stats(df)
        top_n = int(self.sv_topn.get() or "15")
        hl = self.sv_hl.get().strip() or None

        # 统计摘要
        self.txt_stats.config(state="normal"); self.txt_stats.delete("1.0","end")
        ft,fu=auto_unit(st["fans"]["sum"]); pt,pu=auto_unit(st["plays"]["sum"])
        wline = ""
        if hl:
            w = df[df["name"]==hl]
            if len(w)>0:
                w=w.iloc[0]; wf,wfu=auto_unit(w["fans_base"]); wp,wpu=auto_unit(w["play_base"])
                rank = (df["fans_base"]>w["fans_base"]).sum()+1
                wline = (f"\n*** {hl} ***  Rank #{rank}  |  "
                         f"Fans: {wf:,.1f}{wfu}  |  Plays: {wp:,.1f}{wpu}  |  Videos: {int(w['video_cnt']):,}\n")
        self.txt_stats.insert("end",
            f"Accounts: {st['total']}\n{'='*60}{wline}{'='*60}\n"
            f"Fans  Total: {ft:,.1f}{fu}   Mean: {st['fans']['mean']:,.0f}   "
            f"Median: {st['fans']['median']:,.0f}   Max: {st['fans']['max']:,.0f}\n"
            f"Plays Total: {pt:,.1f}{pu}   Mean: {st['plays']['mean']:,.0f}   "
            f"Median: {st['plays']['median']:,.0f}   Max: {st['plays']['max']:,.0f}\n"
            f"Videos Total: {st['videos']['sum']:,}   Mean: {st['videos']['mean']:,.1f}   "
            f"Median: {st['videos']['median']:,.0f}   Max: {st['videos']['max']:,}")
        self.txt_stats.config(state="disabled")

        # 重建图表按钮面板
        self._clear(self._chart_panel)
        self._chart_vars.clear(); self._chart_cfgs.clear()

        hl_val = None
        if hl:
            w = df[df["name"]==hl]
            if len(w)>0: hl_val = w.iloc[0]["fans_base"]

        # 每个图表一行：checkbox + 名称 + View按钮
        charts = [
            ("1","Fans TOP N Bar",        "bar",  dict(df=df, col="fans_base", n=top_n, title=f"Fans TOP {top_n}", hl=hl)),
            ("2","Plays TOP N Bar",       "bar",  dict(df=df, col="play_base", n=top_n, title=f"Plays TOP {top_n}", hl=hl)),
            ("3","Fans Distribution",     "hist", dict(df=df, col="fans_base", title="Fans Distribution", bins=20, hl=hl, hlv=hl_val)),
            ("4","Fans vs Plays Scatter","scat",  dict(df=df, xc="fans_base", yc="play_base", xl="Fans", yl="Plays", title="Fans vs Plays", hl=hl)),
        ]
        for key,label,ctype,cfg in charts:
            rowf = ttk.Frame(self._chart_panel); rowf.pack(fill="x", pady=3)
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(rowf, variable=var).pack(side="left", padx=(5,8))
            self._chart_vars[key]=var; self._chart_cfgs[key]=(ctype,cfg,label)
            ttk.Label(rowf, text=label, font=("",10)).pack(side="left")
            tk.Button(rowf, text="View", padx=14, command=lambda k=key: self._open_chart(k)).pack(side="right", padx=(0,5))

        sep = ttk.Separator(self._chart_panel, orient="horizontal"); sep.pack(fill="x", pady=8)
        tk.Button(self._chart_panel, text="Open Dashboard (selected charts in grid)",
            bg=CWR, fg="white", font=("",11,"bold"), padx=20, pady=6,
            command=self._open_dashboard).pack(pady=4)

    def _open_chart(self, key):
        info = self._chart_cfgs.get(key)
        if not info: return
        ctype, cfg, label = info
        from .chart_windows import BarChartWindow, HistogramWindow, ScatterWindow
        if ctype == "bar":
            BarChartWindow(self, df=cfg["df"], col=cfg["col"], n=cfg["n"],
                           title=cfg["title"], highlight_name=cfg["hl"])
        elif ctype == "hist":
            HistogramWindow(self, df=cfg["df"], col=cfg["col"], title=cfg["title"],
                            bins=cfg["bins"], highlight_name=cfg["hl"],
                            highlight_value=cfg["hlv"])
        elif ctype == "scat":
            ScatterWindow(self, df=cfg["df"], x=cfg["xc"], y=cfg["yc"],
                          xl=cfg["xl"], yl=cfg["yl"], title=cfg["title"],
                          highlight_name=cfg["hl"])

    def _open_dashboard(self):
        selected = []
        for key, var in self._chart_vars.items():
            if var.get():
                ctype, cfg, label = self._chart_cfgs[key]
                dc = {"type": ctype if ctype!="scat" else "scatter", "title": label}
                if ctype=="bar": dc.update(col=cfg["col"], n=cfg["n"])
                elif ctype=="hist": dc.update(col=cfg["col"], bins=cfg["bins"])
                else: dc.update(x=cfg["xc"], y=cfg["yc"], xl=cfg["xl"], yl=cfg["yl"])
                selected.append(dc)
        if not selected: messagebox.showwarning("Dashboard","Please select at least one chart."); return
        df = self._chart_cfgs.get("1",(None,{},None))[1].get("df")
        if df is None: return
        hl = self.sv_hl.get().strip() or None
        from .chart_windows import DashboardWindow
        DashboardWindow(self, df, selected, highlight_name=hl)

    # ── 双快照对比 ──────────────────────────────
    def _run_compare(self):
        snap_a, data_a = self._get_snap(self.cb_a)
        snap_b, data_b = self._get_snap(self.cb_b)
        if not data_a or not data_b: return
        if snap_a["id"]==snap_b["id"]: messagebox.showwarning("Warning","Select two different snapshots"); return

        # 自动判断时间顺序：A 必须是较早的快照
        swapped = False
        if snap_a.get("created_at") and snap_b.get("created_at"):
            if snap_a["created_at"] > snap_b["created_at"]:
                snap_a, snap_b = snap_b, snap_a
                data_a, data_b = data_b, data_a
                swapped = True

        na,nb = snap_a["name"],snap_b["name"]
        r = compare_snapshots(data_a, data_b, na, nb); s=r["summary"]
        hl = self.sv_hl.get().strip() or None

        self.txt_compare.config(state="normal"); self.txt_compare.delete("1.0","end")
        swap_note = "*** Auto-swapped: A was newer than B, reversed for correct comparison ***\n" if swapped else ""
        self.txt_compare.insert("end",
            f"Compare: [{na}] vs [{nb}]\n{'='*60}\n{swap_note}"
            f"Fans:  {s[f'fans_{na}']:,.0f} -> {s[f'fans_{nb}']:,.0f}  (chg: {s['fans_chg']:+,.0f})\n"
            f"Plays: {s[f'play_{na}']:,.0f} -> {s[f'play_{nb}']:,.0f}  (chg: {s['play_chg']:+,.0f})\n"
            f"Videos:{s[f'video_{na}']:,} -> {s[f'video_{nb}']:,}  (chg: {s['video_chg']:+,})\n"
            f"Accts: {s['acct_chg']:+d}  (new: {len(r['new'])}, gone: {len(r['gone'])})")
        self.txt_compare.config(state="disabled")

        # 缓存结果，供搜索使用
        self._cmp_last_result = r
        self._clear_cmp_search()

        self._clear(self._cmp_inner)

        # 1. 粉丝增长 TOP 10
        if r["fans_growth"]:
            self._add_growth_chart(r["fans_growth"], "fans_chg", "Fans Growth TOP 10",
                                    "粉丝增长", CPUR, hl)

        # 2. 播放量增长 TOP 10
        if r["play_growth"]:
            self._add_growth_chart(r["play_growth"], "play_chg", "Plays Growth TOP 10",
                                    "播放量增长", CGRN, hl)

        # 3. 视频增长 TOP 10
        if r["video_growth"]:
            self._add_growth_chart(r["video_growth"], "video_chg", "Video Growth TOP 10",
                                    "视频增长", CPRI, hl)

        # 4. 播放增长/新发视频 TOP 10 (仅当 video_chg>0 时有效)
        if r["ppv_growth"]:
            self._add_growth_chart(r["ppv_growth"], "play_per_video", "Play/Video Ratio TOP 10",
                                    "播放增长/新视频", CWR, hl, fmt=",.1f")

    def _add_growth_chart(self, data, col, title, cn_label, color, hl, fmt=",.0f"):
        """通用增长柱状图"""
        gd = sorted(data[:10], key=lambda x: x[col] or 0)
        fig, ax = plt.subplots(figsize=(10, 5))
        setup_font(); cjk = get_cjk_font()
        names = [d["name"] for d in gd]
        vals = [d[col] if d[col] is not None else 0 for d in gd]
        colors = [color if v >= 0 else "#999999" for v in vals]
        if hl:
            colors = [CRED if n == hl else c for n, c in zip(names, colors)]
        ax.barh(range(len(names)), vals, color=colors)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=9, fontproperties=cjk)
        ax.set_title(title, fontsize=14, fontweight="bold", fontproperties=cjk)
        ax.axvline(0, color="black", linewidth=0.5)
        # 在柱子上显示数值
        for i, v in enumerate(vals):
            xpos = max(v, 0) + max(vals)*0.01 if v >= 0 else v - max(abs(vv) for vv in vals)*0.01
            ha = "left" if v >= 0 else "right"
            ax.text(xpos, i, f" {v:{fmt}}", va="center", ha=ha, fontsize=8,
                    fontproperties=cjk)
        fig.tight_layout(); self._add_fig(fig, self._cmp_inner)

    def _on_cmp_search(self):
        """搜索按钮：显示最多5个匹配高校"""
        r = self._cmp_last_result
        # 还没点 Compare
        if not r:
            self._cmp_status.config(text="Please click [Compare] first", foreground=CRED)
            return
        txt = self.sv_cmp_search.get().strip()
        self._cmp_result_lb.delete(0, "end")
        self._cmp_result_lb.grid_remove()
        self._cmp_matches = []
        if not txt:
            self._cmp_status.config(text="")
            return
        # 模糊匹配，最多5条
        matches = []
        for d in r.get("all", []):
            if txt.lower() in d.get("name", "").lower():
                matches.append(d)
                if len(matches) >= 5:
                    break
        if matches:
            for d in matches:
                self._cmp_result_lb.insert("end", d["name"])
            self._cmp_result_lb.configure(height=len(matches))
            self._cmp_result_lb.grid()  # 显示
            self._cmp_matches = matches
            self._cmp_status.config(text=f"{len(matches)} match(es) — click to view detail",
                                    foreground=CGRN)
        else:
            self._cmp_status.config(text=f"No match for '{txt}'", foreground=CRED)

    def _on_cmp_select(self, event):
        """点击搜索结果：在摘要区显示该校详细对比"""
        sel = self._cmp_result_lb.curselection()
        if not sel or not self._cmp_matches:
            return
        d = self._cmp_matches[sel[0]]
        # 高亮选中项
        for i in range(self._cmp_result_lb.size()):
            self._cmp_result_lb.itemconfig(i, bg="#fffbe6")
        self._cmp_result_lb.itemconfig(sel[0], bg="#b3d9ff")

        self.txt_compare.config(state="normal")
        text = self.txt_compare.get("1.0", "end-1c")
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("*** Search:")]
        text = "\n".join(lines)
        fchg = d.get("fans_chg", 0) or 0
        pchg = d.get("play_chg", 0) or 0
        vchg = d.get("video_chg", 0) or 0
        ppv = d.get("play_per_video", None)
        ppv_str = f"{ppv:,.1f}" if ppv is not None and ppv == ppv else "N/A"
        search_line = (f"*** Search: {d['name']} ***  "
                      f"Fans chg: {fchg:+,.0f}  "
                      f"Plays chg: {pchg:+,.0f}  "
                      f"Videos chg: {vchg:+,.0f}  "
                      f"Play/Video: {ppv_str}")
        self.txt_compare.delete("1.0", "end")
        self.txt_compare.insert("end", text + "\n" + search_line)
        self.txt_compare.config(state="disabled")

    def _clear_cmp_search(self):
        """清除搜索"""
        self.sv_cmp_search.set("")
        self._cmp_result_lb.delete(0, "end")
        self._cmp_result_lb.grid_remove()
        self._cmp_matches = []
        self._cmp_status.config(text="")
        if self._cmp_last_result:
            self.txt_compare.config(state="normal")
            text = self.txt_compare.get("1.0", "end-1c")
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("*** Search:")]
            self.txt_compare.delete("1.0", "end")
            self.txt_compare.insert("end", "\n".join(lines))
            self.txt_compare.config(state="disabled")

# ═══════════════════════════════════════════════════════
#  Settings Dialog
# ═══════════════════════════════════════════════════════
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent); self.title("Settings")
        self.resizable(False,False); self.transient(parent)
        self._build(); self._load()

    def _build(self):
        f=ttk.Frame(self,padding=20); f.pack(fill="both")
        r=[0]
        def a(l,v,w=10):
            ttk.Label(f,text=l).grid(row=r[0],column=0,sticky="w",pady=3)
            ttk.Entry(f,textvariable=v,width=w).grid(row=r[0],column=1,sticky="ew",pady=3,padx=(15,0))
            r[0]+=1
        self.sv_int=tk.StringVar(); a("Request Interval (s):",self.sv_int)
        self.sv_con=tk.StringVar(); a("Concurrency:",self.sv_con)
        self.sv_to=tk.StringVar(); a("Timeout (s):",self.sv_to)
        self.sv_ret=tk.StringVar(); a("Max Retries:",self.sv_ret)
        self.sv_day=tk.StringVar(); a("Rate Window (days):",self.sv_day)
        self.sv_cnt=tk.StringVar(); a("Max Crawls/Window:",self.sv_cnt)
        ttk.Separator(f,orient="horizontal").grid(row=r[0],column=0,columnspan=2,sticky="ew",pady=15)
        r[0]+=1
        b=ttk.Frame(f); b.grid(row=r[0],column=0,columnspan=2)
        tk.Button(b,text="Save",bg=CPRI,fg="white",padx=20,command=self._save).pack(side="left",padx=5)
        tk.Button(b,text="Cancel",padx=20,command=self.destroy).pack(side="left",padx=5)

    def _load(self):
        for v,k in [(self.sv_int,"request_interval","3"),(self.sv_con,"max_concurrency","3"),
                     (self.sv_to,"timeout_seconds","30"),(self.sv_ret,"max_retries","3"),
                     (self.sv_day,"rate_limit_days","7"),(self.sv_cnt,"rate_limit_count","2")]:
            v.set(get_setting(k,default))

    def _save(self):
        for v,k in [(self.sv_int,"request_interval"),(self.sv_con,"max_concurrency"),
                     (self.sv_to,"timeout_seconds"),(self.sv_ret,"max_retries"),
                     (self.sv_day,"rate_limit_days"),(self.sv_cnt,"rate_limit_count")]:
            set_setting(k,v.get())
        messagebox.showinfo("OK","Settings saved."); self.destroy()

# ═══════════════════════════════════════════════════════
#  Snapshot Manager
# ═══════════════════════════════════════════════════════
class SnapshotManager(tk.Toplevel):
    def __init__(self, parent, on_change=None):
        super().__init__(parent); self.title("Snapshot Manager")
        self.geometry("500x420"); self.transient(parent)
        self._cb=on_change; self._build(); self._refresh()

    def _build(self):
        f=ttk.Frame(self,padding=15); f.pack(fill="both",expand=True)
        f.columnconfigure(0,weight=1); f.rowconfigure(1,weight=1)
        ttk.Label(f,text="Manage snapshots. Delete cannot be undone.",foreground="#888").grid(row=0,column=0,sticky="w")
        self.lb=tk.Listbox(f,font=("",10)); self.lb.grid(row=1,column=0,sticky="nsew",pady=(5,5))
        self.lb.bind("<<ListboxSelect>>",self._sel)
        self.lbl=ttk.Label(f,text="",font=("",9),foreground="#555",background="#f0f0f0",padding=8,anchor="w")
        self.lbl.grid(row=2,column=0,sticky="ew",pady=(0,5))
        b=ttk.Frame(f); b.grid(row=3,column=0)
        tk.Button(b,text="Rename",padx=12,command=self._rename).pack(side="left",padx=3)
        tk.Button(b,text="Delete",fg=CRED,padx=12,command=self._delete).pack(side="left",padx=3)
        tk.Button(b,text="Close",padx=12,command=self.destroy).pack(side="right",padx=3)

    def _refresh(self):
        self.lb.delete(0,"end"); self._snaps=get_all_snapshots()
        for s in self._snaps:
            self.lb.insert("end",f"{s['name']}  |  {s['created_at'][:19]}  |  {s['success_count']}/{s['total_count']}")
        if self._snaps: self.lb.selection_set(0); self._sel()

    def _sel(self,event=None):
        sel=self.lb.curselection()
        if not sel: return
        s=self._snaps[sel[0]]; data=get_snapshot_data(s["id"])
        top5=sorted(data,key=lambda x:x.get("fans_base",0) or 0,reverse=True)[:5]
        names=" > ".join([d["name"] for d in top5])
        self.lbl.config(text=f"Name: {s['name']}  |  Created: {s['created_at'][:19]}\n"
            f"Total: {s['total_count']}  |  OK: {s['success_count']}  |  Fail: {s['fail_count']}\n"
            f"Notes: {s.get('notes','-')}\nTOP5: {names}")

    def _rename(self):
        sel=self.lb.curselection()
        if not sel: return
        s=self._snaps[sel[0]]
        from tkinter import simpledialog
        n=simpledialog.askstring("Rename","New name:",initialvalue=s["name"],parent=self)
        if n:
            from ..models.database import _connect
            c=_connect(); c.execute("UPDATE snapshots SET name=? WHERE id=?",(n,s["id"]))
            c.commit(); c.close()
            self._refresh()
            if self._cb: self._cb()

    def _delete(self):
        sel=self.lb.curselection()
        if not sel: return
        s=self._snaps[sel[0]]
        if messagebox.askyesno("Confirm",f"Delete '{s['name']}'?\n{s['total_count']} records lost."):
            delete_snapshot(s["id"]); self._refresh()
            if self._cb: self._cb()

# ═══════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════
class MainWindow:
    def __init__(self):
        self.root=tk.Tk(); self.root.title("YSPlatform Analyzer")
        self.root.geometry("1150x780"); self.root.minsize(950,650)
        self.root.configure(bg=CBG)
        init_db()
        self._build_menu(); self._build_notebook()
        self.root.after(200,self._initial_refresh)

    def _build_menu(self):
        mb=tk.Menu(self.root); self.root.config(menu=mb)
        fm=tk.Menu(mb,tearoff=0)
        fm.add_command(label="Export CSV",command=lambda:self.data_tab._export())
        fm.add_separator(); fm.add_command(label="Exit",command=self.root.destroy)
        mb.add_cascade(label="File",menu=fm)
        tm=tk.Menu(mb,tearoff=0)
        tm.add_command(label="Snapshot Manager",command=self._open_sm)
        tm.add_command(label="Settings",command=self._open_settings)
        mb.add_cascade(label="Tools",menu=tm)

    def _build_notebook(self):
        self.nb=ttk.Notebook(self.root); self.nb.pack(fill="both",expand=True,padx=4,pady=4)
        self.crawl_tab=CrawlTab(self.nb,self)
        self.data_tab=DataTableTab(self.nb,self)
        self.analysis_tab=AnalysisTab(self.nb,self)
        self.nb.add(self.crawl_tab,text=" Crawl ")
        self.nb.add(self.data_tab,text=" Data Table ")
        self.nb.add(self.analysis_tab,text=" Analysis ")
        self.nb.bind("<<NotebookTabChanged>>",self._on_tab)

    def _initial_refresh(self):
        self.crawl_tab.refresh(); self.data_tab.refresh_snapshots(); self.analysis_tab.refresh_snapshots()

    def _on_tab(self,event):
        i=self.nb.index("current")
        if i==0: self.crawl_tab.refresh()
        elif i==1: self.data_tab.refresh_snapshots()
        elif i==2: self.analysis_tab.refresh_snapshots()

    def on_crawl_done(self,sid):
        self.data_tab.refresh_snapshots(); self.analysis_tab.refresh_snapshots(); self.nb.select(1)

    def _open_sm(self):
        SnapshotManager(self.root,on_change=lambda:(self.data_tab.refresh_snapshots(),self.analysis_tab.refresh_snapshots()))

    def _open_settings(self): SettingsDialog(self.root)

    def run(self): self.root.mainloop()
