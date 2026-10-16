"""Tiny offline desktop interface. No account, uploads, or server required."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
import threading
from queue import Empty, Queue

from tkinterdnd2 import DND_FILES, TkinterDnD
from cleaner import DEFAULT_KEY, DEFAULT_REQUIRED, DEFAULT_NUMERIC, process

ROOT = Path(__file__).resolve().parent


class Window(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSV & Excel Cleaner | Local Automation")
        self.geometry("760x700")
        self.minsize(660, 650)
        self.configure(bg="#f2f6fa")
        self.input_var = tk.StringVar(value=str(ROOT / "data" / "input"))
        self.output_var = tk.StringVar(value=str(ROOT / "data" / "output"))
        self.key_var = tk.StringVar(value=DEFAULT_KEY)
        self.required_var = tk.StringVar(value="id,time,latitude,longitude")
        self.numeric_var = tk.StringVar(value="latitude,longitude,depth,magnitude")
        self.events = Queue()
        self.report_path = None
        self.dropped = None
        self.input_var.trace_add("write", lambda *_: setattr(self, "dropped", None))
        self._build()

    def _build(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TEntry", padding=9, relief="flat", borderwidth=1)
        style.configure("TButton", padding=9, font=("Segoe UI", 10))
        outer = tk.Frame(self, bg="#f2f6fa", padx=34, pady=19)
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg="#14283b", padx=25, pady=17)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="LOCAL WORKFLOW AUTOMATION", bg="#14283b", fg="#78d6d9",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(header, text="CSV & Excel Cleaner", bg="#14283b", fg="white",
                 font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(3, 2))
        tk.Label(header, text="Merge · Validate · Deduplicate · Export report",
                 bg="#14283b", fg="#b9ceda", font=("Segoe UI", 10)).pack(anchor="w")
        form = tk.Frame(outer, bg="#f2f6fa")
        form.pack(fill="x")
        self._folder(form, "INPUT FOLDER", self.input_var, 0)
        self._folder(form, "OUTPUT FOLDER", self.output_var, 1)
        drop = tk.Label(form, text="Drop CSV / XLSX files or folders here",
                        bg="#e8f5f5", fg="#176472", font=("Segoe UI", 11, "bold"),
                        relief="groove", bd=1, pady=9)
        drop.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        drop.drop_target_register(DND_FILES)
        drop.dnd_bind("<<Drop>>", self._drop)
        options = tk.Frame(form, bg="#f2f6fa")
        options.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 8))
        options.grid_columnconfigure(1, weight=1)
        for index, (title, variable) in enumerate([
            ("Unique key", self.key_var),
            ("Required columns", self.required_var),
            ("Numeric columns", self.numeric_var),
        ]):
            tk.Label(options, text=title, bg="#f2f6fa", fg="#37485a",
                     font=("Segoe UI", 10)).grid(row=index, column=0, sticky="w", pady=5, padx=(0, 18))
            ttk.Entry(options, textvariable=variable).grid(row=index, column=1, sticky="ew", pady=5)
        actions = tk.Frame(outer, bg="#f2f6fa")
        actions.pack(fill="x", pady=(4, 9))
        self.run_btn = tk.Button(actions, text="RUN DATA CLEANUP  →", bg="#047d89", fg="white",
                                 relief="flat", cursor="hand2", font=("Segoe UI", 11, "bold"),
                                 padx=24, pady=12, command=self._run)
        self.run_btn.pack(side="left")
        self.report_btn = ttk.Button(actions, text="Open HTML report", command=self._report, state="disabled")
        self.report_btn.pack(side="left", padx=12)
        self.status = tk.StringVar(value="Sample files are preloaded. Edit the columns for your own data.")
        tk.Label(outer, textvariable=self.status, bg="#f2f6fa", fg="#526b7b",
                 wraplength=650, justify="left", font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(outer, text="100% offline · Python + openpyxl · No paid APIs",
                 bg="#f2f6fa", fg="#708596", font=("Segoe UI", 9)).pack(side="bottom", anchor="w")

    def _folder(self, parent, title, variable, row):
        frame = tk.Frame(parent, bg="#f2f6fa")
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        parent.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        tk.Label(frame, text=title, bg="#f2f6fa", fg="#37485a",
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=variable).grid(row=1, column=0, sticky="ew", pady=(5, 0))
        ttk.Button(frame, text="Browse", command=lambda: variable.set(
            filedialog.askdirectory(initialdir=variable.get()) or variable.get()
        )).grid(row=1, column=1, padx=(8, 0), pady=(5, 0))

    def _drop(self, event):
        paths = [Path(p) for p in self.tk.splitlist(event.data)]
        if not paths or any(not p.exists() or
                            (p.is_file() and p.suffix.lower() not in (".csv", ".xlsx"))
                            for p in paths):
            messagebox.showerror("Unsupported drop", "Drop existing CSV/XLSX files or folders.")
            return
        if len(paths) == 1 and paths[0].is_dir():
            self.input_var.set(str(paths[0]))
        else:
            self.input_var.set(f"{len(paths)} dropped item(s)")
            self.dropped = [str(p) for p in paths]
        if (self.required_var.get() == "id,time,latitude,longitude" and
                self.numeric_var.get() == "latitude,longitude,depth,magnitude"):
            self.required_var.set(DEFAULT_REQUIRED)
            self.numeric_var.set(DEFAULT_NUMERIC)
        self.status.set(f"Selected {len(paths)} item(s). Check the key and validation fields, then run.")

    def _run(self):
        self.report_path = None
        self.report_btn.configure(state="disabled")
        self.run_btn.configure(state="disabled")
        self.status.set("Processing input files...")
        inputs = (self.dropped or self.input_var.get(), self.output_var.get(),
                  self.key_var.get(), self.required_var.get(), self.numeric_var.get())

        def worker():
            try:
                self.events.put(("ok", process(*inputs)))
            except Exception as exc:
                self.events.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._poll)

    def _poll(self):
        try:
            status, result = self.events.get_nowait()
        except Empty:
            self.after(100, self._poll)
            return
        self.run_btn.configure(state="normal")
        if status == "error":
            self.status.set("Processing failed; previous results have not been overwritten.")
            messagebox.showerror("CSV Batch Cleaner", result)
            return
        self.report_path = Path(result.output_directory) / "report.html"
        self.status.set(f"Complete: {result.clean_rows} clean / {result.duplicate_rows} duplicates / "
                        f"{result.rejected_rows} rejected, from {result.input_files} files. "
                        f"Results: {result.output_directory}")
        self.report_btn.configure(state="normal")

    def _report(self):
        if self.report_path:
            webbrowser.open(self.report_path.as_uri())


if __name__ == "__main__":
    Window().mainloop()
