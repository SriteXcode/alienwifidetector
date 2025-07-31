import subprocess
import re
import csv
import time
import threading
from collections import defaultdict
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext
from plyer import notification
import pygame
import pystray
from pystray import MenuItem as item
from PIL import Image

# Initialize pygame for sound
pygame.mixer.init()

# Globals
log_history = []
already_alerted = set()

# ------------- WiFi Detection ------------- #
def get_wifi_networks():
    result = subprocess.check_output(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'], encoding='utf-8')
    networks = defaultdict(list)
    current_ssid = ""

    for line in result.splitlines():
        ssid_match = re.match(r"\s+SSID\s+\d+\s+:\s+(.*)", line)
        if ssid_match:
            current_ssid = ssid_match.group(1).strip()

        bssid_match = re.match(r"\s+BSSID\s+\d+\s+:\s+([0-9A-Fa-f:]+)", line)
        if bssid_match and current_ssid:
            mac = bssid_match.group(1).strip()
            networks[mac].append(current_ssid)

    return networks


def detect_clones():
    networks = get_wifi_networks()
    result_lines = []
    clones = []

    for mac, ssids in networks.items():
        unique_ssids = list(set(ssids))
        line = f"{mac} -> {', '.join(unique_ssids)}"
        result_lines.append(line)
        if len(unique_ssids) > 1:
            clones.append((mac, unique_ssids))

    return result_lines, clones


def send_notification(mac, ssids):
    notification.notify(
        title="\u26a0\ufe0f WiFi Spoofing Detected!",
        message=f"{mac} broadcasting multiple SSIDs:\n{', '.join(ssids)}",
        timeout=8
    )
    try:
        pygame.mixer.music.load("alert.wav")
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Error playing sound: {e}")


# ------------- GUI Setup ------------- #
root = Tk()
root.title("\ud83d\udd0d WiFi Clone Detector - Windows Edition")
root.geometry("850x600")
root.configure(bg="#0d0d0d")

style = ttk.Style()
style.theme_use("default")
style.configure("TNotebook", background="#0d0d0d", borderwidth=0)
style.configure("TNotebook.Tab", background="#222", foreground="white", padding=10)
style.map("TNotebook.Tab", background=[("selected", "#5c1a1a")])

notebook = ttk.Notebook(root)
notebook.pack(fill=BOTH, expand=1)

# === Tab 1 - Live Scanner === #
live_tab = Frame(notebook, bg="#0d0d0d")
notebook.add(live_tab, text="\ud83d\udce1 Live Scan")

Label(live_tab, text="WiFi Clone Detector", font=("Arial", 22, "bold"), fg="red", bg="#0d0d0d").pack(pady=10)
live_text = StringVar()
Label(live_tab, textvariable=live_text, font=("Arial", 12), fg="white", bg="#0d0d0d").pack()

text_area = Text(live_tab, height=20, width=100, bg="black", fg="white", font=("Courier", 10))
text_area.tag_config("alert", foreground="red")
text_area.pack(padx=10, pady=10)

Button(live_tab, text="\ud83d\udcc1 Export to CSV", command=lambda: export_to_csv(), bg="red", fg="white", font=("Arial", 12)).pack(pady=10)

# === Tab 2 - Spoof History === #
history_tab = Frame(notebook, bg="#0d0d0d")
notebook.add(history_tab, text="\ud83d\udcdc Spoof History")

Label(history_tab, text="Detected Spoofing History", font=("Arial", 16, "bold"), fg="white", bg="#0d0d0d").pack(pady=10)

history_list = Listbox(history_tab, width=100, height=20, bg="black", fg="white", font=("Courier", 10))
history_list.pack(padx=10, pady=10)

# === Tab 3 - WiFi Info === #
wifi_tab = Frame(notebook, bg="#0d0d0d")
notebook.add(wifi_tab, text="\ud83d\udcf6 WiFi Info")

wifi_listbox = Listbox(wifi_tab, width=100, height=20, bg="black", fg="white", font=("Courier", 10))
wifi_listbox.pack(side=LEFT, padx=(10, 0), pady=10, fill=BOTH, expand=True)

scrollbar = Scrollbar(wifi_tab, orient=VERTICAL, command=wifi_listbox.yview)
scrollbar.pack(side=LEFT, fill=Y, pady=10)
wifi_listbox.config(yscrollcommand=scrollbar.set)

try:
    refresh_icon = PhotoImage(file="alienwifidetector/refresh.png")
except:
    refresh_icon = None

Button(wifi_tab, image=refresh_icon, text="Refresh", compound=LEFT, command=lambda: list_wifi_networks()).pack(side=RIGHT, padx=10, pady=10)

# ------------- Background Threads ------------- #
def update_gui():
    while True:
        result_lines, clones = detect_clones()
        now = datetime.now().strftime('%H:%M:%S')
        live_text.set(f"Last Updated: {now}")
        text_area.delete(1.0, END)
        for line in result_lines:
            text_area.insert(END, line + '\n')

        if clones:
            text_area.insert(END, "\n--- \u26a0\ufe0f Suspicious Clones Detected! ---\n", "alert")
            for mac, ssids in clones:
                key = f"{mac}-{','.join(ssids)}"
                text_area.insert(END, f"[!] {mac} → {ssids}\n", "alert")
                if key not in already_alerted:
                    send_notification(mac, ssids)
                    already_alerted.add(key)
                    log_history.append((datetime.now().strftime('%Y-%m-%d %H:%M:%S'), mac, ssids))
                    refresh_history_tab()

        time.sleep(30)


def refresh_history_tab():
    history_list.delete(0, END)
    for timestamp, mac, ssids in log_history:
        history_list.insert(END, f"[{timestamp}] {mac} → {', '.join(ssids)}")


def export_to_csv():
    if not log_history:
        messagebox.showinfo("Export", "No spoofing detected to export.")
        return
    with open("wifi_clones.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "MAC Address", "SSIDs"])
        for row in log_history:
            writer.writerow(row)
    messagebox.showinfo("Export", "Exported to wifi_clones.csv")


def list_wifi_networks():
    wifi_listbox.delete(0, END)
    try:
        result = subprocess.check_output(["netsh", "wlan", "show", "network", "mode=Bssid"],
                                         shell=True, text=True, encoding='utf-8')
        for line in result.splitlines():
            if "SSID" in line or "Signal" in line:
                wifi_listbox.insert(END, line.strip())
    except Exception as e:
        wifi_listbox.insert(END, f"Error fetching WiFi: {e}")


threading.Thread(target=update_gui, daemon=True).start()
threading.Thread(target=lambda: auto_refresh_wifi(), daemon=True).start()



def auto_refresh_wifi():
    while True:
        list_wifi_networks()
        time.sleep(30)

# ------------- System Tray Integration ------------- #
def show_window(icon=None, item=None):
    root.after(0, root.deiconify)
    if icon:
        icon.stop()


def quit_app(icon=None, item=None):
    icon.stop()
    root.quit()


def minimize_to_tray():
    root.withdraw()
    image = Image.open("alienwifidetector/icon.png")
    menu = (item('Show', show_window), item('Exit', quit_app))
    icon = pystray.Icon("WiFi Clone Detector", image, "WiFi Clone Detector", menu)

    def setup(icon):
        icon.visible = True

    threading.Thread(target=lambda: icon.run(setup), daemon=True).start()


root.protocol("WM_DELETE_WINDOW", minimize_to_tray)
list_wifi_networks()
root.mainloop()
