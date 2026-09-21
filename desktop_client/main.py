import os
import sys
import re
import json
import shutil
import zipfile
import threading
import subprocess
import ctypes
import webbrowser
import urllib.request
import winreg
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(APP_DIR, "bin")


def find_installed_usbip(bin_dir):
    # 1. System PATH
    found = shutil.which("usbip") or shutil.which("usbip.exe")
    if found and os.path.isfile(found):
        return found, "Installed"

    # 2. Standard Program Files installation directories
    candidate_paths = [
        r"C:\Program Files\usbip\usbip.exe",
        r"C:\Program Files\usbip-win\usbip.exe",
        r"C:\Program Files (x86)\usbip\usbip.exe",
        r"C:\Program Files (x86)\usbip-win\usbip.exe",
        r"C:\usbip\usbip.exe",
    ]

    prog_files = os.environ.get("ProgramFiles")
    if prog_files:
        candidate_paths.append(os.path.join(prog_files, "usbip", "usbip.exe"))
        candidate_paths.append(os.path.join(prog_files, "usbip-win", "usbip.exe"))

    prog_files_x86 = os.environ.get("ProgramFiles(x86)")
    if prog_files_x86:
        candidate_paths.append(os.path.join(prog_files_x86, "usbip", "usbip.exe"))

    prog_w6432 = os.environ.get("ProgramW6432")
    if prog_w6432:
        candidate_paths.append(os.path.join(prog_w6432, "usbip", "usbip.exe"))

    for p in candidate_paths:
        if os.path.isfile(p):
            return p, "Installed"

    # 3. Search Windows Registry for installed program location
    try:
        reg_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for root, subkey in reg_roots:
            try:
                with winreg.OpenKey(root, subkey) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            app_subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, app_subkey_name) as app_key:
                                display_name = ""
                                install_loc = ""
                                try:
                                    display_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                except OSError:
                                    pass
                                try:
                                    install_loc, _ = winreg.QueryValueEx(app_key, "InstallLocation")
                                except OSError:
                                    pass

                                if "usbip" in display_name.lower():
                                    if install_loc and os.path.isdir(install_loc):
                                        target = os.path.join(install_loc, "usbip.exe")
                                        if os.path.isfile(target):
                                            return target, f"Installed ({display_name})"
                        except OSError:
                            continue
            except OSError:
                continue
    except Exception:
        pass

    # 4. Local client directory
    local_usbip = os.path.join(bin_dir, "usbip", "usbip.exe")
    if os.path.isfile(local_usbip):
        return local_usbip, "Installed (Local)"

    return None, "Missing"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin():
    try:
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to restart as admin: {e}")


