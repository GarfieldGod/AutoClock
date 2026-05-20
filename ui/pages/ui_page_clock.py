from PyQt5.QtWidgets import QWidget, QLineEdit, QPushButton, QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, \
    QApplication

from src.utils.const import Key
from ui.main_window.auto_clock_window import AutoClockPageContent, AutoClockContainer
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import LineEdit, CheckBox
from src.ui.ui_message import MessageBox
from src.utils.log import Log
from src.utils.utils import Utils

class ClockPage(AutoClockPageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(ClockPage, self).__init__(y, x)

    def init_container(self):
        user_width = 3
        user_height = 2
        user = UserInfoContainer(user_width, user_height)
        self.add_container(user, 0, 0)

        cap = CaptchaContainer(3, user_height)
        self.add_container(cap, 0, user_width)

        web = WebDriverContainer(6, 2)
        self.add_container(web, user_height, 0)

        self.input_save_widget = [
            user.user_name,
            user.user_password,

            cap.captcha_retry_times,
            cap.captcha_tolerance_angle,
            cap.always_retry_check_box,
            cap.show_web_page,

            web.driver_path
        ]


class UserInfoContainer(AutoClockContainer):
    def __init__(self, x, y):
        super(UserInfoContainer, self).__init__(x, y)
        self.global_layout = QVBoxLayout()

        self.user_name = LineEdit(Key.UserName)
        self.user_password = LineEdit(Key.UserPassword)
        self.user_password.setEchoMode(QLineEdit.Password)
        self.show_password_btn = QPushButton()

        self.init_ui_format()
        self.init_ui_layout()

    def init_ui_format(self):
        self.show_password_btn.setFixedSize(28, 28)
        self.show_password_btn.setStyleSheet("border: none; background-color: transparent; padding:0; font-size:18px;")

        self.show_password_btn.setText("🔒")
        self.show_password_btn.setToolTip("显示密码")
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)

    def init_ui_layout(self):
        group_user = QGroupBox("Login")
        group_user.setStyleSheet(get_group_css({"Text_Color": "#D32F2F"}))

        layout_username = QVBoxLayout()
        layout_username.addWidget(QLabel("UserName:"))
        layout_username.addWidget(self.user_name)

        password_input_layout = QHBoxLayout()
        password_input_layout.addWidget(self.user_password)
        password_input_layout.addWidget(self.show_password_btn)
        password_input_layout.setContentsMargins(0, 0, 0, 0)

        layout_password = QVBoxLayout()
        layout_password.addWidget(QLabel("Password:"))
        layout_password.addLayout(password_input_layout)

        layout_user = QVBoxLayout()
        layout_user.addLayout(layout_username)
        layout_user.addLayout(layout_password)

        layout_function = QVBoxLayout(group_user)
        layout_function.addLayout(layout_user)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_user)

    def toggle_password_visibility(self):
        if self.user_password.echoMode() == QLineEdit.Password:
            self.user_password.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setText("👁")
            self.show_password_btn.setToolTip("隐藏密码")
        else:
            self.user_password.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setText("🔒")
            self.show_password_btn.setToolTip("显示密码")

