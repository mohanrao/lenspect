# Lenspect AI — Factory Presence Monitor

AI-powered CCTV monitoring for manufacturing facilities.  
Detects operator absence from monitored stations and triggers real-time alerts.

---

## 🚀 Quick Start (Windows)

1. Download `LenspectAI.exe` from the [latest release](../../releases/latest)
2. Double-click to run — no installation needed
3. Enter your Dahua camera IP, username, and password
4. Click **Connect Camera**
5. Draw a zone on the live feed with your mouse
6. Get alerted when the station is empty

---

## 🛠 Development Setup (Mac/Linux)

```bash
git clone https://github.com/YOUR_USERNAME/lenspect.git
cd lenspect
pip install -r requirements.txt
python app.py
```

---

## 📦 Building the Windows EXE

The `.exe` is built automatically via GitHub Actions every time you push to `main`.

To download the latest build:
1. Go to **Actions** tab on GitHub
2. Click the latest workflow run
3. Download **LenspectAI-Windows** artifact

To create a release with the `.exe` attached:
```bash
git tag v0.1.0
git push origin v0.1.0
```

---

## 📷 Camera Compatibility

Tested with **Dahua IP cameras** via RTSP.  
Default RTSP URL format:
```
rtsp://admin:PASSWORD@192.168.X.X:554/cam/realmonitor?channel=1&subtype=0
```

---

## 🗺 Roadmap

- [x] Live RTSP camera feed
- [x] Mouse-drawn monitoring zones
- [x] Presence detection with YOLOv8
- [x] Absence alerts with configurable threshold
- [x] Connection settings saved locally
- [ ] Multi-camera support
- [ ] Alert logging with timestamps
- [ ] Email / WhatsApp alert notifications
- [ ] Web dashboard

---

## 🏭 Current Pilot

**Suryamitra Exim Pvt Ltd** — Bhimavaram, Andhra Pradesh  
Shrimp processing & export facility

---

Built with ❤️ by Mohan | [lenspect.ai](https://lenspect.ai)
