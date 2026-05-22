from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QLineEdit, QWidget, QSizePolicy,
)


class DailyAuthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Daily Report Authorization")
        self.setFixedSize(420, 540)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_qr_page())
        self.stack.addWidget(self._build_phone_page())
        self.stack.addWidget(self._build_success_page())
        layout.addWidget(self.stack, 1)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setStyleSheet(
            "QPushButton { background: #6b7280; color: white; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; }"
            "QPushButton:hover { background: #4b5563; }"
        )
        self._cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self._cancel_btn, 0, Qt.AlignCenter)

        self._phone = None
        self._code = None
        self._qr_png = None
        self._pending_qr_switch = False
        self._preferred_page = "qr"
        self._send_code_countdown = 0
        self._send_code_timer = QTimer(self)
        self._send_code_timer.setInterval(1000)
        self._send_code_timer.timeout.connect(self._tick_send_code_countdown)
        self._on_phone_submit_cb = None
        self._on_code_submit_cb = None
        self._on_switch_phone_cb = None
        self._on_switch_qr_cb = None
        self._on_cancel_cb = None

    # ── Page builders ─────────────────────────────────

    def _build_qr_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        self._qr_loading = QLabel("Loading QR code...")
        self._qr_loading.setAlignment(Qt.AlignCenter)
        self._qr_loading.setStyleSheet(
            "color: #9ca3af; font-size: 14px; padding: 60px; "
            "border: 2px dashed #d1d5db; border-radius: 8px;"
        )
        layout.addWidget(self._qr_loading)

        self._qr_image = QLabel()
        self._qr_image.setAlignment(Qt.AlignCenter)
        self._qr_image.setFixedSize(240, 240)
        self._qr_image.setStyleSheet("border: none;")
        self._qr_image.hide()
        layout.addWidget(self._qr_image)

        hint = QLabel("Scan the QR code with your phone (Feishu App)")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(hint)

        self._phone_switch_btn = QPushButton("Use Phone Login")
        self._phone_switch_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #2563eb; border: none; "
            "font-size: 13px; }"
            "QPushButton:hover { color: #1d4ed8; text-decoration: underline; }"
        )
        self._phone_switch_btn.clicked.connect(self._on_switch_phone_click)
        layout.addWidget(self._phone_switch_btn, 0, Qt.AlignCenter)

        return page

    def _build_phone_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        layout.addStretch()

        layout.addWidget(QLabel("Phone Number:"))
        self._phone_input = QLineEdit()
        self._phone_input.setPlaceholderText("Enter phone number")
        self._phone_input.setStyleSheet(
            "border: 1px solid #d1d5db; border-radius: 4px; padding: 6px 10px; font-size: 14px;"
        )
        layout.addWidget(self._phone_input)

        self._send_code_btn = QPushButton("Send Code")
        self._send_code_btn.setStyleSheet(
            "QPushButton { background: #2563eb; color: white; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; }"
            "QPushButton:hover { background: #1d4ed8; }"
            "QPushButton:disabled { background: #93c5fd; }"
        )
        self._send_code_btn.clicked.connect(self._on_send_code)
        layout.addWidget(self._send_code_btn, 0, Qt.AlignCenter)

        layout.addSpacing(20)

        layout.addWidget(QLabel("Verification Code:"))
        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("Enter verification code")
        self._code_input.setStyleSheet(
            "border: 1px solid #d1d5db; border-radius: 4px; padding: 6px 10px; font-size: 14px;"
        )
        layout.addWidget(self._code_input)

        self._verify_btn = QPushButton("Verify")
        self._verify_btn.setStyleSheet(
            "QPushButton { background: #16a34a; color: white; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; }"
            "QPushButton:hover { background: #15803d; }"
            "QPushButton:disabled { background: #86efac; }"
        )
        self._verify_btn.clicked.connect(self._on_verify)
        layout.addWidget(self._verify_btn, 0, Qt.AlignCenter)

        layout.addStretch()

        self._back_qr_btn = QPushButton("< Back to QR Code")
        self._back_qr_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #2563eb; border: none; "
            "font-size: 13px; }"
            "QPushButton:hover { color: #1d4ed8; }"
        )
        self._back_qr_btn.clicked.connect(self._on_switch_qr_click)
        layout.addWidget(self._back_qr_btn, 0, Qt.AlignCenter)

        return page

    def _build_success_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("Authorization Successful!")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #16a34a; font-size: 18px; font-weight: 600;")
        layout.addWidget(label)

        return page

    # ── Public API ────────────────────────────────────

    def set_callbacks(self, on_phone_submit=None, on_code_submit=None,
                      on_switch_phone=None, on_switch_qr=None,
                      on_cancel=None):
        self._on_phone_submit_cb = on_phone_submit
        self._on_code_submit_cb = on_code_submit
        self._on_switch_phone_cb = on_switch_phone
        self._on_switch_qr_cb = on_switch_qr
        self._on_cancel_cb = on_cancel

    def show_qr_loading(self):
        self._qr_loading.show()
        self._qr_image.hide()
        if self._preferred_page != "phone":
            self.stack.setCurrentIndex(0)

    def show_qr_code(self, png_bytes):
        self._pending_qr_switch = False
        self._qr_png = png_bytes
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes)
        scaled = pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._qr_image.setPixmap(scaled)
        self._qr_image.show()
        self._qr_loading.hide()
        if self._preferred_page != "phone":
            self.stack.setCurrentIndex(0)

    def show_phone_input(self):
        self._preferred_page = "phone"
        if self._pending_qr_switch:
            return
        self.stack.setCurrentIndex(1)

    def show_code_input(self):
        self._preferred_page = "phone"
        if self._send_code_countdown <= 0:
            self._start_send_code_countdown(60)
        self.stack.setCurrentIndex(1)

    def show_success(self):
        self._preferred_page = "success"
        self.stack.setCurrentIndex(2)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, self.accept)

    def show_error(self, msg):
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Authorization Failed", msg)
        self.reject()

    def reset(self):
        self._phone = None
        self._code = None
        self._qr_png = None
        self._phone_input.clear()
        self._code_input.clear()
        self._stop_send_code_countdown()
        self._verify_btn.setEnabled(True)
        self._verify_btn.setText("Verify")
        self._preferred_page = "qr"
        self.show_qr_loading()

    def _start_send_code_countdown(self, seconds):
        self._send_code_countdown = max(0, int(seconds))
        self._update_send_code_button()
        if self._send_code_countdown > 0:
            self._send_code_timer.start()

    def _stop_send_code_countdown(self):
        self._send_code_timer.stop()
        self._send_code_countdown = 0
        self._update_send_code_button()

    def _tick_send_code_countdown(self):
        if self._send_code_countdown > 0:
            self._send_code_countdown -= 1
        if self._send_code_countdown <= 0:
            self._send_code_timer.stop()
        self._update_send_code_button()

    def _update_send_code_button(self):
        if self._send_code_countdown > 0:
            self._send_code_btn.setEnabled(False)
            self._send_code_btn.setText(f"Send Code ({self._send_code_countdown})")
        else:
            self._send_code_btn.setEnabled(True)
            self._send_code_btn.setText("Send Code")

    # ── Internal handlers ─────────────────────────────

    def _on_switch_phone_click(self):
        self._preferred_page = "phone"
        if self._on_switch_phone_cb:
            self._on_switch_phone_cb()
        self.show_phone_input()

    def _on_switch_qr_click(self):
        self._preferred_page = "qr"
        self._pending_qr_switch = True
        self.show_qr_loading()
        if self._on_switch_qr_cb:
            self._on_switch_qr_cb()

    def _on_send_code(self):
        phone = self._phone_input.text().strip()
        if not phone:
            return
        self._send_code_btn.setEnabled(False)
        self._send_code_btn.setText("Sending...")
        if self._on_phone_submit_cb:
            self._on_phone_submit_cb(phone)

    def _on_verify(self):
        code = self._code_input.text().strip()
        if not code:
            return
        self._verify_btn.setEnabled(False)
        self._verify_btn.setText("Verifying...")
        if self._on_code_submit_cb:
            self._on_code_submit_cb(code)

    def _on_cancel(self):
        self._send_code_timer.stop()
        if self._on_cancel_cb:
            self._on_cancel_cb()
        self.reject()