class WebDriverContainer(AutoClockContainer):
    def __init__(self, x, y):
        super(WebDriverContainer, self).__init__(x, y)

        self.driver_path = LineEdit(Key.DriverPath)
        self.download_driver_btn = QPushButton()

        self.init_ui_format()
        self.init_ui_layout()

    def init_ui_format(self):
        self.download_driver_btn.setFixedSize(28, 28)
        self.download_driver_btn.setStyleSheet("border: none; background-color: transparent; padding:0; font-size:18px;")
        self.download_driver_btn.setText("⬇")
        self.download_driver_btn.setToolTip("自动下载匹配Driver")
        self.download_driver_btn.clicked.connect(self.download_driver)

    def init_ui_layout(self):
        group_driver = QGroupBox("Driver")
        group_driver.setStyleSheet(get_group_css({}))

        driver_input_layout = QHBoxLayout()
        driver_input_layout.addWidget(self.driver_path)
        driver_input_layout.addWidget(self.download_driver_btn)
        driver_input_layout.setContentsMargins(0, 0, 0, 0)

        layout_driver = QVBoxLayout(group_driver)
        layout_driver.addWidget(QLabel("Edge Driver Path:"))
        layout_driver.addLayout(driver_input_layout)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_driver)

    def download_driver(self):
        try:
            self.download_driver_btn.setEnabled(False)
            self.download_driver_btn.setText("⏳")
            self.download_driver_btn.setToolTip("正在下载...")

            QApplication.processEvents()
            Log.info("开始手动下载Edge Driver...")
            w = self.window()
            if hasattr(w, "is_remote_connected") and w.is_remote_connected() and hasattr(w, "ensure_remote_driver"):
                ok, result = w.ensure_remote_driver()
            else:
                ok, result = Utils.download_edge_web_driver()

            if ok:
                self.driver_path.setText(result)
                MessageBox(f"Driver下载成功！\n路径: {result}")
                Log.info(f"Driver下载成功: {result}")
            else:
                MessageBox(f"Driver下载失败！\n错误: {result}")
                Log.error(f"Driver下载失败: {result}")
        except Exception as e:
            MessageBox(f"Driver下载过程中发生异常！\n错误: {str(e)}")
            Log.error(f"Driver下载异常: {str(e)}")
        finally:
            self.download_driver_btn.setEnabled(True)
            self.download_driver_btn.setText("⬇")
            self.download_driver_btn.setToolTip("自动下载匹配Driver")

class CaptchaContainer(AutoClockContainer):
    def __init__(self, x, y):
        super(CaptchaContainer, self).__init__(x, y)

        self.captcha_retry_times = LineEdit(Key.CaptchaRetryTimes, default="5")
        self.captcha_tolerance_angle = LineEdit(Key.CaptchaToleranceAngle, default="5")

        self.always_retry_check_box = CheckBox(Key.AlwaysRetry)
        self.show_web_page = CheckBox(Key.ShowWebPage)

        self.init_ui_layout()

    def init_ui_layout(self):
        group_captcha = QGroupBox("Captcha")
        group_captcha.setStyleSheet(get_group_css({}))
        layout_group = QVBoxLayout(group_captcha)

        widget_retry_a = QWidget()
        layout_retry_a = QVBoxLayout(widget_retry_a)
        layout_retry_a.setContentsMargins(0, 0, 0, 0)
        layout_retry_a.addWidget(QLabel("Retry Times:"))
        layout_retry_a.addWidget(self.captcha_retry_times)

        widget_retry_b = QWidget()
        layout_retry_b = QVBoxLayout(widget_retry_b)
        layout_retry_b.setContentsMargins(0, 0, 0, 0)
        layout_retry_b.addWidget(QLabel("Always Retry:"))
        layout_retry_b.addWidget(self.always_retry_check_box)

        widget_retry_c = QWidget()
        layout_retry_c = QVBoxLayout(widget_retry_c)
        layout_retry_c.setContentsMargins(0, 0, 0, 0)
        layout_retry_c.addWidget(QLabel("Tolerance Angle:"))
        layout_retry_c.addWidget(self.captcha_tolerance_angle)

        widget_retry_d = QWidget()
        layout_retry_d = QVBoxLayout(widget_retry_d)
        layout_retry_d.setContentsMargins(0, 0, 0, 0)
        layout_retry_d.addWidget(QLabel("Show Web:"))
        layout_retry_d.addWidget(self.show_web_page)

        layout_retry_input = QHBoxLayout()
        layout_retry_input.setContentsMargins(0, 0, 0, 0)
        layout_retry_input.addWidget(widget_retry_a)
        layout_retry_input.addWidget(widget_retry_c)

        layout_retry_checkbox = QHBoxLayout()
        layout_retry_checkbox.setContentsMargins(0, 0, 0, 0)
        layout_retry_checkbox.addWidget(widget_retry_b)
        layout_retry_checkbox.addWidget(widget_retry_d)

        layout_group.addLayout(layout_retry_checkbox)
        layout_group.addLayout(layout_retry_input)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_captcha)