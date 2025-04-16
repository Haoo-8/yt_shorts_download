# youtube_shorts_downloader.py
# -*- coding: utf-8 -*-

import sys
import os
import threading
import time
import json
from queue import Queue
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,    
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QProgressBar, QComboBox
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import yt_dlp
import shutil

DOWNLOAD_RECORD_FILE = "downloaded_videos.json"

def load_downloaded():
    if os.path.exists(DOWNLOAD_RECORD_FILE):
        with open(DOWNLOAD_RECORD_FILE, "r") as f:
            try:
                return set(json.load(f))
            except Exception:
                return set()
    return set()

def save_downloaded(downloaded_set):
    with open(DOWNLOAD_RECORD_FILE, "w") as f:
        json.dump(list(downloaded_set), f)

def extract_video_id(url):
    try:
        return url.split("/shorts/")[1].split("?")[0]
    except Exception as e:
        return url

class YouTubeShortsDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Shorts Downloader")
        self.setGeometry(100, 100, 650, 400)
        self.downloaded_videos = load_downloaded()
        self.quality_options = {
            "Best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
            "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]"
        }
        self._stop_event = threading.Event()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Link input
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Nhập link kênh YouTube chứa Shorts")
        layout.addWidget(QLabel("🔗 Link kênh:"))
        layout.addWidget(self.link_input)

        # Quality dropdown
        self.quality_dropdown = QComboBox()
        self.quality_dropdown.addItems(self.quality_options.keys())
        layout.addWidget(QLabel("📊 Chọn chất lượng tải:"))
        layout.addWidget(self.quality_dropdown)

        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_btn = QPushButton("Chọn thư mục...")
        self.folder_btn.clicked.connect(self.choose_folder)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.folder_btn)
        layout.addWidget(QLabel("📁 Thư mục lưu video:"))
        layout.addLayout(folder_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 Bắt đầu tải")
        self.start_btn.clicked.connect(self.start_download)
        self.stop_btn = QPushButton("⛔ Dừng tải")
        self.stop_btn.clicked.connect(self.stop_download)
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)

        # Progress bar and log output
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("📜 Log tiến trình:"))
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu video")
        if folder:
            self.folder_input.setText(folder)

    def log(self, message):
        QMetaObject.invokeMethod(self.log_output, "append", Qt.QueuedConnection, Q_ARG(str, message))

    def set_progress_value(self, value):
        QMetaObject.invokeMethod(self.progress_bar, "setValue", Qt.QueuedConnection, Q_ARG(int, value))

    def enable_start_button(self):
        QMetaObject.invokeMethod(self.start_btn, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))

    def stop_download(self):
        self._stop_event.set()
        self.log("🛑 Đã yêu cầu dừng tải...")

    def start_download(self):
        self._stop_event.clear()
        self.start_btn.setEnabled(False)
        self.log_output.clear()
        threading.Thread(target=self.crawl_and_download, daemon=True).start()

    def crawl_and_download(self):
        channel_url = self.link_input.text().strip()
        save_path = self.folder_input.text().strip()
        if not channel_url or not save_path:
            self.log("❌ Vui lòng nhập đầy đủ link và thư mục lưu.")
            self.enable_start_button()
            return

        # Kiểm tra ffmpeg
        if not shutil.which("ffmpeg"):
            self.log("⚠️ Không tìm thấy ffmpeg. Cài đặt ffmpeg để có chất lượng tải tốt hơn.")
            self.log("🔗 https://github.com/yt-dlp/yt-dlp#dependencies")

        quality_choice = self.quality_dropdown.currentText()
        quality_str = self.quality_options.get(quality_choice, self.quality_options["Best"])

        self.log(f"🔍 Đang lấy danh sách Shorts từ: {channel_url}")
        shorts_links = self.get_shorts_links(channel_url)

        if not shorts_links:
            self.log("⚠️ Không tìm thấy video Shorts nào.")
            self.enable_start_button()
            return

        self.log(f"🔗 Tìm thấy {len(shorts_links)} video. Bắt đầu tải...")
        QMetaObject.invokeMethod(self.progress_bar, "setMaximum", Qt.QueuedConnection, Q_ARG(int, len(shorts_links)))
        self.set_progress_value(0)

        idx = 0
        for url in shorts_links:
            if self._stop_event.is_set():
                self.log("⛔ Dừng tiến trình tải video.")
                break

            video_id = extract_video_id(url)
            if video_id in self.downloaded_videos:
                self.log(f"⏭️ Bỏ qua video (đã tải): {url}")
            else:
                self.log(f"⬇️ Đang tải video: {url}")
                try:
                    ydl_opts = {
                        'outtmpl': os.path.join(save_path, '%(title).80s.%(ext)s'),
                        'format': quality_str,
                        'quiet': True,
                        'noplaylist': True,
                        'merge_output_format': 'mp4'
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    self.downloaded_videos.add(video_id)
                    save_downloaded(self.downloaded_videos)
                except Exception as e:
                    self.log(f"⚠️ Lỗi khi tải video: {e}")
            idx += 1
            self.set_progress_value(idx)

        self.log("✅ Hoàn tất tải xuống hoặc đã dừng quá trình.")
        self.enable_start_button()

    def get_shorts_links(self, channel_url):
        from selenium.webdriver.chrome.service import Service

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--log-level=3")

        driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
        try:
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            self.log(f"❌ Không khởi chạy được ChromeDriver: {e}")
            return []

        links = []
        try:
            driver.get(channel_url)
            self.log("🕵️ Phân tích trang kênh...")
            self.auto_scroll(driver)

            elements = driver.find_elements("xpath", '//a[contains(@href, "/shorts/")]')
            raw_links = [el.get_attribute("href") for el in elements if el.get_attribute("href") and "/shorts/" in el.get_attribute("href")]
            links = list(set(raw_links))
            self.log(f"🔗 Tìm thấy {len(links)} đường link Shorts.")
        except Exception as e:
            self.log(f"❌ Lỗi khi lấy link: {e}")
        finally:
            driver.quit()
        return links

    def auto_scroll(self, driver, pause_time=2, max_attempts=10):
        attempt = 0
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        while attempt < max_attempts:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(pause_time)
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                attempt += 1
            else:
                attempt = 0
                last_height = new_height

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YouTubeShortsDownloader()
    window.show()
    sys.exit(app.exec_())
