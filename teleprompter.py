import html
import os
import re
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from zipfile import ZipFile


APP_NAME = "Teleprom"
AUTHOR = "Marek Zettel"
APP_DIR = Path(__file__).resolve().parent
WINDOWS_ICON_PATH = APP_DIR / "assets" / "teleprom.ico"
SUPPORTED_FILETYPES = (
    ("Obsługiwane pliki", "*.txt *.srt *.md *.markdown *.docx *.rtf"),
    ("Tekst", "*.txt"),
    ("Napisy SRT", "*.srt"),
    ("Markdown", "*.md *.markdown"),
    ("Word DOCX", "*.docx"),
    ("Rich Text Format", "*.rtf"),
    ("Wszystkie pliki", "*.*"),
)


def clean_srt(text):
    lines = []
    timestamp = re.compile(
        r"^\s*\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}\s*-->\s*"
        r"\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}"
    )
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
        elif line.isdigit() or timestamp.match(line):
            continue
        else:
            lines.append(line)
    return normalize_blank_lines("\n".join(lines))


def clean_markdown(text):
    replacements = [
        (r"```[\s\S]*?```", lambda match: match.group(0).strip("`")),
        (r"`([^`]+)`", r"\1"),
        (r"!\[([^\]]*)\]\([^)]+\)", r"\1"),
        (r"\[([^\]]+)\]\([^)]+\)", r"\1"),
        (r"^\s{0,3}#{1,6}\s*", ""),
        (r"^\s{0,3}>\s?", ""),
        (r"^\s*[-*+]\s+", "- "),
        (r"^\s*\d+\.\s+", ""),
        (r"[*_~]{1,3}", ""),
    ]
    cleaned = text
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.MULTILINE)
    return normalize_blank_lines(cleaned)


