from PyQt5.QtWidgets import QLineEdit, QCheckBox, QGroupBox, QVBoxLayout, QLabel, QHBoxLayout

from ui.pages.custom_style import get_group_css
from ui.template.ui_page import PageContent, Container

class NotificationPage(PageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(NotificationPage, self).__init__(y, x)

    def init_container(self):
        email = EmailContainer(3, 2)
        self.add_container(email, 0,0)

        timing = SendTimeContainer(3,2)
        self.add_container(timing, 2,0)

class EmailContainer(Container):
    def __init__(self, x, y):
        super(EmailContainer, self).__init__(x, y)
        self.notification_email = QLineEdit()

        self.init_ui_layout()

    def init_ui_layout(self):
        group_notification = QGroupBox("Email")
        group_notification.setStyleSheet(get_group_css({}))
        layout_notification = QVBoxLayout(group_notification)

        layout_email = QVBoxLayout()
        layout_email.addWidget(QLabel("Notification Email:"))
        layout_email.addWidget(self.notification_email)

        layout_notification.addLayout(layout_email)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_notification)

class SendTimeContainer(Container):
    def __init__(self, x, y):
        super(SendTimeContainer, self).__init__(x, y)

        self.send_email_failed = QCheckBox()
        self.send_email_success = QCheckBox()

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