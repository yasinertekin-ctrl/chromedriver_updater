#!/usr/bin/env python3
"""
PipManager Pro — Gelişmiş GUI pip paket yöneticisi
Python 3.8+ | Tkinter | Standart kütüphane
"""

import sys
import os
import subprocess
import threading
import importlib.metadata
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import json
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────────────────
#  TEMA
# ─────────────────────────────────────────────────────────
C = {
    "bg":       "#0f0f17",
    "panel":    "#16161f",
    "card":     "#1e1e2a",
    "border":   "#2a2a3a",
    "accent":   "#7c6af7",
    "accent2":  "#f7786a",
    "green":    "#5dba7d",
    "yellow":   "#f0c060",
    "red":      "#f7786a",
    "fg":       "#e8e6f0",
    "muted":    "#6b6880",
    "input_bg": "#12121a",
}

FONT_MONO  = ("Consolas", 9)
FONT_MONO_B= ("Consolas", 9, "bold")
FONT_UI    = ("Segoe UI", 9)
FONT_UI_B  = ("Segoe UI", 9, "bold")
FONT_BIG   = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 8)


# ─────────────────────────────────────────────────────────
#  YARDIMCILAR
# ─────────────────────────────────────────────────────────
def run_pip(interpreter: str, args: list[str],
            on_line=None, on_done=None):
    """pip komutunu arka planda çalıştır; her satırı on_line'a ilet."""
    def _worker():
        cmd = [interpreter, "-m", "pip"] + args
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32" else 0
            )
            for line in proc.stdout:
                if on_line:
                    on_line(line.rstrip())
            proc.wait()
            if on_done:
                on_done(proc.returncode)
        except Exception as e:
            if on_line:
                on_line(f"HATA: {e}")
            if on_done:
                on_done(1)

    threading.Thread(target=_worker, daemon=True).start()


