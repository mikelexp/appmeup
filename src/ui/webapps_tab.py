from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config import WebAppConfig
from src.icons import app_icon, webapp_icon


def build_webapps_tab() -> tuple[QWidget, QListWidget, QLabel]:
    container = QWidget()
    layout = QVBoxLayout(container)

    actions_layout = QHBoxLayout()
    webapps_count_label = QLabel()
    actions_layout.addWidget(webapps_count_label, stretch=1)
    refresh_button = QPushButton("Refresh")
    actions_layout.addWidget(refresh_button)
    layout.addLayout(actions_layout)

    webapps_list = QListWidget()
    webapps_list.setSelectionMode(QAbstractItemView.SingleSelection)
    webapps_list.setSpacing(4)
    webapps_list.setContextMenuPolicy(Qt.CustomContextMenu)
    layout.addWidget(webapps_list)

    return container, webapps_list, webapps_count_label


def build_webapp_item_widget(config: WebAppConfig) -> QWidget:
    widget = QWidget()
    widget.setObjectName("WebAppItem")
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(12, 5, 12, 8)
    layout.setSpacing(12)

    icon_label = QLabel()
    icon_label.setFixedSize(48, 48)
    icon_label.setAlignment(Qt.AlignCenter)
    icon = webapp_icon(config.icon_path)
    pixmap = icon.pixmap(48, 48)
    if pixmap.isNull():
        pixmap = app_icon().pixmap(48, 48)
    icon_label.setPixmap(pixmap)
    layout.addWidget(icon_label)

    text_container = QWidget()
    text_layout = QVBoxLayout(text_container)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(2)

    title_label = QLabel(config.name or config.desktop_filename)
    title_label.setStyleSheet("font-weight: 600;")
    title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    text_layout.addWidget(title_label)

    detail_label = QLabel(config.url or config.desktop_path)
    detail_color = detail_label.palette().color(QPalette.WindowText)
    detail_color.setAlpha(180)
    detail_label.setStyleSheet(
        "color: rgba(%d, %d, %d, %d);" % (
            detail_color.red(),
            detail_color.green(),
            detail_color.blue(),
            detail_color.alpha(),
        )
    )
    detail_label.setWordWrap(True)
    detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    text_layout.addWidget(detail_label)

    layout.addWidget(text_container, stretch=1)

    open_button = QPushButton("Launch")
    layout.addWidget(open_button)

    return widget
