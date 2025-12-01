from PyQt5.QtCore import Qt, QRectF, QSizeF, QPropertyAnimation, QSize
from PyQt5.QtGui import QPainter, QPainterPath, QColor
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QGridLayout, QSizePolicy, QStackedWidget

from ui.template.ui_custom_color import CustomColor

class PageNavigation(QWidget):
    round_radius = 15
    bg_color = CustomColor.dark_87_90_95
    selected_color = CustomColor.white_253_254_249
    unselected_color = CustomColor.dark_87_90_95
    normal_color = QColor(255, 100, 255)
    hover_color = QColor(255, 255, 100)

    def __init__(self, name="",ico=""):
        super(PageNavigation, self).__init__()

        self.name = name
        self.ico = ico

        self.content = QStackedWidget()
        self.name_label = QLabel()
        self.ico_label = QLabel()

        self.init_ui()

    def init_ui(self):
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setText(self.name)
        self.name_label.setObjectName("navigation_text")
        self.ico_label.setText(f"Icon_{self.name}")

        self.content.addWidget(self.ico_label)
        self.content.addWidget(self.name_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

        self.show_not_clicked()

    # def enterEvent(self, event):
    #     try:
    #         # hover时启动颜色动画：从默认色→hover色
    #         self.anim = QPropertyAnimation(self, b"color")
    #         self.anim.setDuration(200)
    #         self.anim.setStartValue(self.normal_color)
    #         self.anim.setEndValue(self.hover_color)
    #         self.anim.start()
    #         super().enterEvent(event)
    #     except Exception as e:
    #         print(e)
    #
    # def leaveEvent(self, event):
    #     try:
    #         # 离开时启动颜色动画：从hover色→默认色
    #         self.anim = QPropertyAnimation(self, b"color")
    #         self.anim.setDuration(200)
    #         self.anim.setStartValue(self.hover_color)
    #         self.anim.setEndValue(self.normal_color)
    #         self.anim.start()
    #         super().leaveEvent(event)
    #     except Exception as e:
    #         print(e)

    def set_radius(self, radius):
        self.round_radius = radius
        self.update()

    def set_background_color(self, color=None):
        self.bg_color = color
        self.update()

    def show_not_clicked(self):
        self.content.setCurrentIndex(0)

    def show_clicked(self):
        self.content.setCurrentIndex(1)

    # def selected(self):
    #     self.selected_color = self.selected_color
    #     self.update()
    #
    # def unselected(self):
    #     self.unselected_color = self.unselected_color
    #     self.update()

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(Qt.NoPen)

            rect = QRectF(self.rect())
            radius = self.round_radius

            path = QPainterPath()
            path.moveTo(rect.topRight())
            path.lineTo(rect.bottomRight())
            # 左下角圆角
            path.lineTo(rect.bottomLeft().x() + radius, rect.bottomLeft().y())
            path.arcTo(QRectF(rect.bottomLeft().x(), rect.bottomLeft().y()-radius*2, radius*2, radius*2), 270, -90)
            # 左上角圆角
            path.lineTo(rect.topLeft().x(), rect.topLeft().y() - radius)
            path.arcTo(QRectF(rect.topLeft(), QSizeF(radius*2, radius*2)), 180.0, -90.0)
            path.lineTo(rect.topRight())
            path.closeSubpath()

            # 裁剪画布
            painter.setClipPath(path)
            painter.fillRect(rect, self.bg_color)
        except Exception as e:
            print(e)

class PageContent(QWidget):
    show_grid = False
    containers = []
    cell_size = 0
    page_spacing = 0

    def __init__(self, rows=6, columns=6):
        super(PageContent, self).__init__()
        self.rows = rows
        self.columns = columns

        self.grid = QGridLayout(self)
        self.grid.setSpacing(self.page_spacing)
        self.grid.setContentsMargins(0, 0, 0, 0)

        for row in range(self.rows):
            self.grid.setRowStretch(row, 1)
        for col in range(self.columns):
            self.grid.setColumnStretch(col, 1)

        content_width = self.size().width() - (self.columns - 1) * self.page_spacing
        content_height = self.size().height() - (self.rows - 1) * self.page_spacing
        self.cell_size = QSize(round(content_width / self.columns), round(content_height / self.rows))

        for r in range(self.rows):
            for c in range(self.columns):
                placeholder = QLabel(f"({r},{c})")
                if self.show_grid:
                    placeholder.setAlignment(Qt.AlignTop)
                    placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    placeholder.setStyleSheet("""
                         background-color: #f0f0f0;
                         border: 1px solid #cccccc;
                         color: #888888;
                     """)
                placeholder.setVisible(self.show_grid)
                self.grid.addWidget(placeholder, r, c)

        self.init_container()

    def add_container(self, container, pos_row, pos_col):
        if not isinstance(container, Container):
            print("This is not a Container")
        row_span = container.row
        col_span = container.col

        if not (0 <= pos_row < self.rows and 0 <= pos_col < self.columns):
            print(f"警告: 位置 ({pos_row}, {pos_col}) 超出网格范围 ({self.rows}x{self.columns})。")
            return
        if not (1 <= row_span <= self.rows - pos_row and 1 <= col_span <= self.columns - pos_col):
            print(f"警告: 跨度 ({row_span}x{col_span}) 在位置 ({pos_row}, {pos_col}) 处超出网格范围。剩余：高{self.rows - pos_row} 宽{self.columns - pos_col}。")
            return

        container.setSizePolicy(
            container.sizePolicy().horizontalPolicy() & ~container.sizePolicy().Expanding,
            container.sizePolicy().verticalPolicy() & ~container.sizePolicy().Expanding
        )
        container.setSizePolicy(
            container.sizePolicy().horizontalPolicy() | container.sizePolicy().Ignored,
            container.sizePolicy().verticalPolicy() | container.sizePolicy().Ignored
        )

        self.grid.addWidget(container, pos_row, pos_col, row_span, col_span)
        print(f"在第{pos_row}行，第{pos_col}列，新增container，占用{col_span}列（宽度 {container.size().width()}），{row_span}行（高度 {container.size().height()}）")
        self.containers.append(container)

    def init_container(self):
        pass

class Container(QWidget):
    round_radius = 25
    contents_margins = 10
    bg_color = CustomColor.white_253_254_249

    def __init__(self, width=2, height=2):
        super(Container, self).__init__()

        self.col = width
        self.row = height
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setContentsMargins(self.contents_margins, self.contents_margins, self.contents_margins, self.contents_margins)

    def init_ui(self):
        grid = QGridLayout(self)
        grid.setSpacing(0)
        grid.setContentsMargins(self.contents_margins, self.contents_margins, self.contents_margins, self.contents_margins)

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(Qt.NoPen)

            clip_path = QPainterPath()
            content_rect = QRectF(
                self.contents_margins, self.contents_margins,
                self.width() - 2 * self.contents_margins,
                self.height() - 2 * self.contents_margins
            )
            clip_path.addRect(content_rect)

            path = QPainterPath()
            path.addRoundedRect(
                QRectF(content_rect),
                self.round_radius,
                self.round_radius
            )
            painter.setClipPath(path)
            painter.fillRect(content_rect, self.bg_color)
        except Exception as e:
            print(e)