def get_packages(interpreter: str) -> list[dict]:
    """Yüklü paketleri döndür."""
    try:
        result = subprocess.run(
            [interpreter, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32" else 0
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    # fallback: importlib (sadece EXE içinde paket listesi alınamazsa veya debugging için)
    pkgs = []
    try:
        for dist in importlib.metadata.distributions():
            name = dist.metadata.get("Name")
            ver  = dist.version
            if name:
                pkgs.append({"name": name, "version": ver})
    except Exception:
        pass
    return sorted(pkgs, key=lambda x: x["name"].lower())


def get_outdated(interpreter: str) -> list[dict]:
    """Güncel olmayan paketleri döndür."""
    try:
        result = subprocess.run(
            [interpreter, "-m", "pip", "list", "--outdated", "--format=json"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32" else 0
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return []


def _is_exe_mode() -> bool:
    """
    PS2EXE veya PyInstaller ile paketlenmiş EXE olarak mı çalışıyor?
    sys.executable'ın uzantısı .exe ise ve isminde python geçmiyorsa EXE modundayızdır.
    """
    exe = sys.executable
    if not exe:
        return False
    
    # Windows'ta .exe uzantısı kontrolü
    if exe.lower().endswith(".exe"):
        # İsim kısmında python geçmiyorsa (örn: PipManager.exe), bu bir uygulama EXE'sidir.
        exe_name = os.path.basename(exe).lower()
        if "python" not in exe_name and "pypy" not in exe_name:
            return True
            
    # PyInstaller/PS2EXE için sys.frozen kontrolü (daha güvenilir)
    if getattr(sys, 'frozen', False):
        return True

    return False


def find_real_python() -> str:
    """
    Gerçek python.exe yolunu döndür.
    EXE modunda sys.executable uygulama kendisi olduğu için
    PATH ve yaygın konumlardan gerçek yorumlayıcıyı buluruz.
    """
    # Eğer normal Python modundaysak, doğrudan sys.executable'ı kullanıyoruz.
    if not _is_exe_mode():
        return sys.executable

    # EXE modundaysak, kesinlikle sys.executable'ı (yani kendimizi) döndürmeyiz.
    # Bunun yerine PATH ve Registry'den ararız.
    
    # Önce PATH'den dene
    for name in ["python", "python3", "python3.12", "python3.11",
                 "python3.10", "python3.9", "python3.8"]:
        p = shutil.which(name)
        if p and _verify_python(p):
            return p

    # Windows sabit konumlar
    if sys.platform == "win32":
        import winreg
        # Registry'den Python kurulum yolunu oku
        for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for sub in [r"SOFTWARE\Python\PythonCore",
                        r"SOFTWARE\WOW6432Node\Python\PythonCore"]:
                try:
                    with winreg.OpenKey(root_key, sub) as key:
                        i = 0
                        while True:
                            try:
                                ver = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, ver + r"\InstallPath") as ip:
                                    install_dir = winreg.QueryValue(ip, "")
                                    candidate = os.path.join(install_dir.strip(), "python.exe")
                                    if os.path.isfile(candidate) and _verify_python(candidate):
                                        return candidate
                                i += 1
                            except OSError:
                                break
                except OSError:
                    continue

        # Sabit dizinler
        for base in [
            r"C:\Python312", r"C:\Python311", r"C:\Python310",
            r"C:\Python39",  r"C:\Python38",
            os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\python.exe"),
            os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311\python.exe"),
            os.path.expanduser(r"~\AppData\Local\Programs\Python\Python310\python.exe"),
        ]:
            p = base if base.endswith(".exe") else os.path.join(base, "python.exe")
            if os.path.isfile(p) and _verify_python(p):
                return p

    return ""   # bulunamadı


def _verify_python(path: str) -> bool:
    """Verilen yolun gerçekten Python olduğunu doğrula."""
    # Sonsuz döngüyü engelle: Eğer yol kendimize (exe) eşitse, bu bir Python değildir.
    if _is_exe_mode() and os.path.abspath(path) == os.path.abspath(sys.executable):
        return False
        
    try:
        r = subprocess.run(
            [path, "-c", "import sys; print(sys.version)"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32" else 0
        )
        return r.returncode == 0 and "." in r.stdout
    except Exception:
        return False


def find_pythons() -> list[str]:
    """Sistemdeki Python yorumlayıcılarını bul (EXE'yi listeye ekleme)."""
    candidates = []

    # EXE modunda değilse sys.executable gerçek Python'dur
    if not _is_exe_mode():
        if _verify_python(sys.executable):
            candidates.append(sys.executable)
    else:
        # EXE modundaysak, sys.executable'ı listeye eklemiyoruz.
        # Çünkü bu bizim uygulamamızdır, pip çalıştıramaz.
        pass

    # PATH'deki pythonlar
    for name in ["python", "python3", "python3.12", "python3.11",
                 "python3.10", "python3.9", "python3.8"]:
        p = shutil.which(name)
        if p and p not in candidates and _verify_python(p):
            candidates.append(p)

    # Windows: registry + sabit konumlar
    if sys.platform == "win32":
        import winreg
        for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for sub in [r"SOFTWARE\Python\PythonCore",
                        r"SOFTWARE\WOW6432Node\Python\PythonCore"]:
                try:
                    with winreg.OpenKey(root_key, sub) as key:
                        i = 0
                        while True:
                            try:
                                ver = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, ver + r"\InstallPath") as ip:
                                    install_dir = winreg.QueryValue(ip, "").strip()
                                    p = os.path.join(install_dir, "python.exe")
                                    # Aynı dosyayı tekrar ekleme
                                    if os.path.isfile(p) and p not in candidates and _verify_python(p):
                                        candidates.append(p)
                                i += 1
                            except OSError:
                                break
                except OSError:
                    continue

        for base in [r"C:\Python312", r"C:\Python311", r"C:\Python310",
                     r"C:\Python39",  r"C:\Python38"]:
            p = os.path.join(base, "python.exe")
            if os.path.isfile(p) and p not in candidates and _verify_python(p):
                candidates.append(p)

    return candidates


# ─────────────────────────────────────────────────────────
#  ANA UYGULAMA
# ─────────────────────────────────────────────────────────
class PipManagerPro:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PipManager Pro")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)

        W, H = 920, 680
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        root.minsize(700, 500)

        self._packages: list[dict]  = []
        self._outdated: list[dict]  = []
        self._running   = False
        self._stop_flag = False

        self._build_ui()
        self._refresh_packages()

    # ──────────────────────────────────────────
    #  UI YAPISI
    # ──────────────────────────────────────────
    def _build_ui(self):
        # ── Başlık ──────────────────────────────
        hdr = tk.Frame(self.root, bg="#0a0a12", height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⬡", font=("Segoe UI", 18),
                 bg="#0a0a12", fg=C["accent"]).place(x=16, rely=.5, anchor="w")
        tk.Label(hdr, text="PipManager Pro",
                 font=("Segoe UI", 13, "bold"),
                 bg="#0a0a12", fg=C["fg"]).place(x=44, rely=.5, anchor="w")
        self._py_ver_lbl = tk.Label(hdr, text="",
                 font=FONT_SMALL, bg="#0a0a12", fg=C["muted"])
        self._py_ver_lbl.place(relx=1, x=-16, rely=.5, anchor="e")

        # accent bar
        tk.Frame(self.root, bg=C["accent"], height=2).pack(fill="x")

        # ── Yorumlayıcı satırı ──────────────────
        interp_row = tk.Frame(self.root, bg=C["panel"], padx=14, pady=10)
        interp_row.pack(fill="x")

        tk.Label(interp_row, text="Python:", font=FONT_UI_B,
                 bg=C["panel"], fg=C["muted"]).pack(side="left")

        # EXE modunda sys.executable EXE'nin kendisidir — gerçek Python'u bul
        default_interp = sys.executable if not _is_exe_mode() else find_real_python()
        pythons = find_pythons()
        
        # Eğer default_interp hala sys.executable ise (örn. kontrol atlandı), 
        # ve EXE modundaysak, listeden çıkaralım ki yanlışlıkla seçilmesin.
        if _is_exe_mode():
            if default_interp == sys.executable:
                default_interp = pythons[0] if pythons else ""
            # Listemizde kendimiz varsa (find_pythons korumasına rağmen), temizle
            pythons = [p for p in pythons if p.lower() != sys.executable.lower()]

        if default_interp and default_interp not in pythons:
            pythons.insert(0, default_interp)
        if not default_interp and pythons:
            default_interp = pythons[0]

        self._interp_var = tk.StringVar(value=default_interp)
        self._interp_combo = ttk.Combobox(
            interp_row, textvariable=self._interp_var,
            values=pythons, width=52,
            font=FONT_MONO, state="readonly") # readonly yapıldı, elle hata girişini önlemek için
        self._interp_combo.pack(side="left", padx=8)
        self._interp_combo.bind("<<ComboboxSelected>>",
                                lambda _: self._refresh_packages())

        self._btn(interp_row, "Gözat",    self._browse_python, "secondary").pack(side="left", padx=2)
        self._btn(interp_row, "↺ Yenile", self._refresh_packages, "primary").pack(side="left", padx=2)

        # ── İstatistik kartları ─────────────────
        stats = tk.Frame(self.root, bg=C["bg"], padx=14, pady=8)
        stats.pack(fill="x")
        self._stat_total   = self._stat_card(stats, "Yüklü",        "0", C["accent"])
        self._stat_outdated= self._stat_card(stats, "Güncel Değil", "0", C["yellow"])
        self._stat_size    = self._stat_card(stats, "Durum",        "—", C["green"])

        # ── Notebook (sekmeler) ─────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",          background=C["bg"],  borderwidth=0)
        style.configure("TNotebook.Tab",      background=C["card"],
                        foreground=C["muted"], padding=[14,6],
                        font=FONT_UI_B)
        style.map("TNotebook.Tab",
                  background=[("selected", C["panel"])],
                  foreground=[("selected", C["fg"])])

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        self._tab_packages = tk.Frame(nb, bg=C["bg"])
        self._tab_install  = tk.Frame(nb, bg=C["bg"])
        self._tab_upgrade  = tk.Frame(nb, bg=C["bg"])
        self._tab_console  = tk.Frame(nb, bg=C["bg"])

        nb.add(self._tab_packages, text=" 📦 Paketler ")
        nb.add(self._tab_install,  text=" ➕ Yükle / Kaldır ")
        nb.add(self._tab_upgrade,  text=" ⬆ Güncelle ")
        nb.add(self._tab_console,  text=" 🖥 Konsol ")

        self._build_tab_packages()
        self._build_tab_install()
        self._build_tab_upgrade()
        self._build_tab_console()

        # ── Durum çubuğu ────────────────────────
        status_bar = tk.Frame(self.root, bg="#0a0a12", height=26)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        self._status_var = tk.StringVar(value="Hazır")
        tk.Label(status_bar, textvariable=self._status_var,
                 bg="#0a0a12", fg=C["muted"],
                 font=FONT_SMALL, anchor="w", padx=10).pack(side="left")
        self._progress = ttk.Progressbar(status_bar, mode="indeterminate",
                                         length=120)
        self._progress.pack(side="right", padx=10, pady=4)

    # ── Paketler sekmesi ────────────────────────
    def _build_tab_packages(self):
        p = self._tab_packages

        # Arama + filtre
        top = tk.Frame(p, bg=C["bg"], padx=12, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="🔍", bg=C["bg"], fg=C["muted"],
                 font=("", 11)).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_packages())
        e = tk.Entry(top, textvariable=self._search_var,
                     bg=C["input_bg"], fg=C["fg"],
                     insertbackground=C["accent"],
                     relief="flat", bd=0, font=FONT_UI,
                     highlightthickness=1,
                     highlightbackground=C["border"],
                     highlightcolor=C["accent"],
                     width=30)
        e.pack(side="left", padx=8, ipady=4)

        self._filter_var = tk.StringVar(value="Tümü")
        for txt in ["Tümü", "Güncel Değil"]:
            tk.Radiobutton(top, text=txt, variable=self._filter_var,
                           value=txt, bg=C["bg"], fg=C["muted"],
                           selectcolor=C["card"],
                           activebackground=C["bg"],
                           font=FONT_UI,
                           command=self._filter_packages).pack(side="left", padx=4)

        self._btn(top, "Seçiliyi Kaldır", self._uninstall_selected, "danger")\
            .pack(side="right")
        self._btn(top, "Seçiliyi Güncelle", self._upgrade_selected, "secondary")\
            .pack(side="right", padx=4)

        # Treeview
        cols = ("name", "version", "latest", "location")
        self._tree = ttk.Treeview(p, columns=cols, show="headings",
                                   selectmode="extended")
        style = ttk.Style()
        style.configure("Treeview",
                        background=C["card"], foreground=C["fg"],
                        fieldbackground=C["card"], rowheight=24,
                        borderwidth=0, font=FONT_UI)
        style.configure("Treeview.Heading",
                        background=C["panel"], foreground=C["muted"],
                        borderwidth=0, font=FONT_UI_B, relief="flat")
        style.map("Treeview",
                  background=[("selected", C["accent"])],
                  foreground=[("selected", "#fff")])

        self._tree.heading("name",     text="Paket Adı",   anchor="w")
        self._tree.heading("version",  text="Sürüm",       anchor="w")
        self._tree.heading("latest",   text="Son Sürüm",   anchor="w")
        self._tree.heading("location", text="Durum",       anchor="w")

        self._tree.column("name",     width=220, minwidth=120)
        self._tree.column("version",  width=100, minwidth=70)
        self._tree.column("latest",   width=100, minwidth=70)
        self._tree.column("location", width=120, minwidth=80)

        sb = ttk.Scrollbar(p, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)

        tree_frame = tk.Frame(p, bg=C["bg"])
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(0,8))
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ── Yükle / Kaldır sekmesi ─────────────────
    def _build_tab_install(self):
        p = self._tab_install

        card = tk.Frame(p, bg=C["card"], padx=20, pady=18)
        card.pack(fill="x", padx=16, pady=16)

        # ── Hızlı Yükleme (sadece modül adı yaz, Enter'a bas) ──
        tk.Label(card, text="HIZLI YÜKLEME — Modül adı yazıp Enter'a bas veya Yükle'ye tıkla",
                 bg=C["card"], fg=C["accent"], font=FONT_SMALL).pack(anchor="w")
        quick_row = tk.Frame(card, bg=C["card"])
        quick_row.pack(fill="x", pady=(6, 0))

        self._quick_var = tk.StringVar()
        quick_entry = tk.Entry(quick_row, textvariable=self._quick_var,
                               bg=C["input_bg"], fg=C["fg"],
                               insertbackground=C["accent"],
                               relief="flat", bd=0,
                               font=("Consolas", 13),
                               highlightthickness=2,
                               highlightbackground=C["accent"],
                               highlightcolor=C["accent"])
        quick_entry.pack(side="left", fill="x", expand=True, ipady=8)
        quick_entry.bind("<Return>", lambda _: self._quick_install())
        quick_entry.focus_set()
        self._attach_context_menu(quick_entry)

        self._btn(quick_row, "⚡ Yükle", self._quick_install, "primary").pack(side="left", padx=(10, 2))
        self._btn(quick_row, "✕ Kaldır", self._quick_uninstall, "danger").pack(side="left", padx=2)

        tk.Label(card, text="Birden fazla paket için virgülle ayırın: numpy, pandas, requests",
                 bg=C["card"], fg=C["muted"], font=FONT_SMALL).pack(anchor="w", pady=(4, 0))

        # ayırıcı
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x", pady=(16, 12))

        # Paket adı
        tk.Label(card, text="PAKET ADI / KOMUT",
                 bg=C["card"], fg=C["muted"], font=FONT_SMALL).pack(anchor="w")
        pkg_row = tk.Frame(card, bg=C["card"])
        pkg_row.pack(fill="x", pady=(4,0))

        self._pkg_var = tk.StringVar()
        e = tk.Entry(pkg_row, textvariable=self._pkg_var,
                     bg=C["input_bg"], fg=C["fg"],
                     insertbackground=C["accent"],
                     relief="flat", bd=0, font=("Consolas", 11),
                     highlightthickness=1,
                     highlightbackground=C["border"],
                     highlightcolor=C["accent"])
        e.pack(side="left", fill="x", expand=True, ipady=6)
        e.bind("<Return>", lambda _: self._install())
        self._attach_context_menu(e)

        self._btn(pkg_row, "Yükle ↓",  self._install,   "primary") .pack(side="left", padx=(8,2))
        self._btn(pkg_row, "Kaldır ✕", self._uninstall, "danger")  .pack(side="left", padx=2)

        # Seçenekler
        opt_row = tk.Frame(card, bg=C["card"])
        opt_row.pack(fill="x", pady=(12,0))

        self._upgrade_flag  = tk.BooleanVar(value=False)
        self._user_flag     = tk.BooleanVar(value=False)
        self._pre_flag      = tk.BooleanVar(value=False)

        for var, txt in [
            (self._upgrade_flag, "--upgrade"),
            (self._user_flag,    "--user"),
            (self._pre_flag,     "--pre (beta)"),
        ]:
            tk.Checkbutton(opt_row, text=txt, variable=var,
                           bg=C["card"], fg=C["fg"],
                           selectcolor=C["input_bg"],
                           activebackground=C["card"],
                           font=FONT_UI).pack(side="left", padx=(0,12))

        # Sürüm sabitleme
        ver_row = tk.Frame(card, bg=C["card"])
        ver_row.pack(fill="x", pady=(10,0))
        tk.Label(ver_row, text="Sürüm (opsiyonel):",
                 bg=C["card"], fg=C["muted"], font=FONT_SMALL).pack(side="left")
        self._ver_var = tk.StringVar()
        ver_e = tk.Entry(ver_row, textvariable=self._ver_var,
                 bg=C["input_bg"], fg=C["fg"],
                 insertbackground=C["accent"],
                 relief="flat", bd=0, font=FONT_MONO, width=14,
                 highlightthickness=1,
                 highlightbackground=C["border"],
                 highlightcolor=C["accent"])
        ver_e.pack(side="left", padx=8, ipady=4)
        self._attach_context_menu(ver_e)
        tk.Label(ver_row, text="örn: 1.2.3  veya  >=1.0,<2.0",
                 bg=C["card"], fg=C["muted"], font=FONT_SMALL).pack(side="left")

        # requirements.txt
        req_card = tk.Frame(p, bg=C["card"], padx=20, pady=14)
        req_card.pack(fill="x", padx=16, pady=(0,12))
        tk.Label(req_card, text="REQUIREMENTS.TXT",
                 bg=C["card"], fg=C["muted"], font=FONT_SMALL).pack(anchor="w")
        req_row = tk.Frame(req_card, bg=C["card"])
        req_row.pack(fill="x", pady=(6,0))
        self._req_var = tk.StringVar()
        req_e = tk.Entry(req_row, textvariable=self._req_var,
                 bg=C["input_bg"], fg=C["fg"],
                 insertbackground=C["accent"],
                 relief="flat", bd=0, font=FONT_MONO,
                 highlightthickness=1,
                 highlightbackground=C["border"],
                 highlightcolor=C["accent"])
        req_e.pack(side="left", fill="x", expand=True, ipady=5)
        self._attach_context_menu(req_e)
        self._btn(req_row, "Gözat",  self._browse_req,      "secondary").pack(side="left", padx=(8,2))
        self._btn(req_row, "Yükle",  self._install_req,     "primary")  .pack(side="left", padx=2)
        self._btn(req_row, "Oluştur",self._generate_req,    "secondary").pack(side="left", padx=2)

    # ── Güncelle sekmesi ───────────────────────
    def _build_tab_upgrade(self):
        p = self._tab_upgrade

        top = tk.Frame(p, bg=C["bg"], padx=14, pady=12)
        top.pack(fill="x")

        self._btn(top, "⬆ Tümünü Güncelle", self._upgrade_all,  "primary") .pack(side="left", padx=(0,6))
        self._btn(top, "↺ Listeyi Tazele",  self._check_outdated,"secondary").pack(side="left", padx=6)
        self._btn(top, "⏹ Durdur",          self._stop,          "danger")   .pack(side="right")

        # Güncelleme listesi
        cols2 = ("name", "current", "latest", "type")
        self._upd_tree = ttk.Treeview(p, columns=cols2, show="headings",
                                       selectmode="extended")
        self._upd_tree.heading("name",    text="Paket",         anchor="w")
        self._upd_tree.heading("current", text="Mevcut Sürüm",  anchor="w")
        self._upd_tree.heading("latest",  text="Yeni Sürüm",    anchor="w")
        self._upd_tree.heading("type",    text="Tür",           anchor="w")
        self._upd_tree.column("name",    width=220)
        self._upd_tree.column("current", width=120)
        self._upd_tree.column("latest",  width=120)
        self._upd_tree.column("type",    width=100)

        sb2 = ttk.Scrollbar(p, orient="vertical", command=self._upd_tree.yview)
        self._upd_tree.configure(yscrollcommand=sb2.set)

        frame2 = tk.Frame(p, bg=C["bg"])
        frame2.pack(fill="both", expand=True, padx=12, pady=(0,8))
        self._upd_tree.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")

    # ── Konsol sekmesi ─────────────────────────
    def _build_tab_console(self):
        p = self._tab_console

        # Çıktı alanı
        out_frame = tk.Frame(p, bg=C["bg"])
        out_frame.pack(fill="both", expand=True, padx=12, pady=(12,0))

        self._console = tk.Text(out_frame,
                                bg=C["input_bg"], fg="#a8e6a8",
                                insertbackground=C["accent"],
                                relief="flat", bd=0,
                                font=FONT_MONO,
                                wrap="word", state="disabled",
                                highlightthickness=1,
                                highlightbackground=C["border"])
        csb = ttk.Scrollbar(out_frame, orient="vertical",
                            command=self._console.yview)
        self._console.configure(yscrollcommand=csb.set)
        self._console.pack(side="left", fill="both", expand=True)
        csb.pack(side="right", fill="y")

        # Renk tag'leri
        self._console.tag_config("ok",    foreground="#5dba7d")
        self._console.tag_config("err",   foreground="#f7786a")
        self._console.tag_config("warn",  foreground="#f0c060")
        self._console.tag_config("info",  foreground="#7c9ff7")
        self._console.tag_config("head",  foreground=C["accent"],
                                          font=FONT_MONO_B)

        # Komut satırı
        cmd_row = tk.Frame(p, bg=C["panel"], padx=12, pady=8)
        cmd_row.pack(fill="x")
        tk.Label(cmd_row, text="pip", bg=C["panel"], fg=C["muted"],
                 font=FONT_MONO_B).pack(side="left")
        self._cmd_var = tk.StringVar()
        ce = tk.Entry(cmd_row, textvariable=self._cmd_var,
                      bg=C["input_bg"], fg=C["fg"],
                      insertbackground=C["accent"],
                      relief="flat", bd=0, font=FONT_MONO,
                      highlightthickness=1,
                      highlightbackground=C["border"],
                      highlightcolor=C["accent"])
        ce.pack(side="left", fill="x", expand=True, padx=8, ipady=4)
        ce.bind("<Return>", lambda _: self._run_custom_cmd())
        self._attach_context_menu(ce)
        self._btn(cmd_row, "Çalıştır",  self._run_custom_cmd, "primary") .pack(side="left", padx=2)
        self._btn(cmd_row, "Temizle",   self._clear_console,  "secondary").pack(side="left", padx=2)

    # ──────────────────────────────────────────
    #  SAĞ TIK MENÜSÜ (tüm Entry'lere bağlanır)
    # ──────────────────────────────────────────
    def _attach_context_menu(self, widget):
        """Herhangi bir Entry'e sağ tık Kes/Kopyala/Yapıştır/Tümünü Seç menüsü ekler."""
        menu = tk.Menu(widget, tearoff=0,
                       bg=C["card"], fg=C["fg"],
                       activebackground=C["accent"],
                       activeforeground="#fff",
                       relief="flat", bd=0,
                       font=FONT_UI)
        menu.add_command(label="Kes",            command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Kopyala",        command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_separator()
        menu.add_command(label="Yapıştır",       command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_command(label="Tümünü Seç",     command=lambda: widget.select_range(0, "end"))
        menu.add_command(label="Temizle",        command=lambda: widget.delete(0, "end"))

        def _show(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        widget.bind("<Button-3>", _show)

    # ──────────────────────────────────────────
    #  YARDIMCI WİDGET OLUŞTURUCULAR
    # ──────────────────────────────────────────
    def _btn(self, parent, text, cmd, style="primary"):
        colors = {
            "primary":   (C["accent"],  "#fff"),
            "secondary": (C["card"],    C["fg"]),
            "danger":    (C["red"],     "#fff"),
        }
        bg, fg = colors.get(style, (C["accent"], "#fff"))
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg,
                         font=FONT_UI_B,
                         relief="flat", bd=0,
                         padx=12, pady=5,
                         cursor="hand2",
                         activebackground=C["border"],
                         activeforeground=C["fg"])

    def _stat_card(self, parent, label, value, color):
        f = tk.Frame(parent, bg=C["card"], padx=16, pady=8)
        f.pack(side="left", padx=(0,8))
        tk.Label(f, text=label, bg=C["card"], fg=C["muted"],
                 font=FONT_SMALL).pack(anchor="w")
        lbl = tk.Label(f, text=value, bg=C["card"], fg=color,
                       font=("Segoe UI", 18, "bold"))
        lbl.pack(anchor="w")
        return lbl

    # ──────────────────────────────────────────
    #  KONSOL ÇIKTI
    # ──────────────────────────────────────────
    def _log(self, text: str, tag=""):
        def _write():
            self._console.configure(state="normal")
            if not tag:
                lo = text.lower()
                if any(w in lo for w in ["error", "hata", "failed", "no module"]):
                    t = "err"
                elif any(w in lo for w in ["warning", "warn"]):
                    t = "warn"
                elif any(w in lo for w in ["successfully", "already", "basarili"]):
                    t = "ok"
                else:
                    t = ""
            else:
                t = tag
            self._console.insert("end", text + "\n", t)
            self._console.see("end")
            self._console.configure(state="disabled")
        self.root.after(0, _write)

    def _clear_console(self):
        self._console.configure(state="normal")
        self._console.delete("1.0", "end")
        self._console.configure(state="disabled")

    def _set_status(self, text: str):
        self.root.after(0, lambda: self._status_var.set(text))

    def _start_progress(self):
        self._running = True
        self.root.after(0, self._progress.start)

    def _stop_progress(self):
        self._running = False
        self.root.after(0, self._progress.stop)

    # ──────────────────────────────────────────
    #  PAKET LİSTESİ
    # ──────────────────────────────────────────
    def _refresh_packages(self):
        interp = self._interp_var.get().strip()

        # EXE modunda yanlış yorumlayıcı seçilmişse uyar
        if _is_exe_mode() and (not interp or not _verify_python(interp)):
            self._set_status("⚠ Geçerli bir Python yorumlayıcısı seçin")
            self._log("Python bulunamadi. Lutfen 'Gozat' ile python.exe secin.", "err")
            return
        self._set_status("Paketler yükleniyor…")
        self._start_progress()

        def _worker():
            pkgs = get_packages(interp)
            self._packages = pkgs
            # Python sürümünü al
            try:
                res = subprocess.run(
                    [interp, "--version"],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                        if sys.platform == "win32" else 0
                )
                py_ver = res.stdout.strip() or res.stderr.strip()
            except Exception:
                py_ver = ""
            self.root.after(0, lambda: self._py_ver_lbl.config(text=py_ver))
            self.root.after(0, self._populate_tree)
            self._stop_progress()
            self._set_status(f"{len(pkgs)} paket yüklendi")
            self._log(f"[{datetime.now():%H:%M:%S}] {len(pkgs)} paket listelendi — {interp}", "info")

        threading.Thread(target=_worker, daemon=True).start()

    def _check_outdated(self):
        interp = self._interp_var.get()
        self._set_status("Güncel olmayan paketler kontrol ediliyor…")
        self._start_progress()
        self._log("Güncel olmayan paketler kontrol ediliyor…", "info")

        def _worker():
            outdated = get_outdated(interp)
            self._outdated = outdated
            self.root.after(0, self._populate_upd_tree)
            self._stop_progress()
            self._set_status(f"{len(outdated)} paket güncellenebilir")
            self._log(f"{len(outdated)} paket güncellenebilir", "ok" if outdated else "info")

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_tree(self):
        outdated_names = {d["name"].lower() for d in self._outdated}
        self._tree.delete(*self._tree.get_children())
        q = self._search_var.get().lower()
        show_outdated = self._filter_var.get() == "Güncel Değil"

        for pkg in self._packages:
            name = pkg.get("name", "")
            ver  = pkg.get("version", "")
            if q and q not in name.lower():
                continue
            is_out = name.lower() in outdated_names
            if show_outdated and not is_out:
                continue
            latest  = ""
            status  = "⚠ Güncel Değil" if is_out else "✓ Güncel"
            tag     = "outdated" if is_out else ""
            iid = self._tree.insert("", "end",
                                    values=(name, ver, latest, status),
                                    tags=(tag,))
        self._tree.tag_configure("outdated", foreground=C["yellow"])
        self._stat_total.config(text=str(len(self._packages)))
        self._stat_outdated.config(text=str(len(self._outdated)))

    def _populate_upd_tree(self):
        self._upd_tree.delete(*self._upd_tree.get_children())
        for d in sorted(self._outdated, key=lambda x: x["name"].lower()):
            self._upd_tree.insert("", "end", values=(
                d.get("name",""),
                d.get("version",""),
                d.get("latest_version",""),
                d.get("latest_filetype","wheel"),
            ))

    def _filter_packages(self):
        self._populate_tree()

    # ──────────────────────────────────────────
    #  YÜKLE / KALDIR
    # ──────────────────────────────────────────
    def _quick_install(self):
        """Sadece modül adı/adları yazarak hızlı yükleme (virgülle çoklu)."""
        raw = self._quick_var.get().strip()
        if not raw:
            self._set_status("⚠ Paket adı girin")
            return
        names = [n.strip() for n in raw.replace(";", ",").split(",") if n.strip()]
        if not names:
            return
        args = ["install"] + names
        self._run_pip_cmd(args, f"Yükleniyor: {', '.join(names)}")
        self._quick_var.set("")

    def _quick_uninstall(self):
        """Hızlı kaldırma (quick entry'den)."""
        raw = self._quick_var.get().strip()
        if not raw:
            self._set_status("⚠ Paket adı girin")
            return
        names = [n.strip() for n in raw.replace(";", ",").split(",") if n.strip()]
        if not names:
            return
        if not messagebox.askyesno("Onay", f"Kaldırılsın mı?\n{', '.join(names)}"):
            return
        args = ["uninstall", "-y"] + names
        self._run_pip_cmd(args, f"Kaldırılıyor: {', '.join(names)}")
        self._quick_var.set("")

    def _build_install_cmd(self) -> list[str]:
        name = self._pkg_var.get().strip()
        ver  = self._ver_var.get().strip()
        if not name:
            return []
        spec = name
        if ver:
            if ver[0].isdigit():
                spec = f"{name}=={ver}"
            else:
                spec = f"{name}{ver}"
        args = ["install", spec]
        if self._upgrade_flag.get(): args.append("--upgrade")
        if self._user_flag.get():    args.append("--user")
        if self._pre_flag.get():     args.append("--pre")
        return args

    def _install(self):
        args = self._build_install_cmd()
        if not args:
            self._set_status("⚠ Paket adı girin")
            return
        self._run_pip_cmd(args, f"Yükleniyor: {args[1]}")

    def _uninstall(self):
        name = self._pkg_var.get().strip()
        if not name:
            return
        if not messagebox.askyesno("Onay", f"'{name}' kaldırılsın mı?"):
            return
        self._run_pip_cmd(["uninstall", "-y", name], f"Kaldırılıyor: {name}")

    def _uninstall_selected(self):
        sel = self._tree.selection()
        if not sel:
            return
        names = [self._tree.item(i, "values")[0] for i in sel]
        if not messagebox.askyesno("Onay",
                f"{len(names)} paket kaldırılsın mı?\n" + ", ".join(names[:5])):
            return
        args = ["uninstall", "-y"] + names
        self._run_pip_cmd(args, f"{len(names)} paket kaldırılıyor")

    def _upgrade_selected(self):
        sel = self._tree.selection()
        if not sel:
            return
        names = [self._tree.item(i, "values")[0] for i in sel]
        for name in names:
            self._run_pip_cmd(["install", "--upgrade", name],
                              f"Güncelleniyor: {name}")

    # ──────────────────────────────────────────
    #  REQUIREMENTS
    # ──────────────────────────────────────────
    def _browse_req(self):
        path = filedialog.askopenfilename(
            filetypes=[("Requirements", "*.txt"), ("Tüm Dosyalar", "*.*")])
        if path:
            self._req_var.set(path)

    def _install_req(self):
        path = self._req_var.get().strip()
        if not path or not os.path.isfile(path):
            self._set_status("⚠ Geçerli bir requirements.txt seçin")
            return
        self._run_pip_cmd(["-r", path], f"requirements.txt yükleniyor: {path}",
                          prefix="install")

    def _generate_req(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Requirements", "*.txt")],
            initialfile="requirements.txt")
        if not path:
            return
        interp = self._interp_var.get()
        try:
            res = subprocess.run(
                [interp, "-m", "pip", "freeze"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32" else 0
            )
            Path(path).write_text(res.stdout, encoding="utf-8")
            self._log(f"requirements.txt oluşturuldu: {path}", "ok")
            self._set_status(f"Oluşturuldu: {path}")
        except Exception as e:
            self._log(f"Hata: {e}", "err")

    # ──────────────────────────────────────────
    #  TOPLU GÜNCELLEME
    # ──────────────────────────────────────────
    def _upgrade_all(self):
        if not self._outdated:
            messagebox.showinfo("Bilgi",
                "Güncelleme listesi boş.\nÖnce 'Listeyi Tazele' butonuna basın.")
            return
        names = [d["name"] for d in self._outdated]
        if not messagebox.askyesno("Onay",
                f"{len(names)} paket güncellenecek. Devam?"):
            return
        self._stop_flag = False
        self._log(f"{'='*50}", "head")
        self._log(f"  TOPLU GÜNCELLEME — {len(names)} paket", "head")
        self._log(f"{'='*50}", "head")
        self._start_progress()

        def _worker():
            for i, name in enumerate(names, 1):
                if self._stop_flag:
                    self._log("⏹ Durduruldu.", "warn")
                    break
                self._set_status(f"[{i}/{len(names)}] {name} güncelleniyor…")
                self._log(f"\n[{i}/{len(names)}] {name}…", "info")
                interp = self._interp_var.get()
                res = subprocess.run(
                    [interp, "-m", "pip", "install", "--upgrade", name],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                        if sys.platform == "win32" else 0
                )
                tag = "ok" if res.returncode == 0 else "err"
                out = (res.stdout + res.stderr).strip()
                for line in out.splitlines()[-3:]:
                    self._log(f"  {line}", tag)
            self._stop_progress()
            self._set_status("Güncelleme tamamlandı")
            self._log("✓ Güncelleme tamamlandı.", "ok")
            self.root.after(1000, self._refresh_packages)

        threading.Thread(target=_worker, daemon=True).start()

    # ──────────────────────────────────────────
    #  GENEL PIP ÇALIŞTIRICI
    # ──────────────────────────────────────────
    def _run_pip_cmd(self, args: list[str], label: str, prefix=""):
        interp = self._interp_var.get()
        if prefix:
            args = [prefix] + args
        self._log(f"\n$ pip {' '.join(args)}", "head")
        self._set_status(label)
        self._start_progress()

        def _done(rc):
            self._stop_progress()
            if rc == 0:
                self._set_status(f"✓ Tamamlandı: {label}")
                self._log("✓ Tamamlandı.", "ok")
            else:
                self._set_status(f"✗ Hata: {label}")
            self.root.after(500, self._refresh_packages)

        run_pip(interp, args, on_line=self._log, on_done=_done)

    def _run_custom_cmd(self):
        cmd = self._cmd_var.get().strip()
        if not cmd:
            return
        args = cmd.split()
        self._cmd_var.set("")
        self._run_pip_cmd(args, f"pip {cmd}")

    def _stop(self):
        self._stop_flag = True
        self._set_status("Durduruluyor…")

    # ──────────────────────────────────────────
    #  DİĞER
    # ──────────────────────────────────────────
    def _browse_python(self):
        path = filedialog.askopenfilename(
            filetypes=[("Python", "python*.exe python*"),
                       ("Tüm Dosyalar", "*.*")])
        if path:
            self._interp_var.set(path)
            vals = list(self._interp_combo["values"])
            if path not in vals:
                vals.insert(0, path)
                self._interp_combo["values"] = vals
            self._refresh_packages()


# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = PipManagerPro(root)
    root.mainloop()
