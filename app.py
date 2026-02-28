import tkinter as tk
from tkinter import ttk, messagebox
import threading
import cv2
import time
import json
import os
from ultralytics import YOLO

# ── Config file path ─────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".lenspect_config.json")

# ── Globals ──────────────────────────────────────────────────────────
model = None
cap = None
running = False
zone = None
drawing = False
start_x, start_y = -1, -1
last_seen = time.time()
alert_active = False
ALERT_SECONDS = 10

# ── Save / Load config ────────────────────────────────────────────────
def save_config():
    data = {
        "ip": ip_entry.get().strip(),
        "username": user_entry.get().strip(),
        "channel": channel_var.get(),
        "quality": quality_var.get(),
        "alert_seconds": int(alert_var.get()),
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        ip_entry.insert(0, data.get("ip", ""))
        user_entry.insert(0, data.get("username", "admin"))
        channel_var.set(data.get("channel", "1"))
        quality_var.set(data.get("quality", "Main Stream (HD)"))
        alert_var.set(str(data.get("alert_seconds", 10)))
    except Exception:
        pass

# ── Load YOLO model ───────────────────────────────────────────────────
def load_model():
    global model
    set_status("⏳ Loading AI model...", "#F59E0B")
    model = YOLO("yolov8n.pt")
    set_status("✅ AI model ready — enter camera details and connect.", "#22C55E")

# ── UI helpers ────────────────────────────────────────────────────────
def set_status(msg, color="#94A3B8"):
    status_label.config(text=msg, fg=color)

def set_alert(msg, color="#94A3B8"):
    alert_label.config(text=msg, fg=color)

# ── Build RTSP URL ────────────────────────────────────────────────────
def build_rtsp_url():
    ip   = ip_entry.get().strip()
    user = user_entry.get().strip()
    pwd  = pass_entry.get().strip()
    ch   = channel_var.get()
    sub  = "0" if quality_var.get() == "Main Stream (HD)" else "1"
    if not ip:
        messagebox.showerror("Missing Info", "Please enter the camera IP address.")
        return None
    if not user:
        messagebox.showerror("Missing Info", "Please enter the username.")
        return None
    return f"rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel={ch}&subtype={sub}"

# ── Mouse zone drawing ────────────────────────────────────────────────
def on_mouse(event, x, y, flags, param):
    global zone, drawing, start_x, start_y, last_seen, alert_active
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_x, start_y = x, y
        zone = None
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        zone = (start_x, start_y, x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        zone = (start_x, start_y, x, y)
        last_seen = time.time()
        alert_active = False

# ── Detection loop ────────────────────────────────────────────────────
def detection_loop(rtsp_url):
    global cap, running, zone, last_seen, alert_active

    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        root.after(0, lambda: messagebox.showerror(
            "Connection Failed",
            "Could not connect to the camera.\n\n"
            "Please check:\n"
            "  • IP address is correct\n"
            "  • Username and password are correct\n"
            "  • Camera is on the same network\n"
            "  • Port 554 is not blocked"
        ))
        root.after(0, lambda: set_status("❌ Connection failed. Check details and retry.", "#EF4444"))
        root.after(0, lambda: connect_btn.config(state="normal", text="🔌  Connect Camera"))
        running = False
        return

    win = "Lenspect AI  |  Suryamitra POC  |  Draw zone with mouse  |  Q = quit"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 1280, 720)
    cv2.setMouseCallback(win, on_mouse)

    root.after(0, lambda: set_status("🟢 Live! Draw a station zone on the camera window.", "#22C55E"))
    root.after(0, lambda: connect_btn.config(text="⏹  Disconnect", state="normal"))

    alert_secs = int(alert_var.get()) if alert_var.get().isdigit() else ALERT_SECONDS

    while running:
        ret, frame = cap.read()
        if not ret:
            root.after(0, lambda: set_status("⚠️ Signal lost — reconnecting...", "#F59E0B"))
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue

        results = model(frame, verbose=False)
        annotated = results[0].plot()
        h, w = annotated.shape[:2]

        if zone:
            x1, y1, x2, y2 = zone
            zx1, zy1 = min(x1, x2), min(y1, y2)
            zx2, zy2 = max(x1, x2), max(y1, y2)
            person_in_zone = False

            for box in results[0].boxes:
                if int(box.cls[0]) != 0:
                    continue
                bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
                if zx1 < cx < zx2 and zy1 < cy < zy2:
                    person_in_zone = True
                    last_seen = time.time()
                    alert_active = False

            empty_dur = int(time.time() - last_seen)
            if empty_dur > alert_secs:
                alert_active = True

            # Draw zone
            color = (0, 255, 0) if not alert_active else (0, 0, 255)
            cv2.rectangle(annotated, (zx1, zy1), (zx2, zy2), color, 3)
            cv2.putText(annotated, "Monitored Station", (zx1, max(zy1 - 12, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

            if alert_active:
                # Red alert banner
                overlay = annotated.copy()
                cv2.rectangle(overlay, (0, 0), (w, 75), (0, 0, 180), -1)
                cv2.addWeighted(overlay, 0.65, annotated, 0.35, 0, annotated)
                cv2.putText(annotated, f"  ALERT: Station empty for {empty_dur}s!",
                            (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
                root.after(0, lambda d=empty_dur: set_alert(f"🚨  ALERT: Station empty for {d}s!", "#EF4444"))
            else:
                cv2.putText(annotated, "  Station Occupied",
                            (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                root.after(0, lambda: set_alert("✅  Station Occupied", "#22C55E"))
        else:
            cv2.putText(annotated, "  Click and drag to draw a monitoring zone",
                        (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 255), 2)
            root.after(0, lambda: set_alert("👆  Draw a zone on the camera window to start monitoring", "#F59E0B"))

        # Watermark
        cv2.putText(annotated, "LENSPECT AI  |  lenspect.ai",
                    (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)

        cv2.imshow(win, annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
            break

    running = False
    cap.release()
    cv2.destroyAllWindows()
    root.after(0, lambda: connect_btn.config(state="normal", text="🔌  Connect Camera"))
    root.after(0, lambda: set_status("⚪  Disconnected.", "#94A3B8"))
    root.after(0, lambda: set_alert("", "#94A3B8"))

# ── Connect / Disconnect ──────────────────────────────────────────────
def toggle_connect():
    global running
    if running:
        running = False
        return
    if model is None:
        messagebox.showwarning("Loading", "AI model is still loading. Please wait a moment.")
        return
    rtsp_url = build_rtsp_url()
    if not rtsp_url:
        return
    save_config()
    running = True
    connect_btn.config(state="disabled", text="⏳  Connecting...")
    set_status("⏳  Connecting to camera...", "#F59E0B")
    threading.Thread(target=detection_loop, args=(rtsp_url,), daemon=True).start()

# ══════════════════════════════════════════════════════════════════════
# UI Layout
# ══════════════════════════════════════════════════════════════════════
root = tk.Tk()
root.title("Lenspect AI — Camera Monitor")
root.geometry("540x640")
root.resizable(False, False)
root.configure(bg="#0F172A")

# ── Header ────────────────────────────────────────────────────────────
header = tk.Frame(root, bg="#0EA5E9", height=70)
header.pack(fill="x")
header.pack_propagate(False)

tk.Label(header, text="LENSPECT AI", font=("Arial Black", 22),
         bg="#0EA5E9", fg="white").pack(side="left", padx=20, pady=15)
tk.Label(header, text="Factory Presence Monitor",
         font=("Calibri", 11), bg="#0EA5E9", fg="#E0F2FE").pack(side="left", pady=22)

# ── Status bar ────────────────────────────────────────────────────────
status_frame = tk.Frame(root, bg="#1E293B", height=36)
status_frame.pack(fill="x")
status_frame.pack_propagate(False)
status_label = tk.Label(status_frame, text="⏳ Loading AI model...",
                         font=("Calibri", 10), bg="#1E293B", fg="#F59E0B")
status_label.pack(side="left", padx=15, pady=8)

# ── Main card ─────────────────────────────────────────────────────────
card = tk.Frame(root, bg="#1E293B", padx=24, pady=20)
card.pack(fill="both", expand=True, padx=16, pady=16)

def section_label(parent, text):
    tk.Label(parent, text=text, font=("Arial Black", 10),
             bg="#1E293B", fg="#0EA5E9").pack(anchor="w", pady=(12, 4))

def field_label(parent, text):
    tk.Label(parent, text=text, font=("Calibri", 10),
             bg="#1E293B", fg="#94A3B8").pack(anchor="w")

def make_entry(parent, show=None):
    e = tk.Entry(parent, font=("Calibri", 12), bg="#0F172A", fg="white",
                 insertbackground="white", relief="flat",
                 bd=0, highlightthickness=2,
                 highlightbackground="#334155", highlightcolor="#0EA5E9",
                 show=show)
    e.pack(fill="x", pady=(2, 8), ipady=7)
    return e

# Section: Camera Connection
section_label(card, "📷  Camera Connection")

field_label(card, "Camera IP Address")
ip_entry = make_entry(card)
ip_entry.insert(0, "192.168.1.")

field_label(card, "Username")
user_entry = make_entry(card)
user_entry.insert(0, "admin")

field_label(card, "Password")
pass_entry = make_entry(card, show="●")

# Channel + Quality row
row = tk.Frame(card, bg="#1E293B")
row.pack(fill="x", pady=(0, 8))

left = tk.Frame(row, bg="#1E293B")
left.pack(side="left", fill="x", expand=True, padx=(0, 10))
field_label(left, "Channel")
channel_var = tk.StringVar(value="1")
ch_menu = ttk.Combobox(left, textvariable=channel_var,
                        values=["1", "2", "3", "4", "5", "6", "7", "8"],
                        state="readonly", font=("Calibri", 11), width=8)
ch_menu.pack(anchor="w", ipady=4)

right = tk.Frame(row, bg="#1E293B")
right.pack(side="left", fill="x", expand=True)
field_label(right, "Stream Quality")
quality_var = tk.StringVar(value="Main Stream (HD)")
q_menu = ttk.Combobox(right, textvariable=quality_var,
                       values=["Main Stream (HD)", "Sub Stream (Low)"],
                       state="readonly", font=("Calibri", 11), width=20)
q_menu.pack(anchor="w", ipady=4)

# Section: Alert Settings
section_label(card, "⚙️  Alert Settings")
field_label(card, "Alert if station empty for (seconds)")
alert_var = tk.StringVar(value="10")
alert_entry = tk.Entry(card, textvariable=alert_var,
                        font=("Calibri", 12), bg="#0F172A", fg="white",
                        insertbackground="white", relief="flat",
                        bd=0, highlightthickness=2,
                        highlightbackground="#334155", highlightcolor="#0EA5E9",
                        width=8)
alert_entry.pack(anchor="w", pady=(2, 8), ipady=7)

# Section: Live Status
section_label(card, "📊  Live Status")
alert_label = tk.Label(card, text="Not connected",
                        font=("Calibri", 11), bg="#1E293B", fg="#94A3B8",
                        anchor="w", wraplength=460)
alert_label.pack(fill="x", pady=(0, 12))

# Connect button
connect_btn = tk.Button(card, text="🔌  Connect Camera",
                         font=("Arial Black", 13),
                         bg="#0EA5E9", fg="white",
                         activebackground="#0284C7", activeforeground="white",
                         relief="flat", bd=0, cursor="hand2", pady=12,
                         command=toggle_connect)
connect_btn.pack(fill="x", pady=(4, 0))

# ── Footer ────────────────────────────────────────────────────────────
footer = tk.Frame(root, bg="#0F172A", height=28)
footer.pack(fill="x", side="bottom")
tk.Label(footer, text="lenspect.ai  |  POC Build  |  Suryamitra Exim Pvt Ltd",
         font=("Calibri", 9), bg="#0F172A", fg="#334155").pack(pady=6)

# ── Style dropdowns ────────────────────────────────────────────────────
style = ttk.Style()
style.theme_use("clam")
style.configure("TCombobox",
                fieldbackground="#0F172A", background="#0F172A",
                foreground="white", selectbackground="#0EA5E9",
                bordercolor="#334155", lightcolor="#334155",
                darkcolor="#334155")

# ── Boot ──────────────────────────────────────────────────────────────
threading.Thread(target=load_model, daemon=True).start()
load_config()
root.mainloop()
