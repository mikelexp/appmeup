from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from src.constants import ICON_PREVIEW_SIZE
from src.categories import collect_existing_categories


def build_basic_tab() -> tuple[QWidget, dict[str, QWidget]]:
    widgets: dict[str, QWidget] = {}

    container = QWidget()
    layout = QVBoxLayout(container)

    form_group = QGroupBox("Application")
    form = QFormLayout(form_group)

    name_input = QLineEdit()
    widgets["name_input"] = name_input
    form.addRow("Title", name_input)

    url_input = QLineEdit()
    widgets["url_input"] = url_input
    form.addRow("URL", url_input)

    comment_input = QLineEdit()
    widgets["comment_input"] = comment_input
    form.addRow("Description", comment_input)

    categories_row = QWidget()
    categories_layout = QHBoxLayout(categories_row)
    categories_layout.setContentsMargins(0, 0, 0, 0)
    categories_select = QComboBox()
    categories_select.addItem("Select a category\u2026")
    categories_select.addItems(collect_existing_categories())
    widgets["categories_select"] = categories_select
    categories_layout.addWidget(categories_select)
    categories_input = QLineEdit()
    categories_input.setPlaceholderText("Network;WebBrowser;")
    widgets["categories_input"] = categories_input
    categories_layout.addWidget(categories_input, stretch=1)
    form.addRow("Categories", categories_row)

    filename_row = QWidget()
    filename_layout = QHBoxLayout(filename_row)
    filename_layout.setContentsMargins(0, 0, 0, 0)
    filename_input = QLineEdit()
    widgets["filename_input"] = filename_input
    filename_layout.addWidget(filename_input)
    open_folder_button = QPushButton("Open Folder")
    widgets["open_folder_button"] = open_folder_button
    filename_layout.addWidget(open_folder_button)
    form.addRow(".desktop Filename", filename_row)

    chromium_row = QWidget()
    chromium_layout = QHBoxLayout(chromium_row)
    chromium_layout.setContentsMargins(0, 0, 0, 0)
    chromium_input = QLineEdit()
    widgets["chromium_input"] = chromium_input
    chromium_layout.addWidget(chromium_input)
    chromium_detect_button = QPushButton("Detect")
    widgets["chromium_detect_button"] = chromium_detect_button
    chromium_layout.addWidget(chromium_detect_button)
    form.addRow("Browser Executable", chromium_row)

    icon_row = QWidget()
    icon_layout = QHBoxLayout(icon_row)
    icon_layout.setContentsMargins(0, 0, 0, 0)
    icon_input = QLineEdit()
    widgets["icon_input"] = icon_input
    icon_layout.addWidget(icon_input)
    browse_icon_button = QPushButton("Browse")
    widgets["browse_icon_button"] = browse_icon_button
    icon_layout.addWidget(browse_icon_button)
    fetch_icon_button = QPushButton("Fetch")
    widgets["fetch_icon_button"] = fetch_icon_button
    icon_layout.addWidget(fetch_icon_button)
    form.addRow("Icon", icon_row)

    ignore_icon_ssl_errors_check = QCheckBox()
    ignore_icon_ssl_errors_check.setText("")
    widgets["ignore_icon_ssl_errors_check"] = ignore_icon_ssl_errors_check
    form.addRow("Ignore SSL errors when fetching icon", ignore_icon_ssl_errors_check)

    icon_preview_label = QLabel("No icon")
    icon_preview_label.setAlignment(Qt.AlignCenter)
    icon_preview_label.setFixedSize(ICON_PREVIEW_SIZE + 16, ICON_PREVIEW_SIZE + 16)
    icon_preview_label.setStyleSheet("QLabel { border: 1px solid palette(mid); padding: 4px; }")
    widgets["icon_preview_label"] = icon_preview_label
    form.addRow("Preview", icon_preview_label)

    layout.addWidget(form_group)

    return container, widgets
