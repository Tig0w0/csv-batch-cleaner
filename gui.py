"""Tiny offline desktop interface. No account, uploads, or server required."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from cleaner import process

ROOT = Path(__file__).resolve().parent


class Window(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSV Batch Cleaner | Local Automation")
        self.geometry("760x700")
        self.minsize(660, 650)
        self.configure(bg="#f2f6fa")
        self.input_var = tk.StringVar(value=str(ROOT / "data" / "input"))
        self.output_var = tk.StringVar(value=str(ROOT / "data" / "output"))
        self.key_var = tk.StringVar(value="id")
        self.required_var = tk.StringVar(value="id,time,latitude,longitude")
        self.numeric_var = tk.StringVar(value="latitude,longitude,depth,magnitude")
        self.report_path = None
        self._build()

    def _build(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TEntry", padding=9, relief="flat", borderwidth=1)
        style.configure("TButton", padding=9, font=("Segoe UI", 10))
        outer = tk.Frame(self, bg="#f2f6fa", padx=34, pady=25)
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg="#14283b", padx=25, pady=22)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="LOCAL WORKFLOW AUTOMATION", bg="#14283b", fg="#78d6d9",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(header, text="CSV Batch Cleaner", bg="#14283b", fg="white",
                 font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(3, 2))
        tk.Label(header, text="Merge · Validate · Deduplicate · Export report",
                 bg="#14283b", fg="#b9ceda", font=("Segoe UI", 10)).pack(anchor="w")
        form = tk.Frame(outer, bg="#f2f6fa")
        form.pack(fill="x")
        self._folder(form, "INPUT FOLDER", self.input_var, 0)
        self._folder(form, "OUTPUT FOLDER", self.output_var, 1)
        options = tk.Frame(form, bg="#f2f6fa")
        options.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 12))
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
        actions.pack(fill="x", pady=(6, 12))
        self.run_btn = tk.Button(actions, text="RUN DATA CLEANUP  →", bg="#047d89", fg="white",
                                 relief="flat", cursor="hand2", font=("Segoe UI", 11, "bold"),
                                 padx=24, pady=12, command=self._run)
        self.run_btn.pack(side="left")
        self.report_btn = ttk.Button(actions, text="Open HTML report", command=self._report, state="disabled")
        self.report_btn.pack(side="left", padx=12)
        self.status = tk.StringVar(value="Ready. Your files remain on this computer.")
        tk.Label(outer, textvariable=self.status, bg="#f2f6fa", fg="#526b7b",
                 wraplength=650, justify="left", font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(outer, text="100% offline · Python standard library · No paid APIs",
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

    def _run(self):
        self.run_btn.configure(state="disabled")
        self.update_idletasks()
        try:
            result = process(self.input_var.get(), self.output_var.get(),
                             self.key_var.get(), self.required_var.get(), self.numeric_var.get())
            self.report_path = Path(result.output_directory) / "report.html"
            self.status.set(f"Complete: {result.clean_rows} clean / {result.duplicate_rows} duplicates / "
                            f"{result.rejected_rows} rejected, from {result.input_files} CSV files.")
            self.report_btn.configure(state="normal")
        except Exception as exc:
            self.status.set("Processing failed; please check your input settings.")
            messagebox.showerror("CSV Batch Cleaner", str(exc))
        finally:
            self.run_btn.configure(state="normal")

    def _report(self):
        if self.report_path:
            webbrowser.open(self.report_path.as_uri())


if __name__ == "__main__":
    Window().mainloop()
