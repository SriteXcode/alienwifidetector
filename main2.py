import sys, os
import subprocess
import re
import csv
import time
import threading
from collections import defaultdict
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext, filedialog
from plyer import notification
import pygame
import pystray
from pystray import MenuItem as item
from PIL import Image
import pyperclip
if getattr(sys, 'frozen', False):
    os.environ['PYTHONUNBUFFERED'] = "1"
    sys.stderr = open("error_log.txt", "w")

# === Resource Path Fix (for PyInstaller) === #
def resource_path(relative_path):
    """ Get absolute path to resource (works for dev & PyInstaller exe) """
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Initialize pygame for sound
pygame.mixer.init()

# Globals
log_history = []
already_alerted = set()

class ToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None

    def showtip(self, text, x, y):
        self.hidetip()
        self.tipwindow = Toplevel(self.widget)
        self.tipwindow.wm_overrideredirect(True)
        self.tipwindow.wm_geometry(f"+{x+20}+{y+20}")
        label = Label(self.tipwindow, text=text, background="#222", foreground="white",
                      relief="solid", borderwidth=1, font=("Arial", 10))
        label.pack(ipadx=4, ipady=2)

    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

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
        pygame.mixer.music.load(resource_path("alienwifidetector/alert.wav"))
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

wifi_listbox = Listbox(wifi_tab, width=40, height=20, bg="black", fg="white", font=("Courier", 10))
wifi_listbox.pack(side=BOTTOM, padx=(10, 0), pady=10, fill=BOTH, expand=True)