class OsuTabletCompanion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("tabletizer!")
        self.geometry("780x640")
        self.minsize(700, 580)
        self.configure(bg="#121214")

        self.adb_path = None
        self.usbip_path = None
        self.is_connected = False

        self.setup_styles()
        self.build_ui()

        # Initial check in background
        self.after(300, self.refresh_environment)

    def setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Dark theme color palette
        self.style.configure(".", background="#121214", foreground="#E4E4E7", font=("Segoe UI", 10))
        self.style.configure("Card.TFrame", background="#1E1E24", relief="flat")
        self.style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), foreground="#38BDF8", background="#1E1E24")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 11, "bold"), foreground="#F43F5E", background="#1E1E24")
        self.style.configure("Status.TLabel", font=("Segoe UI", 9), background="#1E1E24")
        self.style.configure("BadgeGreen.TLabel", foreground="#4ADE80", background="#1E1E24", font=("Segoe UI", 9, "bold"))
        self.style.configure("BadgeRed.TLabel", foreground="#F87171", background="#1E1E24", font=("Segoe UI", 9, "bold"))
        self.style.configure("BadgeYellow.TLabel", foreground="#FBBF24", background="#1E1E24", font=("Segoe UI", 9, "bold"))
        self.style.configure("TEntry", fieldbackground="#27272A", foreground="#FFFFFF", bordercolor="#3F3F46", lightcolor="#3F3F46", darkcolor="#3F3F46")
        self.style.map("TEntry", fieldbackground=[("disabled", "#1E1E24")], foreground=[("disabled", "#71717A")])

        # Buttons
        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=6)
        self.style.configure("Connect.TButton", font=("Segoe UI", 12, "bold"), padding=10, foreground="#000000", background="#4ADE80")
        self.style.configure("Disconnect.TButton", font=("Segoe UI", 12, "bold"), padding=10, foreground="#FFFFFF", background="#EF4444")

    def build_ui(self):
        # Admin banner if not running as admin
        if not is_admin():
            banner = tk.Frame(self, bg="#DC2626", padx=10, pady=6)
            banner.pack(fill="x")
            lbl = tk.Label(banner, text="Administrator rights are required for USBip driver binding! (maybe)",
                           bg="#DC2626", fg="#FFFFFF", font=("Segoe UI", 9, "bold"))
            lbl.pack(side="left", padx=5)
            btn = tk.Button(banner, text="Restart as Admin", command=run_as_admin,
                            bg="#FFFFFF", fg="#DC2626", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2")
            btn.pack(side="right", padx=5)

        main_container = tk.Frame(self, bg="#121214", padx=16, pady=12)
        main_container.pack(fill="both", expand=True)

        # Title section
        top_bar = tk.Frame(main_container, bg="#121214")
        top_bar.pack(fill="x", pady=(0, 8))
        tk.Label(top_bar, text="tabletizer!", font=("Segoe UI", 15, "bold"),
                 fg="#38BDF8", bg="#121214").pack(side="left")
        btn_refresh = tk.Button(top_bar, text="Refresh Tools", command=self.refresh_environment,
                                bg="#27272A", fg="#E4E4E7", font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=8, pady=3)
        btn_refresh.pack(side="right")

        # Top Card: Dependencies & Environment
        dep_card = ttk.Frame(main_container, style="Card.TFrame", padding=12)
        dep_card.pack(fill="x", pady=4)

        ttk.Label(dep_card, text="Requirements & Tools", style="Header.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        # 1. Platform Tools (ADB)
        ttk.Label(dep_card, text="Android Platform Tools (ADB):", style="Status.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        self.lbl_adb_status = ttk.Label(dep_card, text="Checking...", style="BadgeYellow.TLabel")
        self.lbl_adb_status.grid(row=1, column=1, sticky="w", padx=10, pady=4)
        self.btn_dl_adb = tk.Button(dep_card, text="Download ADB", command=self.start_download_adb,
                                    bg="#38BDF8", fg="#000000", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2")
        self.btn_dl_adb.grid(row=1, column=2, sticky="e", padx=5, pady=4)

        # 2. USBip Tool
        ttk.Label(dep_card, text="USBip Driver & Client:", style="Status.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        self.lbl_usbip_status = ttk.Label(dep_card, text="Checking...", style="BadgeYellow.TLabel")
        self.lbl_usbip_status.grid(row=2, column=1, sticky="w", padx=10, pady=4)
        self.btn_dl_usbip = tk.Button(dep_card, text="Get USBip", command=self.start_download_usbip,
                                      bg="#38BDF8", fg="#000000", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2")
        self.btn_dl_usbip.grid(row=2, column=2, sticky="e", padx=5, pady=4)

        # 3. OpenTabletDriver Config
        ttk.Label(dep_card, text="OpenTabletDriver Profile:", style="Status.TLabel").grid(row=3, column=0, sticky="w", pady=4)
        self.lbl_otd_status = ttk.Label(dep_card, text="Checking...", style="BadgeYellow.TLabel")
        self.lbl_otd_status.grid(row=3, column=1, sticky="w", padx=10, pady=4)

        otd_btn_frame = tk.Frame(dep_card, bg="#1E1E24")
        otd_btn_frame.grid(row=3, column=2, sticky="e", padx=5, pady=4)

        self.btn_gen_otd = tk.Button(otd_btn_frame, text="Auto-Generate Profile", command=self.generate_otd_config,
                                     bg="#10B981", fg="#000000", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6)
        self.btn_gen_otd.pack(side="left", padx=(0, 4))

        self.btn_manual_otd = tk.Button(otd_btn_frame, text="Manual Config", command=self.manual_otd_config,
                                        bg="#3B82F6", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6)
        self.btn_manual_otd.pack(side="left", padx=(0, 4))

        self.btn_sync_otd = tk.Button(otd_btn_frame, text="Sync Existing", command=self.sync_otd_config,
                                      bg="#3F3F46", fg="#E4E4E7", font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=6)
        self.btn_sync_otd.pack(side="left")

        dep_card.columnconfigure(0, weight=2)
        dep_card.columnconfigure(1, weight=3)
        dep_card.columnconfigure(2, weight=2)

        # Middle Card: Connection Controls
        ctrl_card = ttk.Frame(main_container, style="Card.TFrame", padding=12)
        ctrl_card.pack(fill="x", pady=4)

        ttk.Label(ctrl_card, text="Connection Panel", style="Header.TLabel").pack(anchor="w", pady=(0, 4))

        device_frame = tk.Frame(ctrl_card, bg="#1E1E24")
        device_frame.pack(fill="x", pady=4)
        tk.Label(device_frame, text="Connected Android Device:", font=("Segoe UI", 10), bg="#1E1E24", fg="#A1A1AA").pack(side="left")
        self.lbl_device_info = tk.Label(device_frame, text="Scanning...", font=("Segoe UI", 10, "bold"), bg="#1E1E24", fg="#FBBF24")
        self.lbl_device_info.pack(side="left", padx=8)

        # Connection Mode Radio / Inputs
        mode_frame = tk.Frame(ctrl_card, bg="#1E1E24")
        mode_frame.pack(fill="x", pady=4)

        self.conn_mode = tk.StringVar(value="wired")
        r_wired = tk.Radiobutton(mode_frame, text="Wired USB (Lowest Latency, recommended)",
                                 variable=self.conn_mode, value="wired", command=self.update_mode_ui,
                                 bg="#1E1E24", fg="#E4E4E7", selectcolor="#27272A", activebackground="#1E1E24", font=("Segoe UI", 9))
        r_wired.pack(anchor="w")

        wireless_box = tk.Frame(mode_frame, bg="#1E1E24")
        wireless_box.pack(anchor="w", fill="x", pady=(2, 0))
        r_wifi = tk.Radiobutton(wireless_box, text="Wireless (Wi-Fi IP):",
                                variable=self.conn_mode, value="wireless", command=self.update_mode_ui,
                                bg="#1E1E24", fg="#E4E4E7", selectcolor="#27272A", activebackground="#1E1E24", font=("Segoe UI", 9))
        r_wifi.pack(side="left")
        self.entry_ip = tk.Entry(wireless_box, width=16, font=("Segoe UI", 9), bg="#27272A", fg="#FFFFFF", insertbackground="#FFFFFF", relief="flat")
        self.entry_ip.insert(0, "192.168.1.100")
        self.entry_ip.pack(side="left", padx=6)
        self.entry_ip.config(state="disabled")

        # Action Buttons
        btn_box = tk.Frame(ctrl_card, bg="#1E1E24")
        btn_box.pack(fill="x", pady=(8, 2))

        self.btn_connect = tk.Button(btn_box, text="Connect device", command=self.on_connect_clicked,
                                     bg="#22C55E", fg="#000000", font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", padx=16, pady=8)
        self.btn_connect.pack(expand=True, fill="x")

        # Bottom: Activity Log
        log_frame = tk.Frame(main_container, bg="#121214")
        log_frame.pack(fill="both", expand=True, pady=(4, 0))
        tk.Label(log_frame, text="Activity Log", font=("Segoe UI", 9, "bold"), fg="#A1A1AA", bg="#121214").pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, bg="#18181B", fg="#A1A1AA",
                                                   font=("Consolas", 9), insertbackground="#FFFFFF", relief="flat", borderwidth=0)
        self.log_text.pack(fill="both", expand=True, pady=4)

    def log(self, text):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def update_mode_ui(self):
        if self.conn_mode.get() == "wireless":
            self.entry_ip.config(state="normal")
        else:
            self.entry_ip.config(state="disabled")

    # ---------------- Environment Detection ----------------
    def refresh_environment(self):
        threading.Thread(target=self._check_environment_thread, daemon=True).start()

    def _check_environment_thread(self):
        self.log("🔍 Checking environment and tools...")

        # 1. Check ADB
        adb = shutil.which("adb")
        local_adb = os.path.join(BIN_DIR, "platform-tools", "adb.exe")
        if adb:
            self.adb_path = adb
            self.lbl_adb_status.config(text="Installed (System)", style="BadgeGreen.TLabel")
            self.btn_dl_adb.config(state="disabled")
        elif os.path.exists(local_adb):
            self.adb_path = local_adb
            self.lbl_adb_status.config(text="Installed (Local)", style="BadgeGreen.TLabel")
            self.btn_dl_adb.config(state="disabled")
        else:
            self.adb_path = None
            self.lbl_adb_status.config(text="Missing", style="BadgeRed.TLabel")
            self.btn_dl_adb.config(state="normal")

        # 2. Check USBip
        path, status = find_installed_usbip(BIN_DIR)
        self.usbip_path = path
        if path:
            self.lbl_usbip_status.config(text=status, style="BadgeGreen.TLabel")
            self.btn_dl_usbip.config(state="disabled")
        else:
            self.lbl_usbip_status.config(text="Missing", style="BadgeRed.TLabel")
            self.btn_dl_usbip.config(state="normal")

        # 3. Check OTD Config
        otd_dirs = self.find_otd_dirs()
        installed_name = None
        for d in otd_dirs:
            for sub in ["Configurations", os.path.join("userdata", "Configurations")]:
                cfg_path = os.path.join(d, sub, "AndroidTablet.json")
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            installed_name = data.get("Name", "Configured")
                            break
                    except Exception:
                        installed_name = "Configured"
            if installed_name:
                break

        if installed_name:
            self.lbl_otd_status.config(text=f"Installed ({installed_name})", style="BadgeGreen.TLabel")
        else:
            self.lbl_otd_status.config(text="Not Configured", style="BadgeYellow.TLabel")

        # 4. Check Phone via ADB
        self.check_connected_phone()

        # 5. Check USBip Connection
        self.check_usbip_connection()

    def check_usbip_connection(self):
        if not self.usbip_path:
            return
            
        try:
            # CREATE_NO_WINDOW = 0x08000000 to prevent console flash
            usbip_dir = os.path.dirname(self.usbip_path)
            res = subprocess.run([self.usbip_path, "port"], capture_output=True, text=True, timeout=3, creationflags=0x08000000, cwd=usbip_dir)
            out = res.stdout

            is_attached = False
            if "Port in Use" in out:
                is_attached = True
            elif "Port 00:" in out and "Available" not in out:
                is_attached = True

            if is_attached:
                self.is_connected = True
                self.btn_connect.config(text="Reconnect device", bg="#FBBF24", fg="#000000")
                self.log("🔗 Detected active USBip connection.")
            else:
                self.is_connected = False
                self.btn_connect.config(text="Connect device", bg="#22C55E", fg="#000000")
        except Exception:
            pass

    def find_otd_dirs(self):
        dirs = []
        appdata_otd = os.path.expandvars(r"%LOCALAPPDATA%\OpenTabletDriver")
        if os.path.exists(appdata_otd):
            dirs.append(appdata_otd)

        # Check Desktop and drives for portable OTD
        for dt in [os.path.expanduser(r"~\Desktop"), r"D:\Users\hrdcoreee\Desktop"]:
            if os.path.exists(dt):
                for item in os.listdir(dt):
                    if "OpenTabletDriver" in item and os.path.isdir(os.path.join(dt, item)):
                        dirs.append(os.path.join(dt, item))
        return list(set(dirs))

    def check_connected_phone(self):
        if not self.adb_path:
            self.lbl_device_info.config(text="ADB not available", fg="#F87171")
            return

        try:
            res = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, timeout=5, creationflags=0x08000000)
            lines = res.stdout.strip().splitlines()
            devices = [line.split()[0] for line in lines[1:] if "\tdevice" in line]
            if devices:
                dev_id = devices[0]
                market = subprocess.run([self.adb_path, "-s", dev_id, "shell", "getprop", "ro.product.marketname"],
                                        capture_output=True, text=True, timeout=3, creationflags=0x08000000).stdout.strip()
                if not market:
                    model = subprocess.run([self.adb_path, "-s", dev_id, "shell", "getprop", "ro.product.model"],
                                           capture_output=True, text=True, timeout=3, creationflags=0x08000000).stdout.strip()
                    model_text = model or dev_id
                else:
                    model_text = market

                self.lbl_device_info.config(text=f"🟢 {model_text} ({dev_id})", fg="#4ADE80")
                self.log(f"📱 Detected phone: {model_text} [{dev_id}]")
            else:
                self.lbl_device_info.config(text="No device found (Connect USB cable)", fg="#FBBF24")
        except Exception:
            self.lbl_device_info.config(text="ADB check error", fg="#F87171")

    # ---------------- Downloader Methods ----------------
    def start_download_adb(self):
        threading.Thread(target=self._download_adb_thread, daemon=True).start()

    def _download_adb_thread(self):
        try:
            self.log("📥 Downloading Google Android Platform-Tools (ADB)...")
            os.makedirs(BIN_DIR, exist_ok=True)
            zip_dest = os.path.join(BIN_DIR, "platform-tools.zip")

            urllib.request.urlretrieve(PLATFORM_TOOLS_URL, zip_dest)
            self.log("📦 Extracting platform-tools...")
            with zipfile.ZipFile(zip_dest, "r") as z:
                z.extractall(BIN_DIR)
            os.remove(zip_dest)

            self.log("✅ Platform Tools successfully installed!")
            self.refresh_environment()
        except Exception as e:
            self.log(f"❌ Failed to download ADB: {e}")
            messagebox.showerror("Download Error", f"Could not download ADB:\n{e}")

    def start_download_usbip(self):
        self.log("🔗 Opening USBip releases page in your browser...")
        webbrowser.open("https://github.com/vadimgrn/usbip-win2/releases/latest")
        messagebox.showinfo("USBip Installation",
                            "Please download and run the installer from the GitHub releases page.\n\n"
                            "Once installed, click 'Refresh Tools' in this app.")

    # ---------------- Profile Auto-Generator ----------------
    def generate_otd_config(self):
        if not self.adb_path:
            messagebox.showwarning("ADB Missing", "Platform Tools (ADB) is required to inspect connected device.")
            return
        
        from tkinter import filedialog
        otd_dir = filedialog.askdirectory(title="Select OpenTabletDriver Installation Folder")
        if not otd_dir:
            return
            
        threading.Thread(target=self._generate_otd_thread, args=(otd_dir,), daemon=True).start()

    def _generate_otd_thread(self, otd_dir):
        self.log("\n⚡ Auto-detecting device specifications for OpenTabletDriver...")
        try:
            # Check device
            res = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, timeout=5)
            lines = res.stdout.strip().splitlines()
            devices = [line.split()[0] for line in lines[1:] if "\tdevice" in line]
            if not devices:
                self.log("❌ No Android device detected via ADB.")
                messagebox.showerror("Device Not Found", "No Android device found via ADB.\nPlease connect your device and enable USB debugging.")
                return

            dev_id = devices[0]

            # Get device friendly name
            market = subprocess.run([self.adb_path, "-s", dev_id, "shell", "getprop", "ro.product.marketname"],
                                    capture_output=True, text=True, timeout=3).stdout.strip()
            if not market:
                brand = subprocess.run([self.adb_path, "-s", dev_id, "shell", "getprop", "ro.product.brand"],
                                       capture_output=True, text=True, timeout=3).stdout.strip().capitalize()
                model = subprocess.run([self.adb_path, "-s", dev_id, "shell", "getprop", "ro.product.model"],
                                       capture_output=True, text=True, timeout=3).stdout.strip()
                device_name = f"{brand} {model}".strip() if (brand or model) else "Android Tablet"
            else:
                device_name = market

            # Get Resolution
            dumpsys_res = subprocess.run([self.adb_path, "-s", dev_id, "shell", "dumpsys", "display"],
                                         capture_output=True, text=True, timeout=5).stdout

            m_res = re.search(r'real (\d+) x (\d+)', dumpsys_res)
            if not m_res:
                wm_res = subprocess.run([self.adb_path, "-s", dev_id, "shell", "wm", "size"],
                                        capture_output=True, text=True, timeout=3).stdout
                m_res = re.search(r'(\d+)x(\d+)', wm_res)

            if m_res:
                p1, p2 = int(m_res.group(1)), int(m_res.group(2))
                max_x = max(p1, p2)
                max_y = min(p1, p2)
            else:
                max_x = 2400
                max_y = 1080

            # Get DPI
            m_dpi = re.search(r'density \d+ \((\d+\.?\d*) x (\d+\.?\d*)\) dpi', dumpsys_res)
            if not m_dpi:
                m_dpi = re.search(r'xDpi=(\d+\.?\d*), yDpi=(\d+\.?\d*)', dumpsys_res)

            if m_dpi:
                dpi_x = float(m_dpi.group(1))
                dpi_y = float(m_dpi.group(2))
            else:
                wm_density = subprocess.run([self.adb_path, "-s", dev_id, "shell", "wm", "density"],
                                            capture_output=True, text=True, timeout=3).stdout
                m_dens = re.search(r'(\d+)', wm_density)
                base_dpi = float(m_dens.group(1)) if m_dens else 400.0
                dpi_x = base_dpi
                dpi_y = base_dpi

            # Calculate physical dimensions in millimeters:
            width_mm = round((max_x / dpi_y) * 25.4)
            height_mm = round((max_y / dpi_x) * 25.4)

            self.log(f"📱 Detected: {device_name}")
            self.log(f"   Resolution (Landscape): {max_x} x {max_y}")
            self.log(f"   DPI: {dpi_x:.1f} x {dpi_y:.1f}")
            self.log(f"   Physical Dimensions: {width_mm} mm x {height_mm} mm")

            self._build_and_save_otd_config(otd_dir, device_name, max_x, max_y, width_mm, height_mm)
        except Exception as e:
            self.log(f"❌ Error generating config: {e}")
            messagebox.showerror("Error", f"Failed to generate config:\n{e}")

    def _build_and_save_otd_config(self, otd_dir, device_name, max_x, max_y, width_mm, height_mm):
        # Build config dictionary
        config_data = {
            "Name": device_name,
            "Specifications": {
                "Digitizer": {
                    "Width": width_mm,
                    "Height": height_mm,
                    "MaxX": max_x,
                    "MaxY": max_y
                },
                "Pen": {
                    "MaxPressure": 4095,
                    "ButtonCount": 2
                },
                "AuxiliaryButtons": None,
                "MouseButtons": None,
                "Touch": None
            },
            "DigitizerIdentifiers": [
                {
                    "VendorID": 5824,
                    "ProductID": 1500,
                    "InputReportLength": 12,
                    "OutputReportLength": 0,
                    "ReportParser": "OpenTabletDriver.Configurations.Parsers.FlooGoo.FmaReportParser",
                    "FeatureInitReport": None,
                    "OutputInitReport": None,
                    "DeviceStrings": {},
                    "InitializationStrings": [],
                    "Attributes": {}
                }
            ],
            "AuxiliaryDeviceIdentifiers": [],
            "Attributes": {
                "libinputoverride": "1"
            }
        }

        # Save locally
        dest_local = os.path.join(APP_DIR, "AndroidTablet.json")
        with open(dest_local, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        # Save to chosen OTD folder
        target_dir = os.path.join(otd_dir, "Configurations")
        os.makedirs(target_dir, exist_ok=True)
        dest_file = os.path.join(target_dir, "AndroidTablet.json")
        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        console_exe = os.path.join(otd_dir, "OpenTabletDriver.Console.exe")
        if os.path.exists(console_exe):
            subprocess.run([console_exe, "detect"], capture_output=True, text=True, creationflags=0x08000000)

        self.log(f"✅ Generated and installed profile '{device_name}' into OTD!")
        self.lbl_otd_status.config(text=f"Installed ({device_name})", style="BadgeGreen.TLabel")

        messagebox.showinfo("Profile Generated",
                            f"OpenTabletDriver profile auto-generated successfully!\n\n"
                            f"Device: {device_name}\n"
                            f"Resolution: {max_x}x{max_y}\n"
                            f"Dimensions: {width_mm}x{height_mm} mm\n\n"
                            f"Saved to:\n{dest_file}")

    def manual_otd_config(self):
        dialog = tk.Toplevel(self)
        dialog.title("Manual Config")
        dialog.geometry("320x300")
        dialog.configure(bg="#1E1E24")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Device Name:", style="Status.TLabel").pack(anchor="w", padx=10, pady=(10, 0))
        ent_name = ttk.Entry(dialog)
        ent_name.insert(0, "My Android Tablet")
        ent_name.pack(fill="x", padx=10, pady=2)

        ttk.Label(dialog, text="Max X (Screen Width px):", style="Status.TLabel").pack(anchor="w", padx=10, pady=(10, 0))
        ent_x = ttk.Entry(dialog)
        ent_x.insert(0, "2400")
        ent_x.pack(fill="x", padx=10, pady=2)

        ttk.Label(dialog, text="Max Y (Screen Height px):", style="Status.TLabel").pack(anchor="w", padx=10, pady=(10, 0))
        ent_y = ttk.Entry(dialog)
        ent_y.insert(0, "1080")
        ent_y.pack(fill="x", padx=10, pady=2)

        ttk.Label(dialog, text="Screen DPI:", style="Status.TLabel").pack(anchor="w", padx=10, pady=(10, 0))
        ent_dpi = ttk.Entry(dialog)
        ent_dpi.insert(0, "400")
        ent_dpi.pack(fill="x", padx=10, pady=2)

        def on_save():
            try:
                device_name = ent_name.get().strip()
                max_x = int(ent_x.get().strip())
                max_y = int(ent_y.get().strip())
                dpi = float(ent_dpi.get().strip())
                
                width_mm = round((max_x / dpi) * 25.4)
                height_mm = round((max_y / dpi) * 25.4)

                from tkinter import filedialog
                otd_dir = filedialog.askdirectory(title="Select OpenTabletDriver Installation Folder", parent=dialog)
                if otd_dir:
                    dialog.destroy()
                    self._build_and_save_otd_config(otd_dir, device_name, max_x, max_y, width_mm, height_mm)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numeric values for X, Y, and DPI.", parent=dialog)

        btn_save = tk.Button(dialog, text="Save Config", command=on_save, bg="#10B981", fg="#000000", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2")
        btn_save.pack(fill="x", padx=10, pady=15)

    def sync_otd_config(self):
        src_json = os.path.join(APP_DIR, "AndroidTablet.json")
        if not os.path.exists(src_json):
            self.generate_otd_config()
            return
            
        from tkinter import filedialog
        otd_dir = filedialog.askdirectory(title="Select OpenTabletDriver Installation Folder")
        if not otd_dir:
            return

        target_dir = os.path.join(otd_dir, "Configurations")
        os.makedirs(target_dir, exist_ok=True)
        dest_file = os.path.join(target_dir, "AndroidTablet.json")
        shutil.copy2(src_json, dest_file)

        self.log(f"✅ OpenTabletDriver profile synced to {target_dir}.")
        self.lbl_otd_status.config(text="Profile Installed", style="BadgeGreen.TLabel")
        messagebox.showinfo("Success", f"OpenTabletDriver configuration saved to:\n{dest_file}")

    # ---------------- Connect / Disconnect ----------------
    def on_connect_clicked(self):
        if not self.adb_path and self.conn_mode.get() == "wired":
            messagebox.showwarning("ADB Missing", "Please install Platform Tools (ADB) first.")
            return
        if not self.usbip_path:
            messagebox.showwarning("USBip Missing", "Please install USBip first.")
            return

        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        self.log("\n🚀 Starting connection sequence...")

        # 1. Forward port if wired
        if self.conn_mode.get() == "wired":
            self.log("🔌 Forwarding port 3240 over ADB...")
            res = subprocess.run([self.adb_path, "forward", "tcp:3240", "tcp:3240"], capture_output=True, text=True, creationflags=0x08000000)
            if res.returncode != 0:
                self.log(f"❌ adb forward failed: {res.stderr.strip()}")
                messagebox.showerror("Connection Error", f"ADB port forward failed:\n{res.stderr}")
                return
            self.log("✅ Port 3240 forwarded successfully.")
            target_ip = "127.0.0.1"
        else:
            target_ip = self.entry_ip.get().strip()
            self.log(f"📡 Using wireless IP: {target_ip}")

        # 2. Attach via USBip
        self.log(f"🔗 Attaching to device at {target_ip} (bus 1-1)...")
        usbip_dir = os.path.dirname(self.usbip_path)
        res = subprocess.run([self.usbip_path, "attach", "-r", target_ip, "-b", "1-1"], capture_output=True, text=True, creationflags=0x08000000, cwd=usbip_dir)
        out = (res.stdout + "\n" + res.stderr).strip()

        if res.returncode == 0 or "attached" in out.lower():
            self.log("🎉 SUCCESS! Device connected via USBip!")
            self.log("OpenTabletDriver should now detect your device.")
            self.is_connected = True
            self.btn_connect.config(text="Reconnect device", bg="#FBBF24", fg="#000000")
        else:
            self.log(f"⚠️ USBip output: {out}")
            if "refused" in out.lower() or "timeout" in out.lower():
                self.log("💡 Tip: Make sure the server app is RUNNING and active on your phone screen!")
            messagebox.showwarning("Attachment Result", f"Result from USBip:\n{out}")




if __name__ == "__main__":
    app = OsuTabletCompanion()
    app.mainloop()
