#!/usr/bin/env python3
"""
BetterPDF - betterpdf_gui.py
------------------------------
Application de bureau (fenetre graphique native, Tkinter) pour SilentPDF.py.

Aucun serveur, aucun navigateur, aucun port : on choisit un PDF, on choisit
ou l'enregistrer, et le traitement se fait directement sur la machine.

Utilise :
  - SilentPDF.py tel quel (non modifie) pour la pixelisation/redaction
  - optimizer.py pour l'optimisation de taille en post-traitement
"""

import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import SilentPDF
from optimizer import optimize_lossless, optimize_aggressive


# ---------- Palette : interface epuree, fond blanc, texte anthracite ----------
COLOR_BG = "#FFFFFF"
COLOR_PANEL = "#FAFAFA"
COLOR_TEXT = "#2E2E2E"
COLOR_SUBTEXT = "#7A7A7A"
COLOR_BORDER = "#E3E3E3"
COLOR_ACCENT = "#2E2E2E"
COLOR_ACCENT_HOVER = "#000000"
COLOR_ACCENT_TEXT = "#FFFFFF"
COLOR_SUCCESS = "#2E7D46"
COLOR_ERROR = "#B3261E"

FONT_FAMILY = "Helvetica" if sys.platform == "darwin" else "Segoe UI"


def human_size(num_bytes):
    if num_bytes < 1024:
        return f"{num_bytes} o"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} Ko"
    return f"{num_bytes / (1024 * 1024):.2f} Mo"


class BetterPDFApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BetterPDF")
        self.root.configure(bg=COLOR_BG)
        self.root.geometry("560x620")
        self.root.minsize(520, 580)

        self.input_path = None
        self.msg_queue = queue.Queue()

        self._build_style()
        self._build_ui()
        self.root.after(100, self._poll_queue)

    # ---------------------------------------------------------------- style
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=COLOR_BG)
        style.configure("Panel.TFrame", background=COLOR_PANEL)
        style.configure(
            "TLabel", background=COLOR_BG, foreground=COLOR_TEXT,
            font=(FONT_FAMILY, 11)
        )
        style.configure(
            "Panel.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXT,
            font=(FONT_FAMILY, 11)
        )
        style.configure(
            "Title.TLabel", background=COLOR_BG, foreground=COLOR_TEXT,
            font=(FONT_FAMILY, 20, "bold")
        )
        style.configure(
            "Sub.TLabel", background=COLOR_BG, foreground=COLOR_SUBTEXT,
            font=(FONT_FAMILY, 10)
        )
        style.configure(
            "PanelSub.TLabel", background=COLOR_PANEL, foreground=COLOR_SUBTEXT,
            font=(FONT_FAMILY, 9)
        )
        style.configure(
            "Accent.TButton",
            background=COLOR_ACCENT, foreground=COLOR_ACCENT_TEXT,
            font=(FONT_FAMILY, 11, "bold"), padding=10, borderwidth=0
        )
        style.map("Accent.TButton", background=[("active", COLOR_ACCENT_HOVER)])
        style.configure(
            "Secondary.TButton",
            background=COLOR_PANEL, foreground=COLOR_TEXT,
            font=(FONT_FAMILY, 10), padding=8, borderwidth=1
        )
        style.configure(
            "Horizontal.TScale", background=COLOR_PANEL
        )
        style.configure(
            "TCheckbutton", background=COLOR_PANEL, foreground=COLOR_TEXT,
            font=(FONT_FAMILY, 10)
        )

    # ------------------------------------------------------------------ ui
    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)

        # --- Header ---
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="BetterPDF", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Retire le texte d'un PDF (pixelisation) sans toucher aux dessins vectoriels.",
            style="Sub.TLabel", wraplength=500, justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # --- File picker panel ---
        file_panel = tk.Frame(outer, bg=COLOR_PANEL, highlightbackground=COLOR_BORDER,
                               highlightthickness=1)
        file_panel.pack(fill="x", pady=(0, 14))
        inner = ttk.Frame(file_panel, style="Panel.TFrame", padding=16)
        inner.pack(fill="x")

        self.file_label = ttk.Label(
            inner, text="Aucun fichier selectionne", style="Panel.TLabel"
        )
        self.file_label.pack(anchor="w")
        self.file_sub = ttk.Label(inner, text="", style="PanelSub.TLabel")
        self.file_sub.pack(anchor="w", pady=(2, 10))

        ttk.Button(
            inner, text="Choisir un fichier PDF...", style="Secondary.TButton",
            command=self._pick_file
        ).pack(anchor="w")

        # --- Options panel ---
        opt_panel = tk.Frame(outer, bg=COLOR_PANEL, highlightbackground=COLOR_BORDER,
                              highlightthickness=1)
        opt_panel.pack(fill="x", pady=(0, 14))
        opt_inner = ttk.Frame(opt_panel, style="Panel.TFrame", padding=16)
        opt_inner.pack(fill="x")

        self.pixel_var = tk.IntVar(value=4)
        self.zoom_var = tk.DoubleVar(value=4.0)
        self.aggressive_var = tk.BooleanVar(value=False)
        self.quality_var = tk.IntVar(value=75)

        self._add_slider(opt_inner, "Taille du pixel", self.pixel_var, 2, 20, is_int=True)
        self._add_slider(opt_inner, "Resolution de rendu (zoom)", self.zoom_var, 1, 6, is_int=False)

        sep = tk.Frame(opt_inner, bg=COLOR_BORDER, height=1)
        sep.pack(fill="x", pady=10)

        agg_check = ttk.Checkbutton(
            opt_inner,
            text="Compression agressive des images (optionnel, avec perte sur les images uniquement)",
            variable=self.aggressive_var, command=self._toggle_quality
        )
        agg_check.pack(anchor="w")

        self.quality_frame = ttk.Frame(opt_inner, style="Panel.TFrame")
        self._add_slider(self.quality_frame, "Qualite JPEG", self.quality_var, 10, 95, is_int=True)
        # quality_frame packed/unpacked dynamically by _toggle_quality

        # --- Run button ---
        self.run_button = ttk.Button(
            outer, text="Traiter le PDF", style="Accent.TButton",
            command=self._start_processing, state="disabled"
        )
        self.run_button.pack(fill="x", pady=(4, 14))

        # --- Status / log ---
        self.status_label = ttk.Label(outer, text="En attente d'un fichier...", style="Sub.TLabel")
        self.status_label.pack(anchor="w")

        log_frame = tk.Frame(outer, bg=COLOR_PANEL, highlightbackground=COLOR_BORDER,
                              highlightthickness=1)
        log_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.log_text = tk.Text(
            log_frame, bg=COLOR_PANEL, fg=COLOR_SUBTEXT, relief="flat",
            font=(FONT_FAMILY, 9), wrap="word", height=8, state="disabled",
            padx=12, pady=10, highlightthickness=0, borderwidth=0
        )
        self.log_text.pack(fill="both", expand=True)

    def _add_slider(self, parent, label, var, lo, hi, is_int):
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=6)

        top = ttk.Frame(row, style="Panel.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=label, style="Panel.TLabel").pack(side="left")
        val_label = ttk.Label(top, text=str(var.get()), style="Panel.TLabel")
        val_label.pack(side="right")

        def on_change(_evt=None):
            v = var.get()
            val_label.configure(text=f"{v:.1f}" if not is_int else str(int(v)))

        scale = ttk.Scale(
            row, from_=lo, to=hi, orient="horizontal", variable=var,
            command=lambda _v: on_change()
        )
        scale.pack(fill="x", pady=(4, 0))
        on_change()

    def _toggle_quality(self):
        if self.aggressive_var.get():
            self.quality_frame.pack(fill="x", pady=(6, 0))
        else:
            self.quality_frame.pack_forget()

    # -------------------------------------------------------------- actions
    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Choisir un PDF",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not path:
            return
        self.input_path = path
        size = os.path.getsize(path)
        self.file_label.configure(text=os.path.basename(path))
        self.file_sub.configure(text=human_size(size))
        self.run_button.configure(state="normal")
        self.status_label.configure(text="Pret. Cliquez sur Traiter le PDF.")
        self._clear_log()

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _log(self, text, color=None):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{text}\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _start_processing(self):
        if not self.input_path:
            return
        self.run_button.configure(state="disabled")
        self.status_label.configure(text="Traitement en cours...")
        self._clear_log()

        params = dict(
            pixel_size=int(self.pixel_var.get()),
            zoom=float(self.zoom_var.get()),
            aggressive=bool(self.aggressive_var.get()),
            jpeg_quality=int(self.quality_var.get()),
        )
        thread = threading.Thread(target=self._worker, args=(self.input_path, params), daemon=True)
        thread.start()

    def _worker(self, input_path, params):
        try:
            self.msg_queue.put(("log", f"Ouverture de {os.path.basename(input_path)}..."))
            base, _ = os.path.splitext(input_path)
            tmp_output = base + "_betterpdf_tmp.pdf"

            self.msg_queue.put(("log", "Appel de SilentPDF.process_pdf() (script original)..."))
            SilentPDF.process_pdf(
                input_path, tmp_output,
                pixel_size=params["pixel_size"], zoom=params["zoom"]
            )

            self.msg_queue.put(("log", "Optimisation de la taille du fichier..."))
            if params["aggressive"]:
                optimize_aggressive(tmp_output, jpeg_quality=params["jpeg_quality"])
            else:
                optimize_lossless(tmp_output)

            original_size = os.path.getsize(input_path)
            output_size = os.path.getsize(tmp_output)
            self.msg_queue.put(("done", (tmp_output, original_size, output_size)))
        except Exception as exc:
            self.msg_queue.put(("error", str(exc)))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self._log("> " + payload)
                elif kind == "error":
                    self._log("> ERREUR : " + payload)
                    self.status_label.configure(text="Echec du traitement.")
                    messagebox.showerror("BetterPDF", f"Erreur pendant le traitement :\n{payload}")
                    self.run_button.configure(state="normal")
                elif kind == "done":
                    tmp_output, original_size, output_size = payload
                    self._log("> Texte retire et fichier optimise avec succes.", COLOR_SUCCESS)
                    self._log(
                        f"> Taille originale {human_size(original_size)} -> "
                        f"{human_size(output_size)}"
                    )
                    self.status_label.configure(text="Termine. Choisissez ou enregistrer le fichier.")
                    self._save_result(tmp_output)
                    self.run_button.configure(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _save_result(self, tmp_output):
        default_name = os.path.splitext(os.path.basename(self.input_path))[0] + "_betterpdf.pdf"
        save_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF traite",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("Fichier PDF", "*.pdf")]
        )
        if save_path:
            try:
                if os.path.abspath(save_path) != os.path.abspath(tmp_output):
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    os.rename(tmp_output, save_path)
                self._log(f"> Enregistre : {save_path}")
                messagebox.showinfo("BetterPDF", f"Fichier enregistre :\n{save_path}")
            except Exception as exc:
                messagebox.showerror("BetterPDF", f"Impossible d'enregistrer le fichier :\n{exc}")
        else:
            self._log("> Enregistrement annule (le fichier temporaire reste dans le dossier source).")


def main():
    root = tk.Tk()
    BetterPDFApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