try:
    refresh_icon = PhotoImage(file=resource_path("alienwifidetector/refresh.png"))
    refresh_icon = refresh_icon.subsample(
        max(refresh_icon.width() // 24, 1),
        max(refresh_icon.height() // 24, 1)
    )
except:
    refresh_icon = None

Button(wifi_tab, image=refresh_icon, text="Refresh", compound=LEFT, command=lambda: list_wifi_networks()).pack(side=TOP, padx=0, pady=10)

# === Tab 4 - Connected History === #
# (Your connected history tab code remains the same, but update icon/sound paths with resource_path where needed)

# === Tab 4 - Connected Network History === #
connected_tab = Frame(notebook, bg="#0d0d0d")
notebook.add(connected_tab, text="\U0001F4C2 Connected History")

Label(connected_tab, text="Connected Network History", font=("Arial", 16, "bold"), fg="white", bg="#0d0d0d").pack(pady=10)

# --- Search Bar ---
search_var = StringVar()
def filter_connected_list(*args):
    search = search_var.get().lower()
    connected_list.delete(0, END)
    for row in connected_history_data:
        display = f"SSID: {row[0]} | Status: {row[1]} | Blocked: {row[2]} | Password: {row[3]}"
        if search in row[0].lower():
            connected_list.insert(END, display)

search_var.trace("w", filter_connected_list)
Entry(connected_tab, textvariable=search_var, font=("Arial", 12), width=40).pack(pady=5)

connected_list = Listbox(connected_tab, width=100, height=20, bg="black", fg="white", font=("Courier", 10))
connected_list.pack(padx=10, pady=10)

tooltip = ToolTip(connected_list)

def on_motion(event):
    try:
        index = connected_list.nearest(event.y)
        if index >= 0 and index < len(connected_history_data):
            password = connected_history_data[index][3]
            x, y = event.x_root, event.y_root
            tooltip.showtip(f"Password: {password}", x, y)
    except:
        tooltip.hidetip()

def on_leave(event):
    tooltip.hidetip()

connected_list.bind("<Motion>", on_motion)
connected_list.bind("<Leave>", on_leave)

# --- Fetch blocked profiles ---
def get_blocked_profiles():
    try:
        filters_output = subprocess.check_output(['netsh', 'wlan', 'show', 'filters'], encoding='utf-8')
        blocked = re.findall(r"Network\s+type\s+:\s+Infrastructure\s+SSID\s+:\s+(.*)", filters_output)
        return [b.strip() for b in blocked]
    except Exception:
        return []

def get_connected_networks_history():
    blocked_profiles = get_blocked_profiles()
    try:
        profiles_output = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'], encoding='utf-8')
        profiles = re.findall(r"All User Profile\s*:\s*(.*)", profiles_output)
    except Exception as e:
        connected_list.delete(0, END)
        connected_list.insert(END, f"Error fetching profiles: {e}")
        return

    try:
        current_output = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces'], encoding='utf-8')
        current_ssid_match = re.search(r"^\s*SSID\s*:\s*(.+)$", current_output, re.MULTILINE)
        current_ssid = current_ssid_match.group(1).strip() if current_ssid_match else None
        current_state_match = re.search(r"^\s*State\s*:\s*(.+)$", current_output, re.MULTILINE)
        current_state = current_state_match.group(1).strip() if current_state_match else None
    except Exception:
        current_ssid = None
        current_state = None

    connected_list.delete(0, END)
    global connected_history_data
    connected_history_data = []

    for profile in profiles:
        profile = profile.strip()
        try:
            detail_output = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', f'name={profile}', 'key=clear'], encoding='utf-8', errors='ignore')
            password_match = re.search(r"Key Content\s*:\s*(.*)", detail_output)
            password = password_match.group(1).strip() if password_match else "(None)"
        except Exception:
            password = "(Error)"

        if current_ssid and profile == current_ssid:
            status = "Connected" if current_state and "connected" in current_state.lower() else "Disconnected"
        else:
            status = "Disconnected"

        blocked = "Blocked" if profile in blocked_profiles else "Allowed"
        connected_history_data.append([profile, status, blocked, password])

    # --- Insert with Colors ---
    for row in connected_history_data:
        display = f"SSID: {row[0]} | Status: {row[1]} | Blocked: {row[2]} | Password: {row[3]}"
        idx = connected_list.size()
        connected_list.insert(END, display)
        if row[1] == "Connected":
            connected_list.itemconfig(idx, {'fg': 'green'})
        elif row[2] == "Blocked":
            connected_list.itemconfig(idx, {'fg': 'red'})
        else:
            connected_list.itemconfig(idx, {'fg': 'white'})

def export_connected_to_csv():
    if not connected_history_data:
        messagebox.showinfo("Export", "No connected networks to export.")
        return
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")],
        title="Save Connected Networks As"
    )
    if not file_path:
        return
    try:
        with open(file_path, "w", newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["SSID", "Status", "Blocked", "Password"])
            for row in connected_history_data:
                writer.writerow(row)
        messagebox.showinfo("Export", f"Exported successfully to:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export: {e}")

# --- Right-Click Context Menu ---
context_menu = Menu(connected_tab, tearoff=0)
def on_right_click(event):
    try:
        index = connected_list.curselection()[0]
        selected_item = connected_history_data[index][0]
        context_menu.delete(0, END)
        context_menu.add_command(label="Disconnect", command=lambda: disconnect_wifi(selected_item))
        context_menu.add_command(label="Delete", command=lambda: delete_profile(selected_item))
        context_menu.post(event.x_root, event.y_root)
    except:
        pass

connected_list.bind("<Button-3>", on_right_click)

def disconnect_wifi(ssid):
    if messagebox.askyesno("Confirm", f"Disconnect from '{ssid}'?"):
        try:
            subprocess.run(['netsh', 'wlan', 'disconnect'], check=True)
            messagebox.showinfo("Disconnect", f"Disconnected from {ssid}.")
            get_connected_networks_history()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disconnect: {e}")

def delete_profile(ssid):
    if messagebox.askyesno("Confirm", f"Delete Wi-Fi profile '{ssid}'?"):
        try:
            subprocess.run(['netsh', 'wlan', 'delete', 'profile', f'name={ssid}'], check=True)
            messagebox.showinfo("Delete", f"Deleted profile {ssid}.")
            get_connected_networks_history()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

# --- Double-Click to Copy Password ---
def copy_password(event):
    try:
        index = connected_list.curselection()[0]
        password = connected_history_data[index][3]
        pyperclip.copy(password)
        messagebox.showinfo("Copied", f"Password copied to clipboard:\n{password}")
    except:
        pass

connected_list.bind("<Double-1>", copy_password)

# Buttons
btn_frame = Frame(connected_tab, bg="#0d0d0d")
btn_frame.pack(pady=10)
Button(btn_frame, text="Refresh", command=get_connected_networks_history, bg="red", fg="white", font=("Arial", 12)).pack(side=LEFT, padx=5)
Button(btn_frame, text="Export CSV", command=export_connected_to_csv, bg="green", fg="white", font=("Arial", 12)).pack(side=LEFT, padx=5)

get_connected_networks_history()

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
    with open("wifi_clones.csv", "w", newline='', encoding="utf-8") as file:
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

def auto_refresh_wifi():
    while True:
        prev_networks = getattr(auto_refresh_wifi, "prev_networks", set())
        list_wifi_networks()
        try:
            result = subprocess.check_output(["netsh", "wlan", "show", "network", "mode=Bssid"],
                             shell=True, text=True, encoding='utf-8')
            current_macs = set()
            for line in result.splitlines():
                bssid_match = re.match(r"\s*BSSID\s+\d+\s+:\s+([0-9A-Fa-f:]+)", line)
                if bssid_match:
                    current_macs.add(bssid_match.group(1).strip())
            new_devices = current_macs - prev_networks
            if new_devices:
                try:
                    pygame.mixer.music.load(resource_path("alienwifidetector/alert.wav"))  # <-- updated
                    pygame.mixer.music.play()
                except Exception as e:
                    print(f"Error playing sound: {e}")
            auto_refresh_wifi.prev_networks = current_macs
        except Exception:
            pass
        time.sleep(30)

threading.Thread(target=update_gui, daemon=True).start()
threading.Thread(target=lambda: auto_refresh_wifi(), daemon=True).start()

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
    image = Image.open(resource_path("alienwifidetector/icon.png"))  # <-- updated
    menu = (item('Show', show_window), item('Exit', quit_app))
    icon = pystray.Icon("WiFi Clone Detector", image, "WiFi Clone Detector", menu)
    def on_clicked(show, menu):
        show_window(menu)
    icon.on_click = on_clicked
    def setup(icon):
        icon.visible = True
    threading.Thread(target=lambda: icon.run(setup), daemon=True).start()

root.protocol("WM_DELETE_WINDOW", minimize_to_tray)
list_wifi_networks()
root.mainloop()
