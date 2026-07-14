# Telegram Media Saver Bot: Setup & Installation Guide

This guide provides full instructions on how to install system dependencies, configure cookies to bypass rate-limits/login walls, and deploy the Telegram bot as a 24/7 background service on Linux.

---

## 1. Install System Dependencies

### FFmpeg Installation
`yt-dlp` requires `ffmpeg` to merge high-quality video and audio streams seamlessly.

#### Debian / Ubuntu:
```bash
sudo apt update
sudo apt install -y ffmpeg
```

#### Fedora / Red Hat Enterprise Linux / CentOS:
```bash
sudo dnf install -y ffmpeg
```

---

## 2. Extracting `cookies.txt` for Instagram

Instagram aggressively rate-limits and blocks requests coming from datacenter or server IPs. Providing a valid session cookie file enables `yt-dlp` to successfully bypass security and login walls.

### How to extract cookies:
1. Install a browser extension such as **Get cookies.txt LOCALLY** (available for Chrome/Firefox) or any other reputable Netscape cookie exporter.
2. Log into your Instagram account in the browser.
3. Click the extension icon while on the Instagram website.
4. Export/download the cookies as a Netscape-formatted text file.
5. Save this file as `cookies.txt` in the root directory of the bot project.
6. The bot automatically checks for the presence of `cookies.txt` and attaches it to all `yt-dlp` download sessions.

---

## 3. Configuration & Local Execution

1. **Clone/Move project files** to your Linux directory.
2. Create and configure your `.env` environment file:
   ```bash
   echo "BOT_TOKEN=your_telegram_bot_token_here" > .env
   ```
3. Set up a Python Virtual Environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run the bot manually to verify:
   ```bash
   python3 main.py
   ```

---

## 4. Setup as a `systemd` Background Service

To ensure the bot runs 24/7, restarts automatically on crash or system reboot, and captures standard log outputs, configure it as a `systemd` service.

1. Create a service file using `sudo`:
   ```bash
   sudo nano /etc/systemd/system/media-saver-bot.service
   ```
2. Paste the following configuration, adjusting user, working directory, and paths:
   ```ini
   [Unit]
   Description=Telegram Media Saver Bot Service
   After=network.target

   [Service]
   Type=simple
   User=your_linux_username
   WorkingDirectory=/home/your_linux_username/telegram-media-saver
   ExecStart=/home/your_linux_username/telegram-media-saver/venv/bin/python3 main.py
   Restart=always
   RestartSec=5
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```
3. Reload systemd daemon to pick up the new service:
   ```bash
   sudo systemctl daemon-reload
   ```
4. Enable the service to start on boot:
   ```bash
   sudo systemctl enable media-saver-bot.service
   ```
5. Start the service:
   ```bash
   sudo systemctl start media-saver-bot.service
   ```
6. Check service status and logs:
   ```bash
   sudo systemctl status media-saver-bot.service
   journalctl -u media-saver-bot.service -f
   ```
