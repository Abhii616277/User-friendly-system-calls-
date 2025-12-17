import sys
import os
import cv2
import subprocess
import shutil
import time

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QFileDialog, QMessageBox, QTextEdit, QInputDialog, QProgressBar
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import (
    QTimer, Qt, QUrl, QPropertyAnimation, QEasingCurve,
    QRect, QThread, pyqtSignal
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

IMG_FOLDER = resource_path("img")
os.makedirs(IMG_FOLDER, exist_ok=True)


class WorkerThread(QThread):
    finished = pyqtSignal(str, bool)

    def __init__(self, operation):
        super().__init__()
        self.operation = operation

    def run(self):
        try:
            result = self.operation()
            self.finished.emit(str(result), True)
        except Exception as e:
            self.finished.emit(str(e), False)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ultimate GUI")
        
        # FORCE WINDOW TO CENTER OF SCREEN
        screen = QApplication.primaryScreen().geometry()
        window_width = 1100
        window_height = 750
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        
        # ENSURE WINDOW IS NOT TRANSPARENT
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # CRITICAL: Add visible background and styling
        self.setStyleSheet("""
            QWidget#MainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e,
                    stop:1 #16213e
                );
                color: white;
                font-size: 16px;
            }

            QWidget {
                background: transparent;
            }

            QListWidget {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                padding: 5px;
                font-size: 16px;
            }

            QListWidget::item {
                padding: 10px;
                border-radius: 8px;
                margin: 2px;
            }

            QListWidget::item:selected {
                background: rgba(100, 200, 255, 0.3);
            }

            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.1);
            }

            QPushButton {
                background: rgba(100, 200, 255, 0.2);
                border: 1px solid rgba(100, 200, 255, 0.3);
                border-radius: 10px;
                padding: 10px;
                font-weight: bold;
            }

            QPushButton:hover {
                background: rgba(100, 200, 255, 0.25);
                border: 1px solid rgba(100, 200, 255, 0.4);
            }

            QPushButton:pressed {
                background: rgba(100, 200, 255, 0.4);
            }

            QLabel {
                background: transparent;
                color: white;
            }

            QTextEdit {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                padding: 10px;
            }

            QProgressBar {
                border: 2px solid rgba(100, 200, 255, 0.5);
                border-radius: 10px;
                background: rgba(0, 0, 0, 0.5);
                text-align: center;
                color: white;
                font-weight: bold;
                height: 30px;
            }

            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4ff,
                    stop:1 #0080ff
                );
                border-radius: 8px;
            }
        """)

        self.cap = None
        self.timer = None
        self.media_player = None
        self.audio_player = None
        self.video_widget = None
        self.current_images = []
        self.current_image_index = 0

        self.loading_overlay = None
        self.progress_bar = None
        self.spinner_timer = None

        layout = QHBoxLayout(self)

        self.menu = QListWidget()
        self.menu.setFixedWidth(180)
        self.menu.addItems([
            "Home", "Gallery", "Camera",
            "Video Player", "Music Player",
            "Tools", "Settings"
        ])
        self.menu.currentRowChanged.connect(self.switch_page)

        self.pages = QWidget()
        self.pages_layout = QVBoxLayout(self.pages)

        layout.addWidget(self.menu)
        layout.addWidget(self.pages)

        self.show_home()
        # TEMPORARILY DISABLE ANIMATION TO TEST VISIBILITY
        # self.animate_entry()

    def animate_entry(self):
        self.setWindowOpacity(0)
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(800)
        fade.setStartValue(0)
        fade.setEndValue(1)
        fade.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade.start()
        
        menu_start_x = -self.menu.width()
        slide = QPropertyAnimation(self.menu, b"geometry")
        slide.setDuration(1000)
        slide.setStartValue(QRect(menu_start_x, 0, self.menu.width(), self.height()))
        slide.setEndValue(QRect(0, 0, self.menu.width(), self.height()))
        slide.setEasingCurve(QEasingCurve.Type.OutBounce)
        QTimer.singleShot(200, slide.start)

    def show_loading(self, message="Processing..."):
        self.loading_overlay = QWidget(self)
        self.loading_overlay.setStyleSheet("background: rgba(0,0,0,0.8);")
        self.loading_overlay.setGeometry(0, 0, self.width(), self.height())

        layout = QVBoxLayout(self.loading_overlay)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner_label = QLabel("⚙️")
        self.spinner_label.setStyleSheet("font-size:64px;color:white;")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.spinner_label)

        label = QLabel(message)
        label.setStyleSheet("color:white;font-size:20px;font-weight:bold;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedWidth(400)
        layout.addWidget(self.progress_bar)

        self.loading_overlay.show()
        
        self.spinner_timer = QTimer()
        self.spinner_state = 0
        self.spinner_chars = ["⚙️", "⚡", "⭐", "✨", "💫", "🔄"]
        self.spinner_timer.timeout.connect(self.update_spinner)
        self.spinner_timer.start(150)

    def update_spinner(self):
        if hasattr(self, 'spinner_label'):
            self.spinner_state = (self.spinner_state + 1) % len(self.spinner_chars)
            self.spinner_label.setText(self.spinner_chars[self.spinner_state])

    def hide_loading(self):
        if self.spinner_timer:
            self.spinner_timer.stop()
        if self.loading_overlay:
            self.loading_overlay.deleteLater()
            self.loading_overlay = None

    def update_progress(self, value):
        if self.progress_bar:
            self.progress_bar.setValue(value)

    def switch_page(self, index):
        self.cleanup_resources()
        for i in reversed(range(self.pages_layout.count())):
            w = self.pages_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        if index == 0:
            self.show_home()
        elif index == 1:
            self.show_gallery()
        elif index == 2:
            self.show_camera()
        elif index == 3:
            self.show_video_player()
        elif index == 4:
            self.show_music_player()
        elif index == 5:
            self.show_tools()
        elif index == 6:
            self.show_settings()

    def cleanup_resources(self):
        if self.timer:
            try:
                self.timer.stop()
            except:
                pass
            self.timer = None
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        if self.media_player:
            try:
                self.media_player.stop()
            except:
                pass
            self.media_player = None
        if self.audio_player:
            try:
                self.audio_player.stop()
            except:
                pass
            self.audio_player = None

    def show_home(self):
        label = QLabel("✨ Welcome to the Ultimate GUI ✨")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size:36px;font-weight:bold;color:#00d4ff;")
        self.pages_layout.addWidget(label)

    def show_gallery(self):
        # Ask for gallery permission
        reply = QMessageBox.question(
            self, "🖼️ Gallery Access", 
            "This app needs access to view your images.\n\nAllow gallery access?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            label = QLabel("❌ Gallery access denied")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size:20px;color:#ff6b6b;")
            self.pages_layout.addWidget(label)
            return
        
        self.show_loading("Loading gallery...")
        QTimer.singleShot(300, self._load_gallery)
    
    def _load_gallery(self):
        self.hide_loading()
        
        layout = QVBoxLayout()
        
        label = QLabel("🖼️ Image Gallery")
        label.setStyleSheet("font-size:24px;font-weight:bold;color:#00d4ff;")
        layout.addWidget(label)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setMinimumSize(600, 400)
        layout.addWidget(self.img_label)

        self.current_images = []
        self.current_image_index = 0

        try:
            for file in os.listdir(IMG_FOLDER):
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    self.current_images.append(os.path.join(IMG_FOLDER, file))
        except:
            pass

        if not self.current_images:
            self.img_label.setText("❌ No images found\nCapture a photo from Camera!")
            self.img_label.setStyleSheet("font-size:18px;")
        else:
            nav_layout = QHBoxLayout()
            
            prev_btn = QPushButton("◀ Previous")
            prev_btn.clicked.connect(self.show_prev_image)
            nav_layout.addWidget(prev_btn)
            
            self.image_counter = QLabel()
            self.image_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nav_layout.addWidget(self.image_counter)
            
            next_btn = QPushButton("Next ▶")
            next_btn.clicked.connect(self.show_next_image)
            nav_layout.addWidget(next_btn)
            
            layout.addLayout(nav_layout)
            self.display_current_image()

        widget = QWidget()
        widget.setLayout(layout)
        self.pages_layout.addWidget(widget)

    def display_current_image(self):
        if not self.current_images:
            return
        try:
            img_path = self.current_images[self.current_image_index]
            pix = QPixmap(img_path)
            if not pix.isNull():
                scaled = pix.scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation)
                self.img_label.setPixmap(scaled)
                self.image_counter.setText(f"Image {self.current_image_index + 1} / {len(self.current_images)}")
        except:
            pass

    def show_next_image(self):
        if self.current_images:
            self.current_image_index = (self.current_image_index + 1) % len(self.current_images)
            self.display_current_image()

    def show_prev_image(self):
        if self.current_images:
            self.current_image_index = (self.current_image_index - 1) % len(self.current_images)
            self.display_current_image()

    def show_camera(self):
        # Ask for camera permission
        reply = QMessageBox.question(
            self, "📸 Camera Access", 
            "This app needs access to your camera.\n\nAllow camera access?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            label = QLabel("❌ Camera access denied")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size:20px;color:#ff6b6b;")
            self.pages_layout.addWidget(label)
            return
        
        self.show_loading("Opening camera...")
        QTimer.singleShot(500, self._open_camera)
    
    def _open_camera(self):
        self.hide_loading()
        
        layout = QVBoxLayout()
        
        label = QLabel("📸 Camera")
        label.setStyleSheet("font-size:24px;font-weight:bold;color:#00d4ff;")
        layout.addWidget(label)
        
        self.video_label = QLabel("Starting camera...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        layout.addWidget(self.video_label)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.video_label.setText("❌ Camera not available")
        else:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)
            
            btn = QPushButton("📸 Capture Photo")
            btn.clicked.connect(self.take_photo)
            layout.addWidget(btn)

        widget = QWidget()
        widget.setLayout(layout)
        self.pages_layout.addWidget(widget)

    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
        try:
            ret, frame = self.cap.read()
            if not ret:
                return
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
            scaled = QPixmap.fromImage(img).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
            if self.video_label:  # Check if label still exists
                self.video_label.setPixmap(scaled)
        except Exception as e:
            # Silently handle errors without printing
            pass

    def take_photo(self):
        if not self.cap or not self.cap.isOpened():
            QMessageBox.warning(self, "Error", "Camera not available!")
            return
        try:
            ret, frame = self.cap.read()
            if ret:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(IMG_FOLDER, f"captured_{timestamp}.png")
                cv2.imwrite(save_path, frame)
                QMessageBox.information(self, "Success", f"✔ Photo saved!\nCheck Gallery to view it.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to capture: {str(e)}")

    def show_video_player(self):
        layout = QVBoxLayout()
        
        label = QLabel("🎥 Video Player")
        label.setStyleSheet("font-size:24px;font-weight:bold;color:#00d4ff;")
        layout.addWidget(label)
        
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(640, 480)
        layout.addWidget(self.video_widget)

        self.media_player = QMediaPlayer()
        audio = QAudioOutput()
        self.media_player.setAudioOutput(audio)
        self.media_player.setVideoOutput(self.video_widget)

        btn_layout = QHBoxLayout()
        
        load_btn = QPushButton("🎥 Load Video")
        load_btn.clicked.connect(self.load_video)
        btn_layout.addWidget(load_btn)
        
        play_btn = QPushButton("▶ Play")
        play_btn.clicked.connect(lambda: self.media_player.play())
        btn_layout.addWidget(play_btn)
        
        pause_btn = QPushButton("⏸ Pause")
        pause_btn.clicked.connect(lambda: self.media_player.pause())
        btn_layout.addWidget(pause_btn)
        
        stop_btn = QPushButton("⏹ Stop")
        stop_btn.clicked.connect(lambda: self.media_player.stop())
        btn_layout.addWidget(stop_btn)
        
        layout.addLayout(btn_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.pages_layout.addWidget(widget)

    def load_video(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Videos (*.mp4 *.avi *.mkv)")
        if fname:
            self.media_player.setSource(QUrl.fromLocalFile(fname))
            self.media_player.play()

    def show_music_player(self):
        layout = QVBoxLayout()
        
        label = QLabel("🎵 Music Player")
        label.setStyleSheet("font-size:24px;font-weight:bold;color:#00d4ff;")
        layout.addWidget(label)
        
        self.song_label = QLabel("No song loaded")
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_label.setStyleSheet("font-size:18px;")
        layout.addWidget(self.song_label)
        
        # Create audio player with audio output
        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()  # Store as instance variable
        self.audio_player.setAudioOutput(self.audio_output)

        btn_layout = QHBoxLayout()
        
        load_btn = QPushButton("🎵 Load Music")
        load_btn.clicked.connect(self.load_audio)
        btn_layout.addWidget(load_btn)
        
        play_btn = QPushButton("▶ Play")
        play_btn.clicked.connect(lambda: self.audio_player.play() if self.audio_player else None)
        btn_layout.addWidget(play_btn)
        
        pause_btn = QPushButton("⏸ Pause")
        pause_btn.clicked.connect(lambda: self.audio_player.pause() if self.audio_player else None)
        btn_layout.addWidget(pause_btn)
        
        stop_btn = QPushButton("⏹ Stop")
        stop_btn.clicked.connect(lambda: self.audio_player.stop() if self.audio_player else None)
        btn_layout.addWidget(stop_btn)
        
        layout.addLayout(btn_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.pages_layout.addWidget(widget)

    def load_audio(self):
        # Ask for permission to access files
        reply = QMessageBox.question(
            self, "🎵 File Access", 
            "Allow access to audio files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            QMessageBox.information(self, "Access Denied", "Audio file access denied.")
            return
        
        fname, _ = QFileDialog.getOpenFileName(self, "Open Audio", "", "Audio (*.mp3 *.wav *.ogg *.flac)")
        if fname:
            try:
                self.show_loading("Loading music...")
                self.audio_player.setSource(QUrl.fromLocalFile(fname))
                self.song_label.setText(f"🎵 {os.path.basename(fname)}")
                QTimer.singleShot(500, self._play_audio)
            except Exception as e:
                self.hide_loading()
                QMessageBox.critical(self, "Error", f"Failed to load audio: {str(e)}")
    
    def _play_audio(self):
        self.hide_loading()
        self.audio_player.play()

    def show_tools(self):
        layout = QVBoxLayout()

        label = QLabel("🛠️ System Tools & File Manager")
        label.setStyleSheet("font-size:24px;font-weight:bold;color:#00d4ff;")
        layout.addWidget(label)

        self.tools_output = QTextEdit()
        self.tools_output.setReadOnly(True)
        self.tools_output.setText("Ready. Click a button to run a command...\n")
        layout.addWidget(self.tools_output)

        # Network Tools
        net_layout = QHBoxLayout()
        net_label = QLabel("🌐 Network:")
        net_label.setStyleSheet("font-weight:bold;font-size:14px;")
        net_layout.addWidget(net_label)
        
        ping_btn = QPushButton("Ping Google")
        ping_btn.clicked.connect(self.ping_google)
        net_layout.addWidget(ping_btn)
        
        ip_btn = QPushButton("IP Config")
        ip_btn.clicked.connect(self.show_ipconfig)
        net_layout.addWidget(ip_btn)
        
        net_layout.addStretch()
        layout.addLayout(net_layout)

        # File Operations
        file_layout = QHBoxLayout()
        file_label = QLabel("📁 Files:")
        file_label.setStyleSheet("font-weight:bold;font-size:14px;")
        file_layout.addWidget(file_label)
        
        create_btn = QPushButton("Create File")
        create_btn.clicked.connect(self.create_file)
        file_layout.addWidget(create_btn)
        
        read_btn = QPushButton("Read File")
        read_btn.clicked.connect(self.read_file)
        file_layout.addWidget(read_btn)
        
        delete_btn = QPushButton("Delete File")
        delete_btn.clicked.connect(self.delete_file)
        file_layout.addWidget(delete_btn)
        
        file_layout.addStretch()
        layout.addLayout(file_layout)

        # Folder Operations
        folder_layout = QHBoxLayout()
        folder_label = QLabel("📂 Folders:")
        folder_label.setStyleSheet("font-weight:bold;font-size:14px;")
        folder_layout.addWidget(folder_label)
        
        create_folder_btn = QPushButton("Create Folder")
        create_folder_btn.clicked.connect(self.create_folder)
        folder_layout.addWidget(create_folder_btn)
        
        list_btn = QPushButton("List Directory")
        list_btn.clicked.connect(self.list_directory)
        folder_layout.addWidget(list_btn)
        
        open_btn = QPushButton("Open Downloads")
        open_btn.clicked.connect(lambda: os.startfile(os.path.expanduser("~/Downloads")))
        folder_layout.addWidget(open_btn)
        
        folder_layout.addStretch()
        layout.addLayout(folder_layout)

        # Clear button
        clear_layout = QHBoxLayout()
        clear_layout.addStretch()
        clear_btn = QPushButton("🗑️ Clear Output")
        clear_btn.clicked.connect(self.tools_output.clear)
        clear_layout.addWidget(clear_btn)
        layout.addLayout(clear_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.pages_layout.addWidget(widget)

    def ping_google(self):
        # Ask for network permission
        reply = QMessageBox.question(
            self, "🌐 Network Access", 
            "This will send network requests to Google (8.8.8.8).\n\nAllow network access?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            self.tools_output.append("\n❌ Network access denied\n" + "=" * 50 + "\n")
            return
        
        self.tools_output.append("\n🌐 Pinging Google...\n" + "=" * 50)
        self.show_loading("Pinging Google DNS...")
        
        progress_timer = QTimer()
        progress = [0]
        
        def update_prog():
            progress[0] += 25
            self.update_progress(progress[0])
        
        progress_timer.timeout.connect(update_prog)
        progress_timer.start(250)

        def operation():
            result = subprocess.run(["ping", "8.8.8.8", "-n", "4"], 
                                  capture_output=True, text=True, timeout=10)
            return result.stdout

        self.worker = WorkerThread(operation)
        self.worker.finished.connect(lambda out, ok: self.ping_finished(out, ok, progress_timer))
        self.worker.start()

    def ping_finished(self, output, success, timer):
        timer.stop()
        self.hide_loading()
        if success:
            self.tools_output.append(output + "\n✅ Ping complete!")
        else:
            self.tools_output.append(f"❌ Error: {output}")
        self.tools_output.append("=" * 50 + "\n")

    def show_ipconfig(self):
        # Ask for system info permission
        reply = QMessageBox.question(
            self, "💻 System Access", 
            "This will access your network configuration.\n\nAllow system access?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            self.tools_output.append("\n❌ System access denied\n" + "=" * 50 + "\n")
            return
        
        self.tools_output.append("\n💻 Getting IP Config...\n" + "=" * 50)
        self.show_loading("Fetching Network Info...")
        
        progress_timer = QTimer()
        progress = [0]
        
        def update_prog():
            progress[0] += 20
            self.update_progress(progress[0])
        
        progress_timer.timeout.connect(update_prog)
        progress_timer.start(100)

        def operation():
            result = subprocess.run(["ipconfig"], capture_output=True, text=True)
            return result.stdout

        self.worker = WorkerThread(operation)
        self.worker.finished.connect(lambda out, ok: self.ipconfig_finished(out, ok, progress_timer))
        self.worker.start()

    def ipconfig_finished(self, output, success, timer):
        timer.stop()
        self.hide_loading()
        if success:
            self.tools_output.append(output)
        else:
            self.tools_output.append(f"❌ Error: {output}")
        self.tools_output.append("=" * 50 + "\n")

    # -----------------------------------------------------------
    # FILE OPERATIONS
    # -----------------------------------------------------------
    def create_file(self):
        """Create a new file with permission"""
        # Ask for filename
        filename, ok = QInputDialog.getText(self, "Create File", "Enter filename (e.g., myfile.txt):")
        if not ok or not filename:
            return
        
        # Ask for location
        location = QFileDialog.getExistingDirectory(self, "Select Location to Save File")
        if not location:
            return
        
        filepath = os.path.join(location, filename)
        
        # Permission dialog
        reply = QMessageBox.question(
            self, "Create File", 
            f"Create file at:\n{filepath}\n\nDo you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.show_loading("Creating file...")
            self.update_progress(50)
            
            def operation():
                time.sleep(0.5)  # Simulate work
                with open(filepath, 'w') as f:
                    f.write(f"# File created by Ultimate GUI\n# Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                return filepath
            
            self.worker = WorkerThread(operation)
            self.worker.finished.connect(self.create_file_finished)
            self.worker.start()

    def create_file_finished(self, output, success):
        self.update_progress(100)
        QTimer.singleShot(300, self.hide_loading)
        
        if success:
            filepath = output
            self.tools_output.append(f"\n✅ File created successfully!\n📄 {filepath}\n" + "=" * 50 + "\n")
            QMessageBox.information(self, "Success", f"File created:\n{filepath}")
        else:
            self.tools_output.append(f"\n❌ Error creating file: {output}\n" + "=" * 50 + "\n")

    def read_file(self):
        """Read and display file contents"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select File to Read", "", 
            "Text Files (*.txt *.log *.md *.py *.js);;All Files (*.*)"
        )
        if not filepath:
            return
        
        # Permission dialog
        reply = QMessageBox.question(
            self, "Read File", 
            f"Read file:\n{filepath}\n\nDo you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.show_loading("Reading file...")
            
            def operation():
                time.sleep(0.3)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"{os.path.basename(filepath)}|||{content}"
            
            self.worker = WorkerThread(operation)
            self.worker.finished.connect(self.read_file_finished)
            self.worker.start()

    def read_file_finished(self, output, success):
        self.hide_loading()
        
        if success:
            parts = output.split("|||")
            filename = parts[0]
            content = parts[1] if len(parts) > 1 else ""
            
            self.tools_output.append(f"\n📄 Reading: {filename}\n" + "=" * 50 + "\n")
            self.tools_output.append(content[:1000])  # First 1000 chars
            if len(content) > 1000:
                self.tools_output.append("\n... (truncated)")
            self.tools_output.append("\n" + "=" * 50 + "\n")
        else:
            self.tools_output.append(f"\n❌ Error reading file: {output}\n" + "=" * 50 + "\n")

    def delete_file(self):
        """Delete a file with confirmation"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select File to Delete", "", "All Files (*.*)"
        )
        if not filepath:
            return
        
        # Permission dialog with warning
        reply = QMessageBox.warning(
            self, "⚠️ Delete File", 
            f"DELETE FILE:\n{filepath}\n\n⚠️ This action cannot be undone!\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.show_loading("Deleting file...")
            
            def operation():
                time.sleep(0.5)
                os.remove(filepath)
                return filepath
            
            self.worker = WorkerThread(operation)
            self.worker.finished.connect(self.delete_file_finished)
            self.worker.start()

    def delete_file_finished(self, output, success):
        self.hide_loading()
        
        if success:
            filepath = output
            self.tools_output.append(f"\n✅ File deleted successfully!\n🗑️ {filepath}\n" + "=" * 50 + "\n")
            QMessageBox.information(self, "Success", "File deleted successfully!")
        else:
            self.tools_output.append(f"\n❌ Error deleting file: {output}\n" + "=" * 50 + "\n")

    def create_folder(self):
        """Create a new folder"""
        foldername, ok = QInputDialog.getText(self, "Create Folder", "Enter folder name:")
        if not ok or not foldername:
            return
        
        location = QFileDialog.getExistingDirectory(self, "Select Location to Create Folder")
        if not location:
            return
        
        folderpath = os.path.join(location, foldername)
        
        # Permission dialog
        reply = QMessageBox.question(
            self, "Create Folder", 
            f"Create folder at:\n{folderpath}\n\nDo you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.show_loading("Creating folder...")
            
            def operation():
                time.sleep(0.3)
                os.makedirs(folderpath, exist_ok=True)
                return folderpath
            
            self.worker = WorkerThread(operation)
            self.worker.finished.connect(self.create_folder_finished)
            self.worker.start()

    def create_folder_finished(self, output, success):
        self.hide_loading()
        
        if success:
            folderpath = output
            self.tools_output.append(f"\n✅ Folder created successfully!\n📁 {folderpath}\n" + "=" * 50 + "\n")
            QMessageBox.information(self, "Success", f"Folder created:\n{folderpath}")
        else:
            self.tools_output.append(f"\n❌ Error creating folder: {output}\n" + "=" * 50 + "\n")

    def list_directory(self):
        """List directory contents"""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory to List")
        if not directory:
            return
        
        self.show_loading("Listing directory...")
        
        def operation():
            time.sleep(0.3)
            items = os.listdir(directory)
            folders = [f for f in items if os.path.isdir(os.path.join(directory, f))]
            files = [f for f in items if os.path.isfile(os.path.join(directory, f))]
            return f"{directory}|||{len(folders)}|||{len(files)}|||{'|||'.join(folders[:20])}|||{'|||'.join(files[:20])}"
        
        self.worker = WorkerThread(operation)
        self.worker.finished.connect(self.list_directory_finished)
        self.worker.start()

    def list_directory_finished(self, output, success):
        self.hide_loading()
        
        if success:
            parts = output.split("|||")
            directory = parts[0]
            folder_count = parts[1]
            file_count = parts[2]
            folders = parts[3:3+int(folder_count)] if len(parts) > 3 else []
            files = parts[3+int(folder_count):] if len(parts) > 3+int(folder_count) else []
            
            self.tools_output.append(f"\n📁 Contents of: {directory}\n" + "=" * 50 + "\n")
            self.tools_output.append(f"\n📁 Folders ({folder_count}):\n")
            for folder in folders:
                if folder:
                    self.tools_output.append(f"  └─ 📁 {folder}\n")
            
            self.tools_output.append(f"\n📄 Files ({file_count}):\n")
            for file in files:
                if file:
                    self.tools_output.append(f"  └─ 📄 {file}\n")
            
            self.tools_output.append("\n" + "=" * 50 + "\n")
        else:
            self.tools_output.append(f"\n❌ Error listing directory: {output}\n" + "=" * 50 + "\n")

    def show_settings(self):
        label = QLabel("⚙️ Settings (Coming Soon)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size:28px;font-weight:bold;color:#00d4ff;")
        self.pages_layout.addWidget(label)

    def closeEvent(self, event):
        self.cleanup_resources()
        cv2.destroyAllWindows()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create window
    window = MainWindow()
    
    # ENSURE FULL OPACITY (no transparency)
    window.setWindowOpacity(1.0)
    
    # Show normally (not maximized to avoid issues)
    window.show()
    window.raise_()
    window.activateWindow()
    
    sys.exit(app.exec())