
import sys
import os
import cv2
import subprocess
import shutil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QFileDialog, QMessageBox, QTextEdit, QInputDialog
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QTimer, Qt, QUrl, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


IMG_FOLDER = os.path.join(os.path.dirname(__file__), "img")

# Create img folder if it doesn't exist
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ultimate GUI")
        self.setGeometry(200, 80, 1100, 750)

        # --- Glass Morphic OS Theme ---
        self.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.10);
                color: white;
                font-size: 16px;
            }
            QListWidget {
                background: rgba(255, 255, 255, 0.15);
                border: none;
                font-size: 18px;
            }
            QListWidget::item:selected {
                background: rgba(255, 255, 255, 0.30);
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.20);
                border-radius: 12px;
                padding: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.35);
            }
            QLabel {
                background: transparent;
                color: white;
            }
        """)

        # Initialize all media resources
        self.cap = None
        self.timer = None
        self.media_player = None
        self.audio_player = None
        self.video_widget = None
        self.current_images = []
        self.current_image_index = 0

        # MAIN LAYOUT
        layout = QHBoxLayout(self)

        # Sidebar
        self.menu = QListWidget()
        self.menu.setFixedWidth(180)
        self.menu.addItems(["Home", "Gallery", "Camera", "Video Player", "Music Player", "Tools", "Settings"])
        self.menu.currentRowChanged.connect(self.switch_page)

        # Page container
        self.pages = QWidget()
        self.pages_layout = QVBoxLayout(self.pages)

        # Add menus
        layout.addWidget(self.menu)
        layout.addWidget(self.pages)

        self.show_home()
        
        # START ENTRY ANIMATIONS
        self.animate_entry()

    # -----------------------------------------------------------
    # ENTRY ANIMATION
    # -----------------------------------------------------------
    def animate_entry(self):
        """Create eye-catching entry animations"""
        # Set initial states for animation
        self.setWindowOpacity(0)  # Start invisible
        
        # Sidebar slide in from left
        self.menu_start_pos = QPoint(-180, self.menu.y())
        self.menu.move(self.menu_start_pos)
        
        # Fade in window
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(800)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.start()
        
        # Slide in sidebar
        self.slide_anim = QPropertyAnimation(self.menu, b"pos")
        self.slide_anim.setDuration(1000)
        self.slide_anim.setStartValue(QPoint(-180, self.menu.y()))
        self.slide_anim.setEndValue(QPoint(0, self.menu.y()))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        QTimer.singleShot(200, self.slide_anim.start)
        
        # Zoom in pages container
        self.pages.setStyleSheet("QWidget { transform: scale(0.8); }")
        QTimer.singleShot(400, self.animate_pages_zoom)
        
        # START ENTRY ANIMATIONS
        self.animate_entry()

    # -----------------------------------------------------------
    # SAFE PAGE SWITCHING
    # -----------------------------------------------------------
    def switch_page(self, index):
        # Stop all media resources
        self.cleanup_resources()

        # Clear old widgets
        for i in reversed(range(self.pages_layout.count())):
            widget = self.pages_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # Show new page
        if index == 0: self.show_home()
        elif index == 1: self.show_gallery()
        elif index == 2: self.show_camera()
        elif index == 3: self.show_video_player()
        elif index == 4: self.show_music_player()
        elif index == 5: self.show_tools()
        elif index == 6: self.show_settings()

    def cleanup_resources(self):
        """Clean up all media resources safely"""
        # Stop camera
        if self.timer:
            try:
                self.timer.stop()
                self.timer.deleteLater()
            except:
                pass
            self.timer = None

        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None

        # Stop video player
        if self.media_player:
            try:
                self.media_player.stop()
                self.media_player.setVideoOutput(None)
                self.media_player.deleteLater()
            except:
                pass
            self.media_player = None

        # Stop audio player
        if self.audio_player:
            try:
                self.audio_player.stop()
                self.audio_player.deleteLater()
            except:
                pass
            self.audio_player = None

        self.video_widget = None

    # -----------------------------------------------------------
    # HOME PAGE
    # -----------------------------------------------------------
    def show_home(self):
        label = QLabel("✨ Welcome to the UI ✨")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 32px; font-weight: bold;")
        self.pages_layout.addWidget(label)

    # -----------------------------------------------------------
    # IMAGE GALLERY (FIXED)
    # -----------------------------------------------------------
    def show_gallery(self):
        container = QVBoxLayout()
        
        label = QLabel("Image Gallery")
        label.setStyleSheet("font-size: 24px; font-weight: bold;")
        container.addWidget(label)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setMinimumSize(600, 400)
        container.addWidget(self.img_label)

        # Load all images
        self.current_images = []
        self.current_image_index = 0

        try:
            for file in os.listdir(IMG_FOLDER):
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    self.current_images.append(os.path.join(IMG_FOLDER, file))
        except Exception as e:
            print(f"Error loading images: {e}")

        if not self.current_images:
            self.img_label.setText("❌ No images found in /img/\nCapture a photo from Camera to see it here!")
            self.img_label.setStyleSheet("font-size: 18px;")
        else:
            # Navigation buttons
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
            
            container.addLayout(nav_layout)
            
            # Show first image
            self.display_current_image()

        widget = QWidget()
        widget.setLayout(container)
        self.pages_layout.addWidget(widget)

    def display_current_image(self):
        """Display the current image in gallery"""
        if not self.current_images:
            return
            
        try:
            img_path = self.current_images[self.current_image_index]
            pix = QPixmap(img_path)
            
            if pix.isNull():
                self.img_label.setText("❌ Error loading image")
                return
                
            scaled_pix = pix.scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(scaled_pix)
            
            # Update counter
            self.image_counter.setText(f"Image {self.current_image_index + 1} / {len(self.current_images)}")
        except Exception as e:
            self.img_label.setText(f"❌ Error: {str(e)}")

    def show_next_image(self):
        if self.current_images:
            self.current_image_index = (self.current_image_index + 1) % len(self.current_images)
            self.display_current_image()

    def show_prev_image(self):
        if self.current_images:
            self.current_image_index = (self.current_image_index - 1) % len(self.current_images)
            self.display_current_image()

    # -----------------------------------------------------------
    # CAMERA PAGE (FIXED)
    # -----------------------------------------------------------
    def show_camera(self):
        self.camera_layout = QVBoxLayout()

        self.video_label = QLabel("Opening camera…")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.camera_layout.addWidget(self.video_label)

        # Try to open camera
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.video_label.setText("❌ Cannot open camera\nPlease check camera connection")
                widget = QWidget()
                widget.setLayout(self.camera_layout)
                self.pages_layout.addWidget(widget)
                return
        except Exception as e:
            self.video_label.setText(f"❌ Camera error: {str(e)}")
            widget = QWidget()
            widget.setLayout(self.camera_layout)
            self.pages_layout.addWidget(widget)
            return

        # Timer for camera frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # Buttons
        btn_layout = QHBoxLayout()
        
        snap_btn = QPushButton("📸 Capture Photo")
        snap_btn.clicked.connect(self.take_photo)
        btn_layout.addWidget(snap_btn)

        self.camera_layout.addLayout(btn_layout)

        widget = QWidget()
        widget.setLayout(self.camera_layout)
        self.pages_layout.addWidget(widget)

    def update_frame(self):
        """Update camera frame safely"""
        if not self.cap or not self.cap.isOpened():
            return

        try:
            ret, frame = self.cap.read()
            if not ret:
                return

            # Convert and display
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            if self.video_label:
                pixmap = QPixmap.fromImage(q_img)
                scaled = pixmap.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.FastTransformation)
                self.video_label.setPixmap(scaled)
        except Exception as e:
            print(f"Frame update error: {e}")

    def take_photo(self):
        """Capture photo safely"""
        if not self.cap or not self.cap.isOpened():
            QMessageBox.warning(self, "Error", "Camera not available!")
            return

        try:
            ret, frame = self.cap.read()
            if ret:
                # Generate unique filename
                import time
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(IMG_FOLDER, f"captured_{timestamp}.png")
                
                # Save image
                success = cv2.imwrite(save_path, frame)
                
                if success:
                    QMessageBox.information(self, "Success", 
                        f"✔ Photo saved!\n{save_path}\n\nCheck Gallery to view it.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to save photo!")
            else:
                QMessageBox.warning(self, "Error", "Failed to capture frame!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Capture failed: {str(e)}")

    # -----------------------------------------------------------
    # VIDEO PLAYER (FIXED)
    # -----------------------------------------------------------
    def show_video_player(self):
        layout = QVBoxLayout()

        label = QLabel("Video Player")
        label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(label)

        # Create video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(640, 480)
        layout.addWidget(self.video_widget)

        # Create media player
        self.media_player = QMediaPlayer()
        audio = QAudioOutput()
        self.media_player.setAudioOutput(audio)
        self.media_player.setVideoOutput(self.video_widget)

        # Control buttons
        btn_layout = QHBoxLayout()
        
        load_btn = QPushButton("🎥 Load Video")
        load_btn.clicked.connect(self.load_video)
        btn_layout.addWidget(load_btn)
        
        play_btn = QPushButton("▶ Play")
        play_btn.clicked.connect(lambda: self.media_player.play() if self.media_player else None)
        btn_layout.addWidget(play_btn)
        
        pause_btn = QPushButton("⏸ Pause")
        pause_btn.clicked.connect(lambda: self.media_player.pause() if self.media_player else None)
        btn_layout.addWidget(pause_btn)
        
        stop_btn = QPushButton("⏹ Stop")
        stop_btn.clicked.connect(lambda: self.media_player.stop() if self.media_player else None)
        btn_layout.addWidget(stop_btn)

        layout.addLayout(btn_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.pages_layout.addWidget(widget)

    def load_video(self):
        """Load video file safely"""
        try:
            fname, _ = QFileDialog.getOpenFileName(
                self, "Select Video", "", 
                "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)"
            )
            if fname:
                self.media_player.setSource(QUrl.fromLocalFile(fname))
                self.media_player.play()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load video: {str(e)}")

    # -----------------------------------------------------------
    # MUSIC PLAYER (FIXED)
    # -----------------------------------------------------------
    def show_music_player(self):
        layout = QVBoxLayout()

        label = QLabel("Music Player")
        label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(label)

        self.song_label = QLabel("No song loaded")
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.song_label)

        # Create audio player
        self.audio_player = QMediaPlayer()
        audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(audio_output)

        # Control buttons
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
        """Load audio file safely"""
        try:
            fname, _ = QFileDialog.getOpenFileName(
                self, "Select Audio", "", 
                "Audio Files (*.mp3 *.wav *.ogg *.flac);;All Files (*.*)"
            )
            if fname:
                self.audio_player.setSource(QUrl.fromLocalFile(fname))
                self.song_label.setText(f"🎵 {os.path.basename(fname)}")
                self.audio_player.play()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load audio: {str(e)}")

    # -----------------------------------------------------------
    # SYSTEM TOOLS
    # -----------------------------------------------------------
    def show_tools(self):
        layout = QVBoxLayout()

        label = QLabel("System Tools & File Manager")
        label.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(label)

        # Output display
        self.tools_output = QTextEdit()
        self.tools_output.setReadOnly(True)
        self.tools_output.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.5);
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.tools_output.setText("Ready. Click a button to run a command...\n")
        layout.addWidget(self.tools_output)

        # Network Tools Row
        net_layout = QHBoxLayout()
        net_label = QLabel("🌐 Network Tools:")
        net_label.setStyleSheet("font-weight: bold;")
        net_layout.addWidget(net_label)

        btn_ping = QPushButton("Ping Google")
        btn_ping.clicked.connect(self.ping_google)
        net_layout.addWidget(btn_ping)

        btn_ipconfig = QPushButton("IP Config")
        btn_ipconfig.clicked.connect(self.show_ipconfig)
        net_layout.addWidget(btn_ipconfig)

        net_layout.addStretch()
        layout.addLayout(net_layout)

        # File Operations Row 1
        file_layout1 = QHBoxLayout()
        file_label = QLabel("📁 File Operations:")
        file_label.setStyleSheet("font-weight: bold;")
        file_layout1.addWidget(file_label)

        btn_create_file = QPushButton("Create File")
        btn_create_file.clicked.connect(self.create_file)
        file_layout1.addWidget(btn_create_file)

        btn_create_folder = QPushButton("Create Folder")
        btn_create_folder.clicked.connect(self.create_folder)
        file_layout1.addWidget(btn_create_folder)

        btn_delete = QPushButton("Delete File/Folder")
        btn_delete.clicked.connect(self.delete_file)
        file_layout1.addWidget(btn_delete)

        file_layout1.addStretch()
        layout.addLayout(file_layout1)

        # File Operations Row 2
        file_layout2 = QHBoxLayout()
        file_layout2.addWidget(QLabel(""))  # Spacing

        btn_rename = QPushButton("Rename")
        btn_rename.clicked.connect(self.rename_file)
        file_layout2.addWidget(btn_rename)

        btn_copy = QPushButton("Copy File")
        btn_copy.clicked.connect(self.copy_file)
        file_layout2.addWidget(btn_copy)

        btn_move = QPushButton("Move File")
        btn_move.clicked.connect(self.move_file)
        file_layout2.addWidget(btn_move)

        btn_read = QPushButton("Read Text File")
        btn_read.clicked.connect(self.read_file)
        file_layout2.addWidget(btn_read)

        file_layout2.addStretch()
        layout.addLayout(file_layout2)

        # System Tools Row
        sys_layout = QHBoxLayout()
        sys_label = QLabel("🛠️ System:")
        sys_label.setStyleSheet("font-weight: bold;")
        sys_layout.addWidget(sys_label)

        btn_open_downloads = QPushButton("Open Downloads")
        btn_open_downloads.clicked.connect(lambda: os.startfile(os.path.expanduser("~/Downloads")))
        sys_layout.addWidget(btn_open_downloads)

        btn_open_desktop = QPushButton("Open Desktop")
        btn_open_desktop.clicked.connect(lambda: os.startfile(os.path.expanduser("~/Desktop")))
        sys_layout.addWidget(btn_open_desktop)

        btn_list_dir = QPushButton("List Directory")
        btn_list_dir.clicked.connect(self.list_directory)
        sys_layout.addWidget(btn_list_dir)

        btn_clear = QPushButton("Clear Output")
        btn_clear.clicked.connect(lambda: self.tools_output.clear())
        sys_layout.addWidget(btn_clear)

        sys_layout.addStretch()
        layout.addLayout(sys_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.pages_layout.addWidget(widget)

    def ping_google(self):
        """Ping Google and show results"""
        self.tools_output.append("\n🌐 Pinging 8.8.8.8 (Google DNS)...\n")
        self.tools_output.append("=" * 50 + "\n")

    # -----------------------------------------------------------
    # FILE OPERATIONS
    # -----------------------------------------------------------
    def create_file(self):
        """Create a new text file"""
        filename, ok = QInputDialog.getText(self, "Create File", "Enter filename (with .txt):")
        if not ok or not filename:
            return
        
        location = QFileDialog.getExistingDirectory(self, "Select Location to Save File")
        if not location:
            return
        
        filepath = os.path.join(location, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write("# New file created by Ultimate GUI\n")
            
            self.tools_output.append(f"\n✅ File created successfully!\n")
            self.tools_output.append(f"📄 {filepath}\n")
            self.tools_output.append("=" * 50 + "\n")
            
        except Exception as e:
            self.tools_output.append(f"\n❌ Error creating file: {str(e)}\n")
            self.tools_output.append("=" * 50 + "\n")

    def create_folder(self):
        """Create a new folder"""
        foldername, ok = QInputDialog.getText(self, "Create Folder", "Enter folder name:")
        if not ok or not foldername:
            return
        
        location = QFileDialog.getExistingDirectory(self, "Select Location to Create Folder")
        if not location:
            return
        
        folderpath = os.path.join(location, foldername)
        
        try:
            os.makedirs(folderpath, exist_ok=True)
            
            self.tools_output.append(f"\n✅ Folder created successfully!\n")
            self.tools_output.append(f"📁 {folderpath}\n")
            self.tools_output.append("=" * 50 + "\n")
            
        except Exception as e:
            self.tools_output.append(f"\n❌ Error creating folder: {str(e)}\n")
            self.tools_output.append("=" * 50 + "\n")

    def delete_file(self):
        """Delete a file or folder"""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Delete", "", "All Files (*.*)")
        
        if not filepath:
            # If no file selected, try folder
            filepath = QFileDialog.getExistingDirectory(self, "Select Folder to Delete")
        
        if not filepath:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete:\n{filepath}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    self.tools_output.append(f"\n✅ File deleted successfully!\n")
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath)
                    self.tools_output.append(f"\n✅ Folder deleted successfully!\n")
                
                self.tools_output.append(f"🗑️ {filepath}\n")
                self.tools_output.append("=" * 50 + "\n")
                
            except Exception as e:
                self.tools_output.append(f"\n❌ Error deleting: {str(e)}\n")
                self.tools_output.append("=" * 50 + "\n")

    def rename_file(self):
        """Rename a file or folder"""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Rename", "", "All Files (*.*)")
        
        if not filepath:
            filepath = QFileDialog.getExistingDirectory(self, "Select Folder to Rename")
        
        if not filepath:
            return
        
        old_name = os.path.basename(filepath)
        new_name, ok = QInputDialog.getText(self, "Rename", f"Current name: {old_name}\nEnter new name:")
        
        if not ok or not new_name:
            return
        
        try:
            directory = os.path.dirname(filepath)
            new_path = os.path.join(directory, new_name)
            os.rename(filepath, new_path)
            
            self.tools_output.append(f"\n✅ Renamed successfully!\n")
            self.tools_output.append(f"Old: {old_name}\n")
            self.tools_output.append(f"New: {new_name}\n")
            self.tools_output.append("=" * 50 + "\n")
            
        except Exception as e:
            self.tools_output.append(f"\n❌ Error renaming: {str(e)}\n")
            self.tools_output.append("=" * 50 + "\n")

    def copy_file(self):
        """Copy a file"""
        source, _ = QFileDialog.getOpenFileName(self, "Select File to Copy", "", "All Files (*.*)")
        if not source:
            return
        
        destination = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if not destination:
            return
        
        try:
            filename = os.path.basename(source)
            dest_path = os.path.join(destination, filename)
            
            # Handle duplicate names
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(destination, f"{base}_copy{counter}{ext}")
                    counter += 1
            
            shutil.copy2(source, dest_path)
            
            self.tools_output.append(f"\n✅ File copied successfully!\n")
            self.tools_output.append(f"From: {source}\n")
            self.tools_output.append(f"To: {dest_path}\n")
            self.tools_output.append("=" * 50 + "\n")
            
        except Exception as e:
            self.tools_output.append(f"\n❌ Error copying file: {str(e)}\n")
            self.tools_output.append("=" * 50 + "\n")

    def move_file(self):
        """Move a file"""
        source, _ = QFileDialog.getOpenFileName(self, "Select File to Move", "", "All Files (*.*)")
        if not source:
            return
        
        destination = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if not destination:
            return
        
        try:
            filename = os.path.basename(source)
            dest_path = os.path.join(destination, filename)
            
            shutil.move(source, dest_path)
            
            self.tools_output.append(f"\n✅ File moved successfully!\n")
            self.tools_output.append(f"From: {source}\n")
            self.tools_output.append(f"To: {dest_path}\n")
            self.tools_output.append("=" * 50 + "\n")
            
        except Exception as e:
            self.tools_output.append(f"\n❌ Error moving file: {str(e)}\n")
            self.tools_output.append("=" * 50 + "\n")

    def read_file(self):
        """Read and display a text file"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Text File", "", 
            "Text Files (*.txt *.log *.md);;All Files (*.*)"
        )
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.tools_output.append(f"\n📄 Reading file: {os.path.basename(filepath)}\n")
            self.tools_output.append("=" * 50 + "\n")
            self.tools_output.append(content)
            self.tools_output.append("\n" + "=" * 50 + "\n")
            
        except Exception as e:
            self.tools_output.append(f"\n❌ Error reading file: {str(e)}\n")
            self.tools_output.append("=" * 50 + "\n")

    def list_directory(self):
        """List contents of a directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory to List")
        if not directory:
            return
        
        try:
            self.tools_output.append(f"\n📁 Contents of: {directory}\n")
            self.tools_output.append("=" * 50 + "\n")
            
            items = os.listdir(directory)
            
            folders = [item for item in items if os.path.isdir(os.path.join(directory, item))]
            files = [item for item in items if os.path.isfile(os.path.join(directory, item))]
            
            self.tools_output.append(f"\n📁 Folders ({len(folders)}):\n")
            for folder in sorted(folders):
                self.tools_output.append(f"  └─ 📁 {folder}\n")
            
            self.tools_output.append(f"\n📄 Files ({len(files)}):\n")
            for file in sorted(files):
                size = os.path.getsize(os.path.join(directory, file))
                size_str = self.format_size(size)
                self.tools_output.append(f"  └─ 📄 {file} ({size_str})\n")
            
            self.tools_output.append("\n" + "=" * 50 + "\n")
            
        except Exception as e:
            self.tools_output.append(f"\n❌ Error listing directory: {str(e)}\n")
            self.tools_output.append("=" * 50 + "\n")

    def format_size(self, size):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
        
        try:
            # Run ping command
            result = subprocess.run(
                ["ping", "8.8.8.8", "-n", "4"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Show output
            self.tools_output.append(result.stdout)
            
            if result.returncode == 0:
                self.tools_output.append("\n✅ Ping successful!\n")
            else:
                self.tools_output.append("\n❌ Ping failed!\n")
                
        except subprocess.TimeoutExpired:
            self.tools_output.append("\n⏱️ Ping timed out!\n")
        except Exception as e:
            self.tools_output.append(f"\n❌ Error: {str(e)}\n")
        
        self.tools_output.append("=" * 50 + "\n")

    def show_ipconfig(self):
        """Show IP configuration"""
        self.tools_output.append("\n💻 Getting IP Configuration...\n")
        self.tools_output.append("=" * 50 + "\n")
        
        try:
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            self.tools_output.append(result.stdout)
            
        except Exception as e:
            self.tools_output.append(f"\n❌ Error: {str(e)}\n")
        
        self.tools_output.append("=" * 50 + "\n")

    # -----------------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------------
    def show_settings(self):
        layout = QVBoxLayout()
        label = QLabel("Settings Panel (Coming Soon)")
        label.setStyleSheet("font-size: 22px;")
        layout.addWidget(label)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.pages_layout.addWidget(widget)

    def closeEvent(self, event):
        """Clean up when closing app"""
        self.cleanup_resources()
        cv2.destroyAllWindows()
        event.accept()


# -----------------------------------------------------------
# RUN APP
# -----------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())