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
import customtkinter as ctk
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('green')
import customtkinter as ctk
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('green')
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


class OsuTabletCompanion(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("tabletizer!")
        self.geometry("980x750")
        self.minsize(850, 650)
        self.configure(bg="#121214")

        # Set application icon
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "icon.ico")
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.adb_path = None
        self.usbip_path = None
        self.is_connected = False

        
        self.build_ui()

        # Initial check in background
        self.after(300, self.refresh_environment)

    def build_ui(self):
        if not is_admin():
            banner = ctk.CTkFrame(self, fg_color="#DC2626", corner_radius=0, height=35)
            banner.pack(fill="x")
            lbl = ctk.CTkLabel(banner, text="Administrator rights are required for USBip driver binding! (maybe)",
                               text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
            lbl.pack(side="left", padx=10, pady=5)
            btn = ctk.CTkButton(banner, text="Restart as Admin", command=run_as_admin,
                                fg_color="#FFFFFF", text_color="#DC2626", hover_color="#F3F4F6", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), width=120)
            btn.pack(side="right", padx=10, pady=5)

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=25, pady=25)

        top_bar = ctk.CTkFrame(main_container, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(top_bar, text="tabletizer!", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                     text_color="#4ADE80").pack(side="left")
        ctk.CTkButton(top_bar, text="Refresh Tools", command=self.refresh_environment,
                      fg_color="#222222", text_color="#FFFFFF", hover_color="#333333", 
                      font=ctk.CTkFont(family="Segoe UI", size=12), width=120).pack(side="right")

        dep_card = ctk.CTkFrame(main_container, fg_color="#1A1A1D", corner_radius=12)
        dep_card.pack(fill="x", pady=8, ipady=10, ipadx=10)

        ctk.CTkLabel(dep_card, text="Requirements & Tools", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#FFFFFF").grid(row=0, column=0, columnspan=3, sticky="w", pady=(10, 15), padx=15)

        font_status = ctk.CTkFont(family="Segoe UI", size=13)
        font_badge = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        font_btn = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")

        ctk.CTkLabel(dep_card, text="Android Platform Tools (ADB):", font=font_status, text_color="#AAAAAA").grid(row=1, column=0, sticky="w", pady=8, padx=15)
        self.lbl_adb_status = ctk.CTkLabel(dep_card, text="Checking...", font=font_badge, text_color="#FBBF24")
        self.lbl_adb_status.grid(row=1, column=1, sticky="w", padx=15)
        self.btn_dl_adb = ctk.CTkButton(dep_card, text="Download ADB", command=self.start_download_adb,
                                        fg_color="#444444", text_color="#FFFFFF", hover_color="#555555", font=font_btn, width=120)
        self.btn_dl_adb.grid(row=1, column=2, sticky="e", padx=15)
        
        ctk.CTkLabel(dep_card, text="USBip Driver & Client:", font=font_status, text_color="#AAAAAA").grid(row=2, column=0, sticky="w", pady=8, padx=15)
        self.lbl_usbip_status = ctk.CTkLabel(dep_card, text="Checking...", font=font_badge, text_color="#FBBF24")
        self.lbl_usbip_status.grid(row=2, column=1, sticky="w", padx=15)
        self.btn_dl_usbip = ctk.CTkButton(dep_card, text="Get USBip", command=self.start_download_usbip,
                                          fg_color="#444444", text_color="#FFFFFF", hover_color="#555555", font=font_btn, width=120)
        self.btn_dl_usbip.grid(row=2, column=2, sticky="e", padx=15)

        ctk.CTkLabel(dep_card, text="OpenTabletDriver Profile:", font=font_status, text_color="#AAAAAA").grid(row=3, column=0, sticky="w", pady=8, padx=15)
        self.lbl_otd_status = ctk.CTkLabel(dep_card, text="Checking...", font=font_badge, text_color="#FBBF24")
        self.lbl_otd_status.grid(row=3, column=1, sticky="w", padx=15)

        otd_btn_frame = ctk.CTkFrame(dep_card, fg_color="transparent")
        otd_btn_frame.grid(row=3, column=2, sticky="e", padx=15)
        self.btn_gen_otd = ctk.CTkButton(otd_btn_frame, text="Auto-Generate Profile", command=self.generate_otd_config,
                                         fg_color="#4ADE80", text_color="#000000", hover_color="#22C55E", font=font_btn, width=150)
        self.btn_gen_otd.pack(side="left", padx=(0, 10))
        self.btn_manual_otd = ctk.CTkButton(otd_btn_frame, text="Manual Config", command=self.manual_otd_config,
                                            fg_color="#444444", text_color="#FFFFFF", hover_color="#555555", font=font_btn, width=120)
        self.btn_manual_otd.pack(side="left", padx=(0, 10))
        self.btn_sync_otd = ctk.CTkButton(otd_btn_frame, text="Sync Existing", command=self.sync_otd_config,
                                          fg_color="#222222", text_color="#AAAAAA", hover_color="#333333", font=ctk.CTkFont(family="Segoe UI", size=12), width=100)
        self.btn_sync_otd.pack(side="left")

        dep_card.columnconfigure(0, weight=0, minsize=200)
        dep_card.columnconfigure(1, weight=1)
        dep_card.columnconfigure(2, weight=0)

        ctrl_card = ctk.CTkFrame(main_container, fg_color="#1A1A1D", corner_radius=12)
        ctrl_card.pack(fill="x", pady=10, ipady=10, ipadx=10)

        ctk.CTkLabel(ctrl_card, text="Connection Panel", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#FFFFFF").pack(anchor="w", pady=(10, 10), padx=15)

        device_frame = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        device_frame.pack(fill="x", pady=6, padx=15)
        ctk.CTkLabel(device_frame, text="Connected Android Device:", font=font_status, text_color="#AAAAAA").pack(side="left")
        self.lbl_device_info = ctk.CTkLabel(device_frame, text="Scanning...", font=font_badge, text_color="#FBBF24")
        self.lbl_device_info.pack(side="left", padx=15)

        mode_frame = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        mode_frame.pack(fill="x", pady=10, padx=15)
        ctk.CTkLabel(mode_frame, text="Connection Mode:", font=font_status, text_color="#AAAAAA").pack(side="left", padx=(0, 15))

        self.conn_mode = ctk.StringVar(value="wired")
        def mode_callback(value):
            if value == "Wired USB":
                self.conn_mode.set("wired")
                self.entry_ip.configure(state="disabled")
            else:
                self.conn_mode.set("wireless")
                self.entry_ip.configure(state="normal")
                
        self.seg_button = ctk.CTkSegmentedButton(mode_frame, values=["Wired USB", "Wireless IP"], command=mode_callback,
                                                 selected_color="#4ADE80", selected_hover_color="#22C55E", unselected_color="#444444", unselected_hover_color="#555555", text_color="#FFFFFF")
        self.seg_button.set("Wired USB")
        self.seg_button.pack(side="left")

        self.entry_ip = ctk.CTkEntry(mode_frame, width=150, placeholder_text="192.168.1.100", font=font_status, border_color="#333333", border_width=1)
        self.entry_ip.insert(0, "192.168.1.100")
        self.entry_ip.pack(side="left", padx=20)
        self.entry_ip.configure(state="disabled")

        self.btn_connect = ctk.CTkButton(ctrl_card, text="Connect device", command=self.on_connect_clicked,
                                         fg_color="#4ADE80", text_color="#000000", hover_color="#22C55E", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), height=50)
        self.btn_connect.pack(fill="x", pady=(15, 5), padx=15)

        log_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, pady=(15, 0))
        ctk.CTkLabel(log_frame, text="Activity Log", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#AAAAAA").pack(anchor="w")

        self.log_text = ctk.CTkTextbox(log_frame, fg_color="#18181B", text_color="#AAAAAA", font=ctk.CTkFont(family="Consolas", size=12), corner_radius=8, border_width=0)
        self.log_text.pack(fill="both", expand=True, pady=8)

    def log(self, text):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def update_mode_ui(self):
        if self.conn_mode.get() == "wireless":
            self.entry_ip.configure(state="normal")
        else:
            self.entry_ip.configure(state="disabled")

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
            self.lbl_adb_status.configure(text="Installed (System)", text_color="#4ADE80")
            self.btn_dl_adb.configure(state="disabled")
        elif os.path.exists(local_adb):
            self.adb_path = local_adb
            self.lbl_adb_status.configure(text="Installed (Local)", text_color="#4ADE80")
            self.btn_dl_adb.configure(state="disabled")
        else:
            self.adb_path = None
            self.lbl_adb_status.configure(text="Missing", text_color="#EF4444")
            self.btn_dl_adb.configure(state="normal")

        # 2. Check USBip
        path, status = find_installed_usbip(BIN_DIR)
        self.usbip_path = path
        if path:
            self.lbl_usbip_status.configure(text=status, text_color="#4ADE80")
            self.btn_dl_usbip.configure(state="disabled")
        else:
            self.lbl_usbip_status.configure(text="Missing", text_color="#EF4444")
            self.btn_dl_usbip.configure(state="normal")

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
            self.lbl_otd_status.configure(text=f"Installed ({installed_name})", text_color="#4ADE80")
        else:
            self.lbl_otd_status.configure(text="Not Configured", text_color="#FBBF24")

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
                self.btn_connect.configure(text="Disconnect device", fg_color="#EF4444", hover_color="#DC2626", text_color="#FFFFFF")
                self.log("Detected active USBip connection.")
            else:
                self.is_connected = False
                self.btn_connect.configure(text="Connect device", fg_color="#4ADE80", hover_color="#22C55E", text_color="#000000")
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
            self.lbl_device_info.configure(text="ADB not available", text_color="#F87171")
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

                self.lbl_device_info.configure(text=f"{model_text} ({dev_id})", text_color="#4ADE80")
                self.log(f"Detected phone: {model_text} [{dev_id}]")
            else:
                self.lbl_device_info.configure(text="No device found (Connect USB cable)", text_color="#FBBF24")
        except Exception:
            self.lbl_device_info.configure(text="ADB check error", text_color="#F87171")

    # ---------------- Downloader Methods ----------------
    def start_download_adb(self):
        threading.Thread(target=self._download_adb_thread, daemon=True).start()

    def _download_adb_thread(self):
        try:
            self.log("Downloading Google Android Platform-Tools (ADB)...")
            os.makedirs(BIN_DIR, exist_ok=True)
            zip_dest = os.path.join(BIN_DIR, "platform-tools.zip")

            urllib.request.urlretrieve(PLATFORM_TOOLS_URL, zip_dest)
            self.log("Extracting platform-tools...")
            with zipfile.ZipFile(zip_dest, "r") as z:
                z.extractall(BIN_DIR)
            os.remove(zip_dest)

            self.log("Platform Tools successfully installed!")
            self.refresh_environment()
        except Exception as e:
            self.log(f"Failed to download ADB: {e}")
            messagebox.showerror("Download Error", f"Could not download ADB:\n{e}")

    def start_download_usbip(self):
        self.log("Opening USBip releases page in your browser...")
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
        self.log("\nAuto-detecting device specifications for OpenTabletDriver...")
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

            # Calculate the largest 16:9 box that fits inside the physical screen
            target_ratio = 16 / 9
            screen_ratio = max_x / max_y
            
            if screen_ratio > target_ratio:
                area_y = max_y
                area_x = int(max_y * target_ratio)
            else:
                area_x = max_x
                area_y = int(max_x / target_ratio)

            # Calculate physical dimensions in millimeters for the 16:9 area:
            width_mm = round((area_x / dpi_y) * 25.4)
            height_mm = round((area_y / dpi_x) * 25.4)

            self.log(f"Detected: {device_name}")
            self.log(f"   Physical Screen: {max_x} x {max_y}")
            self.log(f"   16:9 Tablet Area: {area_x} x {area_y}")
            self.log(f"   DPI: {dpi_x:.1f} x {dpi_y:.1f}")
            self.log(f"   Physical Dimensions: {width_mm} mm x {height_mm} mm")

            self._build_and_save_otd_config(otd_dir, device_name, area_x, area_y, width_mm, height_mm)
        except Exception as e:
            self.log(f"Error generating config: {e}")
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

        self.log(f"Generated and installed profile '{device_name}' into OTD!")
        self.lbl_otd_status.configure(text=f"Installed ({device_name})", text_color="#4ADE80")

        messagebox.showinfo("Profile Generated",
                            f"OpenTabletDriver profile auto-generated successfully!\n\n"
                            f"Device: {device_name}\n"
                            f"Resolution: {max_x}x{max_y}\n"
                            f"Dimensions: {width_mm}x{height_mm} mm\n\n"
                            f"Saved to:\n{dest_file}")


    def manual_otd_config(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Manual Config")
        dialog.geometry("380x420")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        font_lbl = ctk.CTkFont(family="Segoe UI", size=12)
        font_ent = ctk.CTkFont(family="Segoe UI", size=13)

        ctk.CTkLabel(dialog, text="Device Name:", font=font_lbl, text_color="#AAAAAA").pack(anchor="w", padx=20, pady=(20, 0))
        ent_name = ctk.CTkEntry(dialog, font=font_ent)
        ent_name.insert(0, "My Android Tablet")
        ent_name.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(dialog, text="Max X (Screen Width px):", font=font_lbl, text_color="#AAAAAA").pack(anchor="w", padx=20, pady=(10, 0))
        ent_x = ctk.CTkEntry(dialog, font=font_ent)
        ent_x.insert(0, "2400")
        ent_x.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(dialog, text="Max Y (Screen Height px):", font=font_lbl, text_color="#AAAAAA").pack(anchor="w", padx=20, pady=(10, 0))
        ent_y = ctk.CTkEntry(dialog, font=font_ent)
        ent_y.insert(0, "1080")
        ent_y.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(dialog, text="Screen DPI:", font=font_lbl, text_color="#AAAAAA").pack(anchor="w", padx=20, pady=(10, 0))
        ent_dpi = ctk.CTkEntry(dialog, font=font_ent)
        ent_dpi.insert(0, "400")
        ent_dpi.pack(fill="x", padx=20, pady=5)

        def on_save():
            try:
                device_name = ent_name.get().strip()
                max_x = int(ent_x.get().strip())
                max_y = int(ent_y.get().strip())
                dpi = float(ent_dpi.get().strip())
                
                target_ratio = 16 / 9
                screen_ratio = max_x / max_y
                if screen_ratio > target_ratio:
                    area_y = max_y
                    area_x = int(max_y * target_ratio)
                else:
                    area_x = max_x
                    area_y = int(max_x / target_ratio)
                
                width_mm = round((area_x / dpi) * 25.4)
                height_mm = round((area_y / dpi) * 25.4)

                from tkinter import filedialog
                otd_dir = filedialog.askdirectory(title="Select OpenTabletDriver Installation Folder", parent=dialog)
                if otd_dir:
                    dialog.destroy()
                    self._build_and_save_otd_config(otd_dir, device_name, area_x, area_y, width_mm, height_mm)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numeric values for X, Y, and DPI.", parent=dialog)

        btn_save = ctk.CTkButton(dialog, text="Save Config", command=on_save, fg_color="#4ADE80", text_color="#000000", hover_color="#22C55E", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), height=40)
        btn_save.pack(fill="x", padx=20, pady=25)

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

        self.log(f"OpenTabletDriver profile synced to {target_dir}.")
        self.lbl_otd_status.configure(text="Profile Installed", text_color="#4ADE80")
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
        self.log("\nStarting connection sequence...")

        # 1. Forward port if wired
        if self.conn_mode.get() == "wired":
            self.log("Forwarding port 3240 over ADB...")
            res = subprocess.run([self.adb_path, "forward", "tcp:3240", "tcp:3240"], capture_output=True, text=True, creationflags=0x08000000)
            if res.returncode != 0:
                self.log(f"adb forward failed: {res.stderr.strip()}")
                messagebox.showerror("Connection Error", f"ADB port forward failed:\n{res.stderr}")
                return
            self.log("Port 3240 forwarded successfully.")
            target_ip = "127.0.0.1"
        else:
            target_ip = self.entry_ip.get().strip()
            self.log(f"Using wireless IP: {target_ip}")

        # 2. Attach via USBip
        self.log(f"Attaching to device at {target_ip} (bus 1-1)...")
        usbip_dir = os.path.dirname(self.usbip_path)
        res = subprocess.run([self.usbip_path, "attach", "-r", target_ip, "-b", "1-1"], capture_output=True, text=True, creationflags=0x08000000, cwd=usbip_dir)
        out = (res.stdout + "\n" + res.stderr).strip()

        if res.returncode == 0 or "attached" in out.lower():
            self.log("SUCCESS! Device connected via USBip!")
            self.log("OpenTabletDriver should now detect your device.")
            self.is_connected = True
            self.btn_connect.configure(text="Reconnect device", fg_color="#FBBF24", hover_color="#F59E0B", text_color="#000000")
        else:
            self.log(f"USBip output: {out}")
            if "refused" in out.lower() or "timeout" in out.lower():
                self.log("Tip: Make sure the server app is RUNNING and active on your phone screen!")
            messagebox.showwarning("Attachment Result", f"Result from USBip:\n{out}")




if __name__ == "__main__":
    app = OsuTabletCompanion()
    app.mainloop()
