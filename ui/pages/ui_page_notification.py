from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QGridLayout, QLabel, QHBoxLayout

from src.utils.const import Key
from ui.main_window.auto_clock_window import AutoClockPageContent, AutoClockContainer
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import CheckBox, LineEdit, PasswordLineEdit

_LABEL_STYLE = "color:#4b5563; font-size:13px;"


class NotificationPage(AutoClockPageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(NotificationPage, self).__init__(y, x)

    def init_container(self):
        email = EmailContainer(6, 3)
        self.add_container(email, 0, 0)

        timing = SendTimeContainer(3, 2)
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

        fields = [
            ("Notification Email:", self.notification_email),
            ("Sender Email:", self.sender_email),
            ("Auth Code:", self.sender_auth_code),
        ]
        for r, (text, widget) in enumerate(fields):
            lbl = QLabel(text)
            lbl.setStyleSheet(_LABEL_STYLE)
            layout.addWidget(lbl, r, 0)
            layout.addWidget(widget, r, 1)

        smtp_label = QLabel("SMTP Server:")
        smtp_label.setStyleSheet(_LABEL_STYLE)
        layout.addWidget(smtp_label, 3, 0)

        smtp_row = QHBoxLayout()
        smtp_row.setSpacing(6)
        smtp_row.addWidget(self.smtp_server, 1)
        port_label = QLabel("Port:")
        port_label.setStyleSheet(_LABEL_STYLE)
        smtp_row.addWidget(port_label)
        self.smtp_port.setFixedWidth(80)
        smtp_row.addWidget(self.smtp_port)
        layout.addLayout(smtp_row, 3, 1)

        layout.setColumnStretch(1, 1)
        layout.setColumnMinimumWidth(0, 140)

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
        layout_notification.setSpacing(8)
        layout_notification.setContentsMargins(14, 12, 14, 12)

        title = QLabel("Send Email When:")
        title.setStyleSheet("color:#374151; font-weight:600; font-size:13px;")
        layout_notification.addWidget(title)

        checkbox_row = QHBoxLayout()
        checkbox_row.setSpacing(16)

        for label_text, checkbox in [
            ("Failed", self.send_email_failed),
            ("Success", self.send_email_success),
        ]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color:#4b5563; font-size:13px;")
            checkbox_row.addWidget(lbl)
            checkbox_row.addWidget(checkbox)

        checkbox_row.addStretch()
        layout_notification.addLayout(checkbox_row)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_notification)
