from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QGridLayout, QLabel, QHBoxLayout

from src.utils.const import Key
from ui.main_window.auto_clock_window import AutoClockPageContent, AutoClockContainer
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import CheckBox, LineEdit, PasswordLineEdit

class NotificationPage(AutoClockPageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(NotificationPage, self).__init__(y, x)

    def init_container(self):
        email = EmailContainer(6, 3)
        self.add_container(email, 0, 0)

        timing = SendTimeContainer(6, 2)
        self.add_container(timing, 3, 0)

        self.input_save_widget = [
            email.notification_email,
            email.smtp_server,
            email.smtp_port,
            email.sender_email,
            email.sender_auth_code,
            timing.send_email_failed,
            timing.send_email_success
        ]

class EmailContainer(AutoClockContainer):
    def __init__(self, x, y):
        super(EmailContainer, self).__init__(x, y)
        self.notification_email = LineEdit(Key.NotificationEmail)
        self.smtp_server = LineEdit(Key.SmtpServer)
        self.smtp_port = LineEdit(Key.SmtpPort)
        self.sender_email = LineEdit(Key.SenderEmail)
        self.sender_auth_code = PasswordLineEdit(Key.SenderAuthCode)

        self.init_ui_layout()

    def init_ui_layout(self):
        group_notification = QGroupBox("Email")
        group_notification.setStyleSheet(get_group_css({}))
        layout = QGridLayout(group_notification)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 18, 14, 14)

        for r, (label, widget) in enumerate([
            ("Notification Email:", self.notification_email),
            ("Sender Email:", self.sender_email),
            ("Auth Code:", self.sender_auth_code),
        ]):
            layout.addWidget(QLabel(label), r, 0)
            layout.addWidget(widget, r, 1)

        layout.addWidget(QLabel("SMTP Server:"), 3, 0)
        smtp_row = QHBoxLayout()
        smtp_row.addWidget(self.smtp_server, 1)
        smtp_row.addSpacing(4)
        smtp_row.addWidget(QLabel("Port:"))
        smtp_row.addSpacing(4)
        smtp_row.addWidget(self.smtp_port)
        layout.addLayout(smtp_row, 3, 1)

        layout.setColumnStretch(1, 1)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_notification)

class SendTimeContainer(AutoClockContainer):
    def __init__(self, x, y):
        super(SendTimeContainer, self).__init__(x, y)

        self.send_email_failed = CheckBox(Key.SendEmailWhenFailed)
        self.send_email_success = CheckBox(Key.SendEmailWhenSuccess)

        self.init_ui_layout()

    def init_ui_layout(self):
        group_notification = QGroupBox("Timing")
        group_notification.setStyleSheet(get_group_css({}))
        layout_notification = QVBoxLayout(group_notification)

        layout_send_email = QVBoxLayout()
        layout_send_email.addStretch()
        title = QLabel("Send Email When:")
        layout_send_email.addWidget(title)
        layout_send_email.addStretch()
        layout_send_email_checkbox = QHBoxLayout()
        layout_send_email_checkbox.addWidget(QLabel("Failed"))
        layout_send_email_checkbox.addWidget(self.send_email_failed)
        layout_send_email_checkbox.addWidget(QLabel("Success"))
        layout_send_email_checkbox.addWidget(self.send_email_success)
        layout_send_email.addLayout(layout_send_email_checkbox)
        layout_send_email.addStretch()

        layout_notification.addLayout(layout_send_email)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_notification)