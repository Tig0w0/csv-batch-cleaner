"""Small offline CSV/Excel desktop UI. One processing engine, no cloud."""
from pathlib import Path
from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from tkinterdnd2 import DND_FILES, TkinterDnD

from cleaner import DEFAULT_KEY, EXPORT_NAMES, export_filename, normalize_header, process
from spreadsheet_io import read_header

ROOT = Path(__file__).resolve().parent
SAMPLE_REQUIRED = "id,time,latitude,longitude"
SAMPLE_NUMERIC = "latitude,longitude,depth,magnitude"


class Window(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSV & Excel Cleaner | Local Automation")
        self.geometry("790x920")
        self.minsize(710, 800)
        self.configure(bg="#f2f6fa")
        self.input_var = tk.StringVar(value=str(ROOT / "data" / "input"))
        self.output_var = tk.StringVar(value=str(ROOT / "data" / "output"))
        self.key_var = tk.StringVar(value=DEFAULT_KEY)
        self.required_var = tk.StringVar(value=SAMPLE_REQUIRED)
        self.numeric_var = tk.StringVar(value=SAMPLE_NUMERIC)
        self.required_preview = tk.StringVar()
        self.numeric_preview = tk.StringVar()
        self.filename_prefix = tk.StringVar()
        self.prefix_preview = tk.StringVar(value="Example: cleaned.xlsx")
        self.filename_prefix.trace_add(
            "write", lambda *_: self.prefix_preview.set(
                "Example: " + export_filename("cleaned.xlsx", self.filename_prefix.get().strip())))
        self.export_flags = {name: tk.BooleanVar(value=name == "cleaned.xlsx")
                             for name in EXPORT_NAMES}
        self.last_result = None
        self.columns = []
        self.events = Queue()
        self.dropped = None
        self.input_var.trace_add("write", lambda *_: setattr(self, "dropped", None))
        self._build()
        self._load_columns(keep_sample=True)

    def _build(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TEntry", padding=9, relief="flat", borderwidth=1)
        style.configure("TButton", padding=9, font=("Segoe UI", 10))
        outer = tk.Frame(self, bg="#f2f6fa", padx=34, pady=18)
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg="#14283b", padx=25, pady=17)
        header.pack(fill="x", pady=(0, 17))
        tk.Label(header, text="LOCAL WORKFLOW AUTOMATION", bg="#14283b", fg="#78d6d9",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(header, text="CSV & Excel Cleaner", bg="#14283b", fg="white",
                 font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(3, 2))
        tk.Label(header, text="Merge · Validate · Deduplicate · Export files",
                 bg="#14283b", fg="#b9ceda", font=("Segoe UI", 10)).pack(anchor="w")

        form = tk.Frame(outer, bg="#f2f6fa")
        form.pack(fill="x")
        self._folder(form, "INPUT FILE / FOLDER", self.input_var, 0)
        self._folder(form, "OUTPUT FOLDER", self.output_var, 1)
        drop = tk.Label(form, text="Drop CSV / XLSX files or folders here",
                        bg="#e8f5f5", fg="#176472", font=("Segoe UI", 11, "bold"),
                        relief="groove", bd=1, pady=10)
        drop.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        drop.drop_target_register(DND_FILES)
        drop.dnd_bind("<<Drop>>", self._drop)

        options = tk.Frame(form, bg="#f2f6fa")
        options.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        options.grid_columnconfigure(1, weight=1)
        for row, caption in enumerate(("Find duplicates by", "Must-have values", "Check numeric values")):
            tk.Label(options, text=caption, bg="#f2f6fa", fg="#37485a",
                     font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))
        self.key_combo = ttk.Combobox(options, textvariable=self.key_var, state="readonly")
        self.key_combo.grid(row=0, column=1, sticky="ew", pady=6)
        for row, var, name in ((1, self.required_preview, "required"),
                               (2, self.numeric_preview, "numeric")):
            line = tk.Frame(options, bg="#f2f6fa")
            line.grid(row=row, column=1, sticky="ew", pady=4)
            ttk.Button(line, text="Choose columns", command=lambda kind=name: self._pick(kind)).pack(side="left")
            tk.Label(line, textvariable=var, bg="#f2f6fa", fg="#526b7b",
                     font=("Segoe UI", 9), anchor="w").pack(side="left", padx=10)

        export_panel = tk.LabelFrame(outer, text=" OUTPUT FILES (select what to save) ",
                                     bg="#f2f6fa", fg="#37485a", padx=12, pady=7,
                                     font=("Segoe UI", 10, "bold"))
        export_panel.pack(fill="x", pady=(2, 8))
        for col, title in ((0, "Data"), (1, "CSV"), (2, "Excel XLSX")):
            tk.Label(export_panel, text=title, bg="#f2f6fa", fg="#526b7b",
                     font=("Segoe UI", 9, "bold")).grid(row=0, column=col, sticky="w", padx=8)
        for row, (kind, title) in enumerate((("cleaned", "Clean records"),
                                             ("duplicates", "Duplicates"),
                                             ("rejected", "Rejected records")), 1):
            tk.Label(export_panel, text=title, bg="#f2f6fa",
                     font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", padx=8, pady=3)
            for col, ext in ((1, "csv"), (2, "xlsx")):
                ttk.Checkbutton(export_panel, variable=self.export_flags[f"{kind}.{ext}"]).grid(
                    row=row, column=col, sticky="w", padx=8)
        extras = ttk.Frame(export_panel)
        extras.grid(row=4, column=0, columnspan=3, sticky="w", pady=(5, 4))
        ttk.Checkbutton(extras, text="Save JSON summary",
                        variable=self.export_flags["summary.json"]).pack(side="left", padx=7)
        tk.Label(export_panel, text="Filename prefix (optional)", bg="#f2f6fa",
                 font=("Segoe UI", 10)).grid(row=5, column=0, sticky="w", padx=8)
        ttk.Entry(export_panel, textvariable=self.filename_prefix).grid(
            row=5, column=1, columnspan=2, sticky="ew", padx=8, pady=(3, 3))
        ttk.Label(export_panel, textvariable=self.prefix_preview).grid(
            row=6, column=1, columnspan=2, sticky="w", padx=8)
        export_panel.grid_columnconfigure(0, weight=1)
        export_panel.grid_columnconfigure(2, weight=1)

        actions = tk.Frame(outer, bg="#f2f6fa")
        actions.pack(fill="x", pady=(5, 9))
        self.run_btn = tk.Button(actions, text="RUN DATA CLEANUP →", bg="#047d89", fg="white",
                                 relief="flat", cursor="hand2", font=("Segoe UI", 11, "bold"),
                                 padx=24, pady=12, command=self._run)
        self.run_btn.pack(side="left")
        self.report_btn = ttk.Button(actions, text="View results",
                                     command=self._show_result, state="disabled")
        self.report_btn.pack(side="left", padx=12)
        self.status = tk.StringVar(value="Select the columns to check, then run.")
        tk.Label(outer, textvariable=self.status, bg="#f2f6fa", fg="#526b7b",
                 wraplength=650, justify="left", font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(outer, text="100% offline · No uploads or paid APIs",
                 bg="#f2f6fa", fg="#708596", font=("Segoe UI", 9)).pack(side="bottom", anchor="w")

    def _folder(self, parent, title, variable, row):
        frame = tk.Frame(parent, bg="#f2f6fa")
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        parent.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        tk.Label(frame, text=title, bg="#f2f6fa", fg="#37485a",
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(frame, textvariable=variable)
        entry.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        if variable is self.input_var:
            entry.bind("<Return>", lambda _: self._load_columns())
            entry.bind("<FocusOut>", lambda _: self._load_columns())
        ttk.Button(frame, text="Browse", command=lambda: self._browse(variable)).grid(
            row=1, column=1, padx=(8, 0), pady=(5, 0))

    def _browse(self, variable):
        folder = filedialog.askdirectory(initialdir=variable.get() if Path(variable.get()).is_dir() else str(ROOT))
        if folder:
            variable.set(folder)
            if variable is self.input_var:
                self._load_columns()

    def _drop(self, event):
        paths = [Path(value) for value in self.tk.splitlist(event.data)]
        if not paths or any(not p.exists() or
                            (p.is_file() and p.suffix.lower() not in (".csv", ".xlsx"))
                            for p in paths):
            messagebox.showerror("Unsupported drop", "Drop existing CSV/XLSX files or folders.")
            return
        self.input_var.set(str(paths[0]) if len(paths) == 1 else f"{len(paths)} dropped items")
        self.dropped = [str(p) for p in paths] if len(paths) > 1 else None
        self._load_columns()

    def _load_columns(self, keep_sample=False):
        """Show only fields shared by every selected file, matching core validation."""
        source = self.dropped or [self.input_var.get()]
        try:
            files = sorted({f.resolve() for item in source for p in [Path(item)]
                            for f in (p.iterdir() if p.is_dir() else [p])
                            if f.is_file() and f.suffix.lower() in (".csv", ".xlsx")
                            and not f.name.startswith("~$")})
            if not files:
                raise ValueError("No CSV/XLSX files found. Choose an input folder or drop files.")
            headers = [[normalize_header(value) for value in read_header(file)] for file in files]
            self.columns = [col for col in headers[0] if col and all(col in fields for fields in headers[1:])]
            if not self.columns:
                raise ValueError("Selected files have no column names in common.")
            self.key_combo["values"] = self.columns
            self.key_var.set(DEFAULT_KEY if DEFAULT_KEY in self.columns else self.columns[0])
            self.required_var.set(
                ",".join(c for c in SAMPLE_REQUIRED.split(",") if c in self.columns)
                if keep_sample else self.key_var.get())
            self.numeric_var.set(
                ",".join(c for c in SAMPLE_NUMERIC.split(",") if c in self.columns)
                if keep_sample else "")
            self._refresh_previews()
            self.run_btn.configure(state="normal")
            self.status.set(f"Found {len(self.columns)} shared columns across {len(files)} file(s).")
        except (OSError, ValueError, UnicodeError) as exc:
            self.columns = []
            self.key_combo["values"] = ()
            self.run_btn.configure(state="disabled")
            self.status.set(f"Input: {exc}")

    def _refresh_previews(self):
        for var, preview in ((self.required_var, self.required_preview),
                             (self.numeric_var, self.numeric_preview)):
            fields = var.get().split(",") if var.get() else []
            preview.set(", ".join(fields[:2]) + (f" +{len(fields)-2}" if len(fields) > 2 else "")
                        if fields else "None selected")

    def _pick(self, kind):
        if not self.columns:
            messagebox.showinfo("Choose input", "Drop a file or select a folder first.")
            return
        variable = self.required_var if kind == "required" else self.numeric_var
        selected = set(variable.get().split(",")) if variable.get() else set()
        dialog = tk.Toplevel(self)
        dialog.title("Required values" if kind == "required" else "Validate as numbers")
        dialog.geometry("400x440")
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="Check the columns to validate", font=("Segoe UI", 11, "bold"),
                 pady=12).pack()
        content = ttk.Frame(dialog)
        content.pack(fill="both", expand=True, padx=15)
        canvas = tk.Canvas(content, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        checks = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=checks, anchor="nw")
        checks.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        flags = [(col, tk.BooleanVar(value=col in selected)) for col in self.columns]
        for name, checked in flags:
            ttk.Checkbutton(checks, text=name, variable=checked).pack(anchor="w", pady=3)

        def apply():
            variable.set(",".join(name for name, flag in flags if flag.get()))
            self._refresh_previews()
            dialog.destroy()

        buttons = ttk.Frame(dialog)
        buttons.pack(pady=12)
        ttk.Button(buttons, text="Apply", command=apply).pack(side="left", padx=5)
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)

    def _run(self):
        if not self.columns:
            messagebox.showerror("Choose input", "Select CSV/XLSX files first.")
            return
        exports = {name for name, flag in self.export_flags.items() if flag.get()}
        if not exports:
            messagebox.showerror("Select output", "Choose at least one output file.")
            return
        self.last_result = None
        self.report_btn.configure(state="disabled")
        self.run_btn.configure(state="disabled")
        self.status.set("Processing input files...")
        prefix = self.filename_prefix.get().strip()
        inputs = (self.dropped or self.input_var.get(), self.output_var.get(),
                  self.key_var.get(), self.required_var.get(), self.numeric_var.get())

        def worker():
            try:
                self.events.put(("ok", process(*inputs, exports=exports,
                                               prefix=prefix)))
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
        self.last_result = result
        self.status.set(f"Complete: {result.clean_rows} clean / {result.duplicate_rows} duplicates / "
                        f"{result.rejected_rows} rejected, from {result.input_files} files. "
                        f"Results: {result.output_directory}")
        self.report_btn.configure(state="normal")
        self._show_result()

    def _show_result(self):
        result = self.last_result
        if result is None:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Processing results")
        dialog.geometry("550x530")
        dialog.transient(self)
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Processing complete", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(frame, text=f"{result.input_files} source files · {result.processed_rows} rows",
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 13))
        stats = ttk.Frame(frame)
        stats.pack(fill="x")
        for label, count in (("Clean", result.clean_rows),
                             ("Duplicates", result.duplicate_rows),
                             ("Rejected", result.rejected_rows)):
            cell = ttk.Frame(stats)
            cell.pack(side="left", expand=True, fill="x")
            ttk.Label(cell, text=str(count), font=("Segoe UI", 21, "bold")).pack()
            ttk.Label(cell, text=label).pack()
        ttk.Label(frame, text="Detected issues", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(19, 5))
        issue_list = ttk.Treeview(frame, columns=("issue", "count"), show="headings", height=6)
        issue_list.heading("issue", text="Reason")
        issue_list.heading("count", text="Rows")
        issue_list.column("issue", width=360)
        issue_list.column("count", width=70, anchor="e")
        for name, count in result.issues.items():
            issue_list.insert("", "end", values=(name.replace("_", " "), count))
        issue_list.pack(fill="x")
        ttk.Label(frame, text="Saved files", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(15, 5))
        names = [p.name for p in sorted(Path(result.output_directory).iterdir())]
        ttk.Label(frame, text=", ".join(names), wraplength=490, justify="left").pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(side="bottom", fill="x", pady=(18, 0))
        ttk.Button(buttons, text="Open output folder", command=lambda: webbrowser.open(
            Path(result.output_directory).as_uri())).pack(side="left")
        ttk.Button(buttons, text="Close", command=dialog.destroy).pack(side="right")


if __name__ == "__main__":
    Window().mainloop()
