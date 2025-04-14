# youtube_shorts_downloader.py
import sys
import os
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QProgressBar
)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import yt_dlp


class YouTubeShortsDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Shorts Downloader")
        self.setGeometry(100, 100, 600, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Link input
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Nhập link kênh YouTube Shorts")
        layout.addWidget(QLabel("🔗 Link kênh:"))
        layout.addWidget(self.link_input)

        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_btn = QPushButton("Chọn thư mục...")
        self.folder_btn.clicked.connect(self.choose_folder)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.folder_btn)
        layout.addWidget(QLabel("📁 Thư mục lưu video:"))
        layout.addLayout(folder_layout)

        # Start button
        self.start_btn = QPushButton("🚀 Bắt đầu tải")
        self.start_btn.clicked.connect(self.start_download)
        layout.addWidget(self.start_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Log area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("📜 Log tiến trình:"))
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if folder:
            self.folder_input.setText(folder)

    def log(self, message):
        self.log_output.append(message)

    def start_download(self):
        self.start_btn.setEnabled(False)
        self.log_output.clear()
        threading.Thread(target=self.crawl_and_download).start()

    def crawl_and_download(self):
        channel_url = self.link_input.text().strip()
        download_path = self.folder_input.text().strip()

        if not channel_url or not download_path:
            self.log("❌ Vui lòng nhập đầy đủ link và thư mục.")
            self.start_btn.setEnabled(True)
            return

        # Step 1: Dùng Selenium để crawl danh sách video shorts
        self.log("🔍 Đang lấy danh sách Shorts...")
        shorts_links = self.get_shorts_links(channel_url)

        if not shorts_links:
            self.log("⚠️ Không tìm thấy Shorts nào.")
            self.start_btn.setEnabled(True)
            return

        # Step 2: Dùng yt-dlp để tải từng video
        self.progress_bar.setMaximum(len(shorts_links))
        self.progress_bar.setValue(0)

        for idx, url in enumerate(shorts_links):
            self.log(f"⬇️ Đang tải: {url}")
            try:
                ydl_opts = {
                    'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'noplaylist': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                self.log(f"⚠️ Lỗi: {e}")
            self.progress_bar.setValue(idx + 1)

        self.log("✅ Hoàn tất!")
        self.start_btn.setEnabled(True)

    def get_shorts_links(self, channel_url):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=chrome_options)

        try:
            driver.get(channel_url)
            self.log("🕵️ Đang phân tích trang...")
            self.scroll_page(driver)

            elements = driver.find_elements("xpath", '//a[contains(@href, "/shorts/")]')
            links = list(set([el.get_attribute("href") for el in elements if el.get_attribute("href") and "/shorts/" in el.get_attribute("href")]))
            self.log(f"🔗 Đã tìm thấy {len(links)} video.")
            return links
        finally:
            driver.quit()

    def scroll_page(self, driver, max_scrolls=5):
        for _ in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            QApplication.processEvents()
            driver.implicitly_wait(2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = YouTubeShortsDownloader()
    win.show()
    sys.exit(app.exec_())
