import os
import json
import pygame
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QSlider, QSpinBox, QMessageBox, QHBoxLayout, QListWidget
)
from PySide6.QtCore import Qt, QTimer


class MP3Player(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MP3 Playlist Player")
        pygame.mixer.init()
        self.settings_file = "mp3_settings.json"
        self.playlist = []
        self.current_index = -1
        self.repeat_count = 1
        self.remaining_repeats = 0
        self.paused = False
        self.last_position = 0

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.check_playback)

        self.init_ui()
        self.load_saved_settings()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("No file selected")
        layout.addWidget(self.label)

        self.playlist_widget = QListWidget()
        self.playlist_widget.itemClicked.connect(self.select_from_list)
        layout.addWidget(self.playlist_widget)

        upload_btn = QPushButton("Add MP3(s) to Playlist")
        upload_btn.clicked.connect(self.upload_mp3s)
        layout.addWidget(upload_btn)

        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("Repeat Count:"))
        self.repeat_box = QSpinBox()
        self.repeat_box.setRange(1, 10)
        self.repeat_box.setValue(1)
        self.repeat_box.valueChanged.connect(lambda v: setattr(self, "repeat_count", v))
        repeat_layout.addWidget(self.repeat_box)

        self.remaining_label = QLabel("Remaining: 0")
        repeat_layout.addWidget(self.remaining_label)

        layout.addLayout(repeat_layout)

        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_mp3)
        btn_layout.addWidget(self.play_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_mp3)
        btn_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_mp3)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def upload_mp3s(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select MP3s", "", "MP3 Files (*.mp3)")
        for file_path in files:
            if file_path not in self.playlist:
                self.playlist.append(file_path)
                self.playlist_widget.addItem(os.path.basename(file_path))
        if self.current_index == -1 and self.playlist:
            self.select_track(0)

    def select_from_list(self, item):
        index = self.playlist_widget.row(item)
        self.select_track(index)

    def select_track(self, index):
        self.current_index = index
        self.label.setText(os.path.basename(self.playlist[index]))
        self.load_settings_for_file()
        self.remaining_repeats = self.repeat_count
        self.update_remaining_label()

    def play_mp3(self):
        if self.current_index == -1 or not self.playlist:
            QMessageBox.warning(self, "No Track", "Please select a file to play.")
            return

        file_path = self.playlist[self.current_index]
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Missing File", f"{file_path} not found.")
            return

        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play(start=self.last_position)
            self.paused = False
            self.timer.start()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def pause_mp3(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
        else:
            pygame.mixer.music.pause()
            self.paused = True

    def stop_mp3(self):
        self.last_position = pygame.mixer.music.get_pos() / 1000.0
        pygame.mixer.music.stop()
        self.timer.stop()
        self.paused = False
        self.save_last_position()
        self.update_remaining_label()

    def check_playback(self):
        if not pygame.mixer.music.get_busy() and not self.paused:
            if self.remaining_repeats > 1:
                self.remaining_repeats -= 1
                pygame.mixer.music.play()
                self.update_remaining_label()
            else:
                self.last_position = 0
                self.remaining_repeats = self.repeat_count
                self.timer.stop()
                self.save_last_position()
                self.next_track()

    def next_track(self):
        self.current_index += 1
        if self.current_index < len(self.playlist):
            self.playlist_widget.setCurrentRow(self.current_index)
            self.select_track(self.current_index)
            self.play_mp3()
        else:
            self.current_index = -1
            self.label.setText("Playlist finished")

    def update_remaining_label(self):
        self.remaining_label.setText(f"Remaining: {self.remaining_repeats}")

    def save_settings(self):
        if self.current_index == -1:
            return
        file_path = self.playlist[self.current_index]
        all_settings = self.load_all_settings()
        all_settings[file_path] = {
            "repeat": self.repeat_box.value(),
            "last_position": self.last_position
        }
        with open(self.settings_file, 'w') as f:
            json.dump(all_settings, f, indent=4)
        QMessageBox.information(self, "Saved", "Settings saved.")

    def save_last_position(self):
        if self.current_index == -1:
            return
        file_path = self.playlist[self.current_index]
        all_settings = self.load_all_settings()
        if file_path not in all_settings:
            all_settings[file_path] = {}
        all_settings[file_path]["last_position"] = self.last_position
        with open(self.settings_file, 'w') as f:
            json.dump(all_settings, f, indent=4)

    def load_settings_for_file(self):
        file_path = self.playlist[self.current_index]
        settings = self.load_all_settings()
        if file_path in settings:
            config = settings[file_path]
            self.repeat_box.setValue(config.get("repeat", 1))
            self.last_position = config.get("last_position", 0)
        else:
            self.last_position = 0

    def load_saved_settings(self):
        settings = self.load_all_settings()
        for path in settings.keys():
            if os.path.exists(path):
                self.playlist.append(path)
                self.playlist_widget.addItem(os.path.basename(path))
        if self.playlist:
            self.select_track(0)

    def load_all_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        return {}


if __name__ == "__main__":
    app = QApplication([])
    player = MP3Player()
    player.resize(500, 400)
    player.show()
    app.exec()
