import tkinter as tk
import threading
import subprocess
import requests
import time
import os
import sys

class VPNApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VPN - Los Angeles")
        self.root.geometry("420x560")
        self.root.configure(bg="#080810")
        self.root.resizable(False, False)
        self.connected = False
        self.vpn_process = None
        self.kill_switch_active = False
        self.setup_ui()
        self.fetch_ip()

    def setup_ui(self):
        tk.Label(self.root, text="SECUREVPN",
                 font=("Courier New", 14, "bold"),
                 fg="#00ffaa", bg="#080810").pack(pady=(35, 2))

        tk.Label(self.root, text="Los Angeles  -  United States",
                 font=("Courier New", 9),
                 fg="#2a2a44", bg="#080810").pack()

        self.canvas = tk.Canvas(self.root, width=240, height=240,
                                bg="#080810", highlightthickness=0)
        self.canvas.pack(pady=25)
        self.canvas.bind("<Button-1>", self.toggle_vpn)
        self.draw_button(False)

        self.status_var = tk.StringVar(value="DISCONNECTED")
        self.status_label = tk.Label(self.root,
                                     textvariable=self.status_var,
                                     font=("Courier New", 12, "bold"),
                                     fg="#ff3355", bg="#080810")
        self.status_label.pack(pady=(0, 8))

        self.ip_var = tk.StringVar(value="Fetching IP...")
        tk.Label(self.root, textvariable=self.ip_var,
                 font=("Courier New", 9),
                 fg="#333355", bg="#080810").pack()

        self.ks_label = tk.Label(self.root,
                                  text="KILL SWITCH ACTIVE - ALL TRAFFIC BLOCKED",
                                  font=("Courier New", 8, "bold"),
                                  fg="#ff8800", bg="#080810")

        tk.Label(self.root, text="click button to connect",
                 font=("Courier New", 8),
                 fg="#1a1a2e", bg="#080810").pack(side="bottom", pady=15)

    def draw_button(self, connected):
        self.canvas.delete("all")
        cx, cy, r = 120, 120, 85
        color = "#00ffaa" if connected else "#ff3355"
        dark = "#003322" if connected else "#220011"

        for i in range(5, 0, -1):
            self.canvas.create_oval(
                cx - r - i*6, cy - r - i*6,
                cx + r + i*6, cy + r + i*6,
                outline=dark, width=1)

        self.canvas.create_oval(
            cx - r - 6, cy - r - 6,
            cx + r + 6, cy + r + 6,
            outline=color, width=1, dash=(4, 6))

        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill="#0c0c1a", outline=color, width=3)

        self.canvas.create_oval(
            cx - r + 16, cy - r + 16,
            cx + r - 16, cy + r - 16,
            fill=dark, outline=dark, width=1)

        arc_r = 30
        self.canvas.create_arc(
            cx - arc_r, cy - arc_r,
            cx + arc_r, cy + arc_r,
            start=50, extent=260,
            outline=color, width=3, style="arc")

        self.canvas.create_line(
            cx, cy - arc_r - 2, cx, cy - 10,
            fill=color, width=3, capstyle="round")

        self.canvas.bind("<Enter>",
            lambda e: self.canvas.configure(cursor="hand2"))
        self.canvas.bind("<Leave>",
            lambda e: self.canvas.configure(cursor=""))

    def toggle_vpn(self, event=None):
        if not self.connected:
            self.connect_vpn()
        else:
            self.disconnect_vpn()

    def connect_vpn(self):
        self.status_var.set("CONNECTING...")
        self.status_label.config(fg="#ffaa00")
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        ovpn_files = [f for f in os.listdir(folder) if f.endswith('.ovpn')]

        if not ovpn_files:
            self.root.after(0, lambda: self.status_var.set("NO .OVPN FILE FOUND"))
            self.root.after(0, lambda: self.status_label.config(fg="#ff3355"))
            self.root.after(0, lambda: self.ip_var.set(
                "Put a .ovpn file in the vpn-app folder"))
            return

        config_path = os.path.join(folder, ovpn_files[0])

        try:
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.CREATE_NO_WINDOW

            self.vpn_process = subprocess.Popen(
                [r"C:\Program Files\OpenVPN\bin\openvpn.exe",
                 "--config", config_path,
                 "--auth-user-pass", os.path.join(folder, "pass.txt")],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=flags)

            for line in iter(self.vpn_process.stdout.readline, b''):
                text = line.decode('utf-8', errors='ignore')
                if "Initialization Sequence Completed" in text:
                    self.connected = True
                    self.root.after(0, self._on_connected)
                    self._start_monitor()
                    return
                if "AUTH_FAILED" in text or "auth-failure" in text:
                    break

            self.root.after(0, lambda: self.status_var.set("CONNECTION FAILED"))
            self.root.after(0, lambda: self.status_label.config(fg="#ff3355"))

        except FileNotFoundError:
            self.root.after(0, lambda: self.status_var.set("OPENVPN NOT FOUND"))
            self.root.after(0, lambda: self.ip_var.set(
                "Install OpenVPN from openvpn.net"))
            self.root.after(0, lambda: self.status_label.config(fg="#ff3355"))

    def _on_connected(self):
        self.draw_button(True)
        self.status_var.set("CONNECTED")
        self.status_label.config(fg="#00ffaa")
        self.fetch_ip()

    def disconnect_vpn(self):
        self.connected = False
        self.remove_kill_switch()
        if self.vpn_process:
            self.vpn_process.terminate()
            self.vpn_process = None
        self.ks_label.pack_forget()
        self.draw_button(False)
        self.status_var.set("DISCONNECTED")
        self.status_label.config(fg="#ff3355")
        self.fetch_ip()

    def _start_monitor(self):
        def monitor():
            while self.connected:
                time.sleep(4)
                if self.vpn_process and self.vpn_process.poll() is not None:
                    self.connected = False
                    self.root.after(0, self._on_vpn_dropped)
                    break
        threading.Thread(target=monitor, daemon=True).start()

    def _on_vpn_dropped(self):
        self.activate_kill_switch()
        self.draw_button(False)
        self.status_var.set("CONNECTION LOST")
        self.status_label.config(fg="#ff3355")
        self.ks_label.pack(pady=(10, 0))
        self.fetch_ip()

    def activate_kill_switch(self):
        self.kill_switch_active = True
        if sys.platform == "win32":
            subprocess.run(
                ["netsh", "advfirewall", "set", "allprofiles",
                 "firewallpolicy", "blockinbound,blockoutbound"],
                capture_output=True)

    def remove_kill_switch(self):
        if self.kill_switch_active:
            self.kill_switch_active = False
            if sys.platform == "win32":
                subprocess.run(
                    ["netsh", "advfirewall", "set", "allprofiles",
                     "firewallpolicy", "blockinbound,allowoutbound"],
                    capture_output=True)

    def fetch_ip(self):
        def _fetch():
            try:
                data = requests.get(
                    "https://ipinfo.io/json", timeout=5).json()
                ip = data.get("ip", "Unknown")
                city = data.get("city", "")
                country = data.get("country", "")
                self.root.after(0, lambda: self.ip_var.set(
                    ip + "  -  " + city + ", " + country))
            except Exception:
                self.root.after(0, lambda: self.ip_var.set(
                    "Could not fetch IP"))
        threading.Thread(target=_fetch, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = VPNApp(root)
    root.mainloop()