def normalize_blank_lines(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_rtf(text):
    text = re.sub(r"{\\fonttbl[\s\S]*?}", "", text)
    text = re.sub(r"{\\colortbl[\s\S]*?}", "", text)
    text = re.sub(r"\\par[d]?", "\n", text)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", "", text)
    text = re.sub(r"\\[a-zA-Z]+\d* ?", "", text)
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    return normalize_blank_lines(html.unescape(text))


def mirror_text(text):
    return "\n".join(line[::-1] for line in text.splitlines())


def read_docx(path):
    try:
        from docx import Document
    except ImportError:
        return read_docx_with_zip(path)

    document = Document(path)
    parts = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return normalize_blank_lines("\n\n".join(parts))


def read_docx_with_zip(path):
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    paragraphs = re.findall(r"<w:p[\s\S]*?</w:p>", xml)
    parts = []
    for paragraph in paragraphs:
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", paragraph)
        line = "".join(html.unescape(piece) for piece in texts).strip()
        if line:
            parts.append(line)
    return normalize_blank_lines("\n\n".join(parts))


def read_text_file(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".docx":
        return read_docx(path)

    data = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1250", "cp1252", "latin-1"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")

    if suffix == ".srt":
        return clean_srt(text)
    if suffix in {".md", ".markdown"}:
        return clean_markdown(text)
    if suffix == ".rtf":
        return clean_rtf(text)
    return normalize_blank_lines(text)


class TeleprompterWindow(tk.Toplevel):
    def __init__(self, master, text, settings):
        super().__init__(master)
        self.title(f"{APP_NAME} - okno promptera")
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.text = text
        self.settings = settings
        self.running = False
        self.position = 0.0
        self.last_tick = None
        self.text_item = None
        self.text_height = 0
        self.wrap_width = 800
        self.is_fullscreen = False

        self.configure(bg=settings["background"])
        self.apply_window_icon()
        self.geometry("1000x650")
        self.minsize(640, 420)

        self._build_ui()
        self._bind_shortcuts()
        self.after(60, self.render_text)
        self.after(120, self.tick)

    def _build_ui(self):
        self.toolbar = ttk.Frame(self, padding=(10, 8))
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.play_button = ttk.Button(self.toolbar, text="Start", command=self.toggle)
        self.play_button.pack(side=tk.LEFT)

        ttk.Button(self.toolbar, text="Reset", command=self.reset).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(self.toolbar, text="Pełny ekran", command=self.toggle_fullscreen).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(self.toolbar, text="Zamknij", command=self.close).pack(side=tk.RIGHT)

        self.status = ttk.Label(self.toolbar, text="Spacja: start/pauza  |  Esc: zamknij")
        self.status.pack(side=tk.LEFT, padx=14)

        self.canvas = tk.Canvas(
            self,
            bg=self.settings["background"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", lambda event: self.manual_scroll(-80))
        self.canvas.bind("<Button-5>", lambda event: self.manual_scroll(80))

    def apply_window_icon(self):
        if WINDOWS_ICON_PATH.exists():
            try:
                self.iconbitmap(str(WINDOWS_ICON_PATH))
            except tk.TclError:
                pass

    def _bind_shortcuts(self):
        self.bind("<space>", lambda event: self.toggle())
        self.bind("<Escape>", lambda event: self.close())
        self.bind("<Home>", lambda event: self.reset())
        self.bind("<F11>", lambda event: self.toggle_fullscreen())
        self.bind("<Up>", lambda event: self.manual_scroll(-80))
        self.bind("<Down>", lambda event: self.manual_scroll(80))
        self.bind("<Prior>", lambda event: self.manual_scroll(-320))
        self.bind("<Next>", lambda event: self.manual_scroll(320))

    def render_text(self):
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        margin_x = int(self.settings["margin"])
        top_padding = int(self.settings["top_padding"])
        self.wrap_width = max(width - (margin_x * 2), 120)

        font = (self.settings["font_family"], int(self.settings["font_size"]))
        anchor = "nw"
        x = margin_x
        y = height + top_padding - self.position

        display_text = self.text or "Wklej lub zaimportuj tekst, aby rozpocząć."
        if self.settings["mirror"]:
            display_text = mirror_text(display_text)

        self.text_item = self.canvas.create_text(
            x,
            y,
            text=display_text,
            fill=self.settings["foreground"],
            font=font,
            width=self.wrap_width,
            anchor=anchor,
            justify=self.settings["align"],
        )

        bbox = self.canvas.bbox(self.text_item)
        self.text_height = (bbox[3] - bbox[1]) if bbox else 0

    def on_resize(self, _event):
        self.render_text()

    def on_mousewheel(self, event):
        self.manual_scroll(-event.delta / 2)

    def manual_scroll(self, amount):
        self.position = max(0.0, self.position + amount)
        self.render_text()

    def toggle(self):
        self.running = not self.running
        self.last_tick = time.perf_counter()
        self.play_button.configure(text="Pauza" if self.running else "Start")

    def reset(self):
        self.position = 0.0
        self.last_tick = time.perf_counter()
        self.render_text()

    def tick(self):
        now = time.perf_counter()
        if self.last_tick is None:
            self.last_tick = now

        elapsed = now - self.last_tick
        self.last_tick = now

        if self.running:
            speed = float(self.settings["speed"])
            self.position += speed * elapsed
            end_at = self.text_height + self.canvas.winfo_height() + int(self.settings["top_padding"])
            if self.position > end_at:
                self.running = False
                self.play_button.configure(text="Start")
            self.render_text()

        self.after(16, self.tick)

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if self.is_fullscreen:
            self.toolbar.pack_forget()
        else:
            self.toolbar.pack(side=tk.TOP, fill=tk.X, before=self.canvas)

    def close(self):
        self.running = False
        self.grab_release()
        self.destroy()


class TelepromApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - {AUTHOR}")
        self.apply_window_icon()
        self.geometry("1120x760")
        self.minsize(860, 580)

        self.font_family = tk.StringVar(value=self.default_font())
        self.font_size = tk.IntVar(value=46)
        self.speed = tk.DoubleVar(value=70.0)
        self.margin = tk.IntVar(value=90)
        self.top_padding = tk.IntVar(value=120)
        self.foreground = tk.StringVar(value="#f7f7f2")
        self.background = tk.StringVar(value="#111111")
        self.align = tk.StringVar(value="center")
        self.mirror = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=True)

        self._configure_style()
        self._build_ui()
        self._insert_sample_text()

    def _configure_style(self):
        self.style = ttk.Style()
        if sys.platform == "darwin":
            if "aqua" in self.style.theme_names():
                self.style.theme_use("aqua")
        elif "vista" in self.style.theme_names():
            self.style.theme_use("vista")

    def apply_window_icon(self):
        if WINDOWS_ICON_PATH.exists():
            try:
                self.iconbitmap(str(WINDOWS_ICON_PATH))
            except tk.TclError:
                pass

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=0)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(header, text=APP_NAME, font=(self.default_font(), 22, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, text=f"autor {AUTHOR}").pack(side=tk.LEFT, padx=(10, 0), pady=(8, 0))

        editor_frame = ttk.LabelFrame(root, text="Tekst", padding=10)
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        self.text_editor = tk.Text(
            editor_frame,
            wrap=tk.WORD,
            undo=True,
            font=(self.default_font(), 14),
            padx=12,
            pady=12,
        )
        self.text_editor.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.text_editor.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_editor.configure(yscrollcommand=scrollbar.set)

        editor_actions = ttk.Frame(editor_frame)
        editor_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(editor_actions, text="Importuj plik", command=self.import_file).pack(side=tk.LEFT)
        ttk.Button(editor_actions, text="Wklej ze schowka", command=self.paste_clipboard).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(editor_actions, text="Wyczyść", command=self.clear_text).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(editor_actions, text="Otwórz prompter", command=self.open_prompter).pack(side=tk.RIGHT)

        controls = ttk.LabelFrame(root, text="Ustawienia promptera", padding=12)
        controls.grid(row=1, column=1, sticky="ns")
        controls.columnconfigure(1, weight=1)

        self._font_picker(controls, 0)
        self._scale(controls, "Rozmiar", self.font_size, 18, 120, 1, row=1)
        self._scale(controls, "Prędkość", self.speed, 5, 260, 5, row=2, suffix=" px/s")
        self._scale(controls, "Margines", self.margin, 20, 240, 10, row=3)
        self._scale(controls, "Start od dołu", self.top_padding, 0, 360, 10, row=4)

        ttk.Label(controls, text="Wyrównanie").grid(row=5, column=0, sticky="w", pady=(14, 4))
        align_frame = ttk.Frame(controls)
        align_frame.grid(row=5, column=1, sticky="ew", pady=(14, 4))
        for label, value in (("Lewo", "left"), ("Środek", "center"), ("Prawo", "right")):
            ttk.Radiobutton(align_frame, text=label, value=value, variable=self.align).pack(
                side=tk.LEFT, padx=(0, 6)
            )

        ttk.Button(controls, text="Kolor tekstu", command=self.pick_foreground).grid(
            row=6, column=0, sticky="ew", pady=(14, 4)
        )
        ttk.Button(controls, text="Kolor tła", command=self.pick_background).grid(
            row=6, column=1, sticky="ew", pady=(14, 4)
        )

        ttk.Checkbutton(controls, text="Odbicie lustrzane", variable=self.mirror).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )
        ttk.Checkbutton(controls, text="Okno zawsze na wierzchu", variable=self.always_on_top).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        tips = (
            "Skróty w oknie promptera:\n"
            "Spacja - start/pauza\n"
            "Home - reset\n"
            "F11 - pełny ekran\n"
            "Esc - zamknij\n"
            "Kółko myszy / strzałki - ręczne przewijanie"
        )
        ttk.Label(controls, text=tips, justify=tk.LEFT).grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(22, 0)
        )

    def _font_picker(self, parent, row):
        ttk.Label(parent, text="Czcionka").grid(row=row, column=0, sticky="w", pady=(0, 4))
        fonts = sorted(set(tkfont.families()))
        picker = ttk.Combobox(parent, textvariable=self.font_family, values=fonts, state="readonly", width=26)
        picker.grid(row=row, column=1, sticky="ew", pady=(0, 4))

    def _scale(self, parent, label, variable, start, end, step, row, suffix=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(12, 0))
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=1, sticky="ew", pady=(12, 0))
        frame.columnconfigure(0, weight=1)
        scale = ttk.Scale(frame, variable=variable, from_=start, to=end)
        scale.grid(row=0, column=0, sticky="ew")
        value_label = ttk.Label(frame, width=8)
        value_label.grid(row=0, column=1, padx=(8, 0))

        def update_label(*_args):
            value = variable.get()
            rounded = int(round(value / step) * step)
            if isinstance(variable, tk.IntVar) and variable.get() != rounded:
                variable.set(rounded)
            value_label.configure(text=f"{rounded}{suffix}")

        variable.trace_add("write", update_label)
        update_label()

    def default_font(self):
        families = set(tkfont.families())
        for candidate in ("Segoe UI", "San Francisco", "Helvetica Neue", "Arial", "Helvetica"):
            if candidate in families:
                return candidate
        return "TkDefaultFont"

    def import_file(self):
        path = filedialog.askopenfilename(title="Wybierz plik z tekstem", filetypes=SUPPORTED_FILETYPES)
        if not path:
            return
        try:
            text = read_text_file(path)
        except Exception as exc:
            messagebox.showerror("Nie udało się wczytać pliku", str(exc))
            return

        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", text)
        self.title(f"{APP_NAME} - {AUTHOR} - {os.path.basename(path)}")

    def paste_clipboard(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("Schowek", "Schowek jest pusty albo nie zawiera tekstu.")
            return
        self.text_editor.insert(tk.INSERT, text)

    def clear_text(self):
        if messagebox.askyesno("Wyczyścić tekst?", "Usunąć cały tekst z edytora?"):
            self.text_editor.delete("1.0", tk.END)

    def pick_foreground(self):
        color = colorchooser.askcolor(color=self.foreground.get(), title="Kolor tekstu")
        if color and color[1]:
            self.foreground.set(color[1])

    def pick_background(self):
        color = colorchooser.askcolor(color=self.background.get(), title="Kolor tła")
        if color and color[1]:
            self.background.set(color[1])

    def open_prompter(self):
        text = normalize_blank_lines(self.text_editor.get("1.0", tk.END))
        if not text:
            messagebox.showinfo("Brak tekstu", "Wklej tekst albo zaimportuj plik przed uruchomieniem.")
            return

        settings = {
            "font_family": self.font_family.get(),
            "font_size": self.font_size.get(),
            "speed": self.speed.get(),
            "margin": self.margin.get(),
            "top_padding": self.top_padding.get(),
            "foreground": self.foreground.get(),
            "background": self.background.get(),
            "align": self.align.get(),
            "mirror": self.mirror.get(),
        }
        window = TeleprompterWindow(self, text, settings)
        window.attributes("-topmost", self.always_on_top.get())
        window.focus_set()

    def _insert_sample_text(self):
        sample = (
            "Teleprom - autor Marek Zettel\n\n"
            "Wklej tutaj tekst albo zaimportuj plik TXT, SRT, MD lub DOCX.\n\n"
            "Następnie ustaw czcionkę, rozmiar i prędkość przewijania, "
            "a potem uruchom modalne okno promptera."
        )
        self.text_editor.insert("1.0", sample)


def main():
    app = TelepromApp()
    app.mainloop()


if __name__ == "__main__":
    main()
