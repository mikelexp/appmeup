from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.constants import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    BROWSER_FLAG_HIDDEN,
    CHROMIUM_SWITCH_TOOLTIPS,
    ICON_DIR,
    ICON_PREVIEW_SIZE,
    USER_APPLICATIONS_DIR,
)
from src.utils import default_user_data_dir, slugify
from src.browser import detect_all_chromiums, detect_chromium, resolve_browser_identity, resolve_executable
from src.icons import app_asset_path, app_icon, fetch_icon_for_url, icon_slug_for_desktop_filename, store_icon_file, webapp_icon
from src.desktop_env import reveal_in_file_manager, run_refresh_commands
from src.categories import (
    append_category_value,
    collect_existing_categories,
    parse_categories,
    serialize_categories,
)
from src.config import WebAppConfig, collect_existing_webapps, load_desktop_file
from src.ui_fields import _UI_TEXT_FIELDS, _UI_CHECKBOX_FIELDS


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(800, 500)
        self._dirty = False
        self._filename_auto_sync = True
        self.current_config = WebAppConfig()
        self._chromium_rows: list[dict] = []
        self._chromium_groups: list[QGroupBox] = []
        self._current_browser = "Unknown"
        self._options_tab_index = 1
        self._fetched_icon_urls: set[str] = set()

        self._build_ui()
        self.load_config(self.current_config)
        self.refresh_webapps_list()
        self.statusBar().showMessage("Ready.")

    def _build_ui(self) -> None:
        self.setStatusBar(QStatusBar(self))

        file_menu = self.menuBar().addMenu("File")

        new_action = QAction("New WebApp", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_config)
        file_menu.addAction(new_action)

        save_action = QAction("Save WebApp", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_desktop)
        file_menu.addAction(save_action)

        help_menu = self.menuBar().addMenu("Help")
        website_action = QAction("Go to the app's website", self)
        website_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/mikelexp/appmeup")))
        help_menu.addAction(website_action)
        about_action = QAction("About AppMeUp!", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

        central = QWidget(self)
        outer_layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_basic_tab(), "Web App Options")
        self._options_tab_index = self.tabs.addTab(self._build_chromium_tab(), "Browser Options")
        self.webapps_tab = self._build_webapps_tab()
        self.tabs.addTab(self.webapps_tab, "Installed Web Apps")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setTabEnabled(self._options_tab_index, False)
        outer_layout.addWidget(self.tabs)

        actions_layout = QHBoxLayout()
        self.target_path_label = QLabel()
        self.target_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        actions_layout.addWidget(self.target_path_label, stretch=1)

        self.new_button = QPushButton("New WebApp")
        self.new_button.clicked.connect(self.new_config)
        actions_layout.addWidget(self.new_button)

        self.save_button = QPushButton("Save WebApp")
        self.save_button.clicked.connect(self.save_desktop)
        actions_layout.addWidget(self.save_button)
        outer_layout.addLayout(actions_layout)

        self.setCentralWidget(central)

    def _build_webapps_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        actions_layout = QHBoxLayout()
        self.webapps_count_label = QLabel()
        actions_layout.addWidget(self.webapps_count_label, stretch=1)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_webapps_list)
        actions_layout.addWidget(refresh_button)
        layout.addLayout(actions_layout)

        self.webapps_list = QListWidget()
        self.webapps_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.webapps_list.setSpacing(8)
        self.webapps_list.itemDoubleClicked.connect(self.open_webapp_list_item)
        self.webapps_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.webapps_list.customContextMenuRequested.connect(self._show_webapp_context_menu)
        layout.addWidget(self.webapps_list)

        return container

    def _build_basic_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        form_group = QGroupBox("Application")
        form = QFormLayout(form_group)

        self.name_input = QLineEdit()
        self.name_input.textEdited.connect(self._on_name_changed)
        form.addRow("Title", self.name_input)

        self.url_input = QLineEdit()
        self.url_input.textEdited.connect(self.mark_dirty)
        self.url_input.editingFinished.connect(self._on_url_edit_finished)
        form.addRow("URL", self.url_input)

        self.comment_input = QLineEdit()
        self.comment_input.textEdited.connect(self.mark_dirty)
        form.addRow("Description", self.comment_input)

        categories_row = QWidget()
        categories_layout = QHBoxLayout(categories_row)
        categories_layout.setContentsMargins(0, 0, 0, 0)
        self.categories_select = QComboBox()
        self.categories_select.addItem("Select a category\u2026")
        self.categories_select.addItems(collect_existing_categories())
        self.categories_select.currentIndexChanged.connect(self._on_category_selected)
        categories_layout.addWidget(self.categories_select)
        self.categories_input = QLineEdit()
        self.categories_input.setPlaceholderText("Network;WebBrowser;")
        self.categories_input.textEdited.connect(self.mark_dirty)
        categories_layout.addWidget(self.categories_input, stretch=1)
        form.addRow("Categories", categories_row)

        filename_row = QWidget()
        filename_layout = QHBoxLayout(filename_row)
        filename_layout.setContentsMargins(0, 0, 0, 0)
        self.filename_input = QLineEdit()
        self.filename_input.textEdited.connect(self._on_filename_changed)
        filename_layout.addWidget(self.filename_input)
        open_folder_button = QPushButton("Open Folder")
        open_folder_button.clicked.connect(self.open_desktop_folder)
        filename_layout.addWidget(open_folder_button)
        form.addRow(".desktop Filename", filename_row)

        chromium_row = QWidget()
        chromium_layout = QHBoxLayout(chromium_row)
        chromium_layout.setContentsMargins(0, 0, 0, 0)
        self.chromium_input = QLineEdit()
        self.chromium_input.textEdited.connect(self.mark_dirty)
        self.chromium_input.textEdited.connect(self._update_browser_ui)
        chromium_layout.addWidget(self.chromium_input)
        chromium_detect_button = QPushButton("Detect")
        chromium_detect_button.clicked.connect(self.detect_chromium_path)
        chromium_layout.addWidget(chromium_detect_button)
        form.addRow("Browser Executable", chromium_row)

        icon_row = QWidget()
        icon_layout = QHBoxLayout(icon_row)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_input = QLineEdit()
        self.icon_input.textEdited.connect(self.mark_dirty)
        self.icon_input.textChanged.connect(self.update_icon_preview)
        icon_layout.addWidget(self.icon_input)
        browse_icon_button = QPushButton("Browse")
        browse_icon_button.clicked.connect(self.choose_icon_file)
        icon_layout.addWidget(browse_icon_button)
        fetch_icon_button = QPushButton("Fetch")
        fetch_icon_button.clicked.connect(self.fetch_icon)
        icon_layout.addWidget(fetch_icon_button)
        form.addRow("Icon", icon_row)

        self.ignore_icon_ssl_errors_check = self._check_box("Ignore SSL certificate errors when fetching icons")
        form.addRow("Ignore SSL errors when fetching icon", self.ignore_icon_ssl_errors_check)

        self.icon_preview_label = QLabel("No icon")
        self.icon_preview_label.setAlignment(Qt.AlignCenter)
        self.icon_preview_label.setFixedSize(ICON_PREVIEW_SIZE + 16, ICON_PREVIEW_SIZE + 16)
        self.icon_preview_label.setStyleSheet("QLabel { border: 1px solid palette(mid); padding: 4px; }")
        form.addRow("Preview", self.icon_preview_label)

        layout.addWidget(form_group)

        return container

    def _build_chromium_tab(self) -> QWidget:
        container = QWidget()
        self._chromium_rows.clear()
        self._chromium_groups.clear()

        search_layout = QHBoxLayout()
        self.chromium_search_input = QLineEdit()
        self.chromium_search_input.setPlaceholderText("Search parameters and tooltips...")
        self.chromium_search_input.textChanged.connect(self._filter_chromium)
        search_layout.addWidget(QLabel("Filter:"))
        search_layout.addWidget(self.chromium_search_input, stretch=1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        app_group = self._chromium_group("App And Window")
        app_grid = app_group.layout()
        self.app_id_input = self._line_edit()
        self._add_chromium_row(app_group, app_grid, 0, "app-id", self.app_id_input)
        self.app_launch_url_input = self._line_edit()
        self._add_chromium_row(app_group, app_grid, 1, "app-launch-url-for-shortcuts-menu-item", self.app_launch_url_input)
        self.wm_class_input = self._line_edit()
        self._add_chromium_row(app_group, app_grid, 2, "class", self.wm_class_input)
        self.guest_check = self._check_box()
        self._add_chromium_check(app_group, app_grid, 3, "guest", self.guest_check)
        self.incognito_check = self._check_box()
        self._add_chromium_check(app_group, app_grid, 4, "incognito", self.incognito_check)
        self.kiosk_check = self._check_box()
        self._add_chromium_check(app_group, app_grid, 5, "kiosk", self.kiosk_check)
        self.wm_name_input = self._line_edit()
        self._add_chromium_row(app_group, app_grid, 6, "name", self.wm_name_input)
        self.new_window_check = self._check_box()
        self._add_chromium_check(app_group, app_grid, 7, "new-window", self.new_window_check)
        self.no_first_run_check = self._check_box()
        self._add_chromium_check(app_group, app_grid, 8, "no-first-run", self.no_first_run_check)
        self.start_fullscreen_check = self._check_box()
        self._add_chromium_check(app_group, app_grid, 9, "start-fullscreen", self.start_fullscreen_check)
        self.start_maximized_check = self._check_box()
        self._add_chromium_check(app_group, app_grid, 10, "start-maximized", self.start_maximized_check)
        self.window_position_input = self._line_edit("50,50")
        self._add_chromium_row(app_group, app_grid, 11, "window-position", self.window_position_input)
        self.window_size_input = self._line_edit("1280,800")
        self._add_chromium_row(app_group, app_grid, 12, "window-size", self.window_size_input)
        inner_layout.addWidget(app_group)

        identity_group = self._chromium_group("Identity And Profile")
        identity_grid = identity_group.layout()
        self.disable_features_input = self._line_edit()
        self._add_chromium_row(identity_group, identity_grid, 0, "disable-features", self.disable_features_input)
        self.enable_features_input = self._line_edit()
        self._add_chromium_row(identity_group, identity_grid, 1, "enable-features", self.enable_features_input)
        self.lang_input = self._line_edit("en-US")
        self._add_chromium_row(identity_group, identity_grid, 2, "lang", self.lang_input)
        self.profile_directory_input = self._line_edit("Default")
        self._add_chromium_row(identity_group, identity_grid, 3, "profile-directory", self.profile_directory_input)
        self.user_data_dir_input = self._path_row_button("Browse", self.choose_user_data_dir)
        self._add_chromium_row(identity_group, identity_grid, 4, "user-data-dir", self.user_data_dir_input["widget"])
        self.user_agent_input = self._line_edit()
        self._add_chromium_row(identity_group, identity_grid, 5, "user-agent", self.user_agent_input)
        inner_layout.addWidget(identity_group)

        rendering_group = self._chromium_group("Rendering And Performance")
        rendering_grid = rendering_group.layout()
        self.autoplay_policy_input = self._line_edit()
        self._add_chromium_row(rendering_group, rendering_grid, 0, "autoplay-policy", self.autoplay_policy_input)
        self.disable_dev_shm_usage_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 1, "disable-dev-shm-usage", self.disable_dev_shm_usage_check)
        self.disable_extensions_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 2, "disable-extensions", self.disable_extensions_check)
        self.disable_gpu_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 3, "disable-gpu", self.disable_gpu_check)
        self.disable_renderer_backgrounding_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 4, "disable-renderer-backgrounding", self.disable_renderer_backgrounding_check)
        self.disable_software_rasterizer_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 5, "disable-software-rasterizer", self.disable_software_rasterizer_check)
        self.disk_cache_dir_input = self._line_edit()
        self._add_chromium_row(rendering_group, rendering_grid, 6, "disk-cache-dir", self.disk_cache_dir_input)
        self.disk_cache_size_input = self._line_edit()
        self._add_chromium_row(rendering_group, rendering_grid, 7, "disk-cache-size", self.disk_cache_size_input)
        self.force_device_scale_factor_input = self._line_edit("1.0")
        self._add_chromium_row(rendering_group, rendering_grid, 8, "force-device-scale-factor", self.force_device_scale_factor_input)
        self.headless_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 9, "headless", self.headless_check)
        self.mute_audio_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 10, "mute-audio", self.mute_audio_check)
        self.ozone_platform_hint_input = self._line_edit("auto")
        self._add_chromium_row(rendering_group, rendering_grid, 11, "ozone-platform-hint", self.ozone_platform_hint_input)
        self.process_per_site_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 12, "process-per-site", self.process_per_site_check)
        self.single_process_check = self._check_box()
        self._add_chromium_check(rendering_group, rendering_grid, 13, "single-process", self.single_process_check)
        self.use_gl_input = self._line_edit()
        self._add_chromium_row(rendering_group, rendering_grid, 14, "use-gl", self.use_gl_input)
        self.virtual_time_budget_input = self._line_edit()
        self._add_chromium_row(rendering_group, rendering_grid, 15, "virtual-time-budget", self.virtual_time_budget_input)
        inner_layout.addWidget(rendering_group)

        network_group = self._chromium_group("Network And Security")
        network_grid = network_group.layout()
        self.allow_insecure_localhost_check = self._check_box()
        self._add_chromium_check(network_group, network_grid, 0, "allow-insecure-localhost", self.allow_insecure_localhost_check)
        self.disable_background_networking_check = self._check_box()
        self._add_chromium_check(network_group, network_grid, 1, "disable-background-networking", self.disable_background_networking_check)
        self.disable_notifications_check = self._check_box()
        self._add_chromium_check(network_group, network_grid, 2, "disable-notifications", self.disable_notifications_check)
        self.disable_popup_blocking_check = self._check_box()
        self._add_chromium_check(network_group, network_grid, 3, "disable-popup-blocking", self.disable_popup_blocking_check)
        self.disable_web_security_check = self._check_box()
        self._add_chromium_check(network_group, network_grid, 4, "disable-web-security", self.disable_web_security_check)
        self.host_resolver_rules_input = self._line_edit()
        self._add_chromium_row(network_group, network_grid, 5, "host-resolver-rules", self.host_resolver_rules_input)
        self.ignore_certificate_errors_check = self._check_box()
        self._add_chromium_check(network_group, network_grid, 6, "ignore-certificate-errors", self.ignore_certificate_errors_check)
        self.no_sandbox_check = self._check_box()
        self._add_chromium_check(network_group, network_grid, 7, "no-sandbox", self.no_sandbox_check)
        self.proxy_bypass_input = self._line_edit()
        self._add_chromium_row(network_group, network_grid, 8, "proxy-bypass-list", self.proxy_bypass_input)
        self.proxy_pac_url_input = self._line_edit()
        self._add_chromium_row(network_group, network_grid, 9, "proxy-pac-url", self.proxy_pac_url_input)
        self.proxy_server_input = self._line_edit()
        self._add_chromium_row(network_group, network_grid, 10, "proxy-server", self.proxy_server_input)
        inner_layout.addWidget(network_group)

        debug_group = self._chromium_group("Debug And Automation")
        debug_grid = debug_group.layout()
        self.auto_open_devtools_check = self._check_box()
        self._add_chromium_check(debug_group, debug_grid, 0, "auto-open-devtools-for-tabs", self.auto_open_devtools_check)
        self.enable_logging_check = self._check_box()
        self._add_chromium_check(debug_group, debug_grid, 1, "enable-logging", self.enable_logging_check)
        self.remote_debugging_port_input = self._line_edit("9222")
        self._add_chromium_row(debug_group, debug_grid, 2, "remote-debugging-port", self.remote_debugging_port_input)
        self.remote_debugging_pipe_check = self._check_box()
        self._add_chromium_check(debug_group, debug_grid, 3, "remote-debugging-pipe", self.remote_debugging_pipe_check)
        self.trace_startup_check = self._check_box()
        self._add_chromium_check(debug_group, debug_grid, 4, "trace-startup", self.trace_startup_check)
        self.trace_startup_file_input = self._line_edit()
        self._add_chromium_row(debug_group, debug_grid, 5, "trace-startup-file", self.trace_startup_file_input)
        self.vmodule_input = self._line_edit()
        self._add_chromium_row(debug_group, debug_grid, 6, "vmodule", self.vmodule_input)
        inner_layout.addWidget(debug_group)

        extra_group = QGroupBox("Extra Flags")
        extra_layout = QVBoxLayout(extra_group)
        self.extra_args_input = QPlainTextEdit()
        self.extra_args_input.setPlaceholderText("--force-device-scale-factor=1.25 --ozone-platform-hint=auto")
        self.extra_args_input.textChanged.connect(self.mark_dirty)
        extra_layout.addWidget(self.extra_args_input)
        inner_layout.addWidget(extra_group)
        inner_layout.addStretch(1)

        scroll.setWidget(inner)
        wrapper_layout = QVBoxLayout(container)
        wrapper_layout.addLayout(search_layout)
        wrapper_layout.addWidget(scroll)
        self._filter_chromium("")
        return container

    def _filter_chromium(self, query: str) -> None:
        if not self._chromium_rows:
            return
        query_lower = query.strip().lower()
        hidden_flags = BROWSER_FLAG_HIDDEN.get(self._current_browser, set())
        visible_by_group: dict[QGroupBox, bool] = {g: False for g in self._chromium_groups}

        for row in self._chromium_rows:
            group = row["group"]
            label_widget = row["label"]
            widget = row["widget"]
            tooltip = row["tooltip"]
            flag_name = row.get("flag_name", "")

            browser_hidden = flag_name in hidden_flags

            if browser_hidden:
                label_widget.setVisible(False)
                widget.setVisible(False)
            elif not query_lower:
                label_widget.setVisible(True)
                widget.setVisible(True)
                visible_by_group[group] = True
            else:
                matches = query_lower in label_widget.text().lower() or query_lower in tooltip.lower()
                label_widget.setVisible(matches)
                widget.setVisible(matches)
                if matches:
                    visible_by_group[group] = True

        for group, visible in visible_by_group.items():
            group.setVisible(visible)

    def _update_browser_ui(self, *_args) -> None:
        path = self.chromium_input.text().strip()
        if not path:
            self._current_browser = "Unknown"
            self.tabs.setTabEnabled(self._options_tab_index, False)
            self.tabs.setTabText(self._options_tab_index, "Browser Options")
            if self.tabs.currentIndex() == self._options_tab_index:
                self.tabs.setCurrentIndex(0)
        else:
            browser = resolve_browser_identity(path)
            if browser == "Unknown":
                browser = "Chromium"
            self._current_browser = browser
            self.tabs.setTabEnabled(self._options_tab_index, True)
            self.tabs.setTabText(self._options_tab_index, f"{browser} Options")

        self._filter_chromium(self.chromium_search_input.text())

    def _chromium_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)
        self._chromium_groups.append(group)
        return group

    def _add_chromium_row(self, group: QGroupBox, layout: QGridLayout, row: int, label: str, widget: QWidget) -> None:
        label_widget = QLabel(label)
        tooltip = CHROMIUM_SWITCH_TOOLTIPS.get(label, "")
        if tooltip:
            label_widget.setToolTip(tooltip)
            widget.setToolTip(tooltip)
        layout.addWidget(label_widget, row, 0)
        layout.addWidget(widget, row, 1)
        self._chromium_rows.append({
            "group": group,
            "label": label_widget,
            "widget": widget,
            "tooltip": tooltip,
            "flag_name": label,
        })

    def _add_chromium_check(self, group: QGroupBox, layout: QGridLayout, row: int, label: str, checkbox: QCheckBox) -> None:
        label_widget = QLabel(label)
        tooltip = CHROMIUM_SWITCH_TOOLTIPS.get(label, "")
        if tooltip:
            label_widget.setToolTip(tooltip)
            checkbox.setToolTip(tooltip)
        layout.addWidget(label_widget, row, 0)
        layout.addWidget(checkbox, row, 1, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        self._chromium_rows.append({
            "group": group,
            "label": label_widget,
            "widget": checkbox,
            "tooltip": tooltip,
            "flag_name": label,
        })

    def _path_row_button(self, button_text: str, callback) -> dict[str, QWidget]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        line_edit = self._line_edit()
        button = QPushButton(button_text)
        button.clicked.connect(callback)
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return {"widget": widget, "line_edit": line_edit}

    def _line_edit(self, placeholder: str = "") -> QLineEdit:
        line_edit = QLineEdit()
        if placeholder:
            line_edit.setPlaceholderText(placeholder)
        line_edit.textEdited.connect(self.mark_dirty)
        return line_edit

    def _check_box(self, text: str = "") -> QCheckBox:
        checkbox = QCheckBox()
        checkbox.setText("")
        if text:
            checkbox.setToolTip(text)
        checkbox.toggled.connect(self.mark_dirty)
        return checkbox

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) == self.webapps_tab:
            self.refresh_webapps_list()

    def refresh_webapps_list(self, *_args) -> None:
        self.webapps_list.clear()
        for config in collect_existing_webapps():
            item_widget = self._build_webapp_item_widget(config)
            item = QListWidgetItem()
            item.setData(Qt.UserRole, config.desktop_path)
            item.setToolTip(config.desktop_path)
            item.setSizeHint(item_widget.sizeHint())
            self.webapps_list.addItem(item)
            self.webapps_list.setItemWidget(item, item_widget)

        count = self.webapps_list.count()
        label = "webapp" if count == 1 else "webapps"
        self.webapps_count_label.setText(f"{count} {label} found")

    def launch_webapp_by_path(self, path: str) -> None:
        desktop_path = Path(path)
        if not desktop_path.exists():
            QMessageBox.warning(self, APP_NAME, f"Desktop file not found:\n{desktop_path}")
            return
        subprocess.Popen(['gio', 'launch', str(desktop_path)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def open_webapp_list_item(self, item: QListWidgetItem) -> None:
        if not self._confirm_discard():
            return
        path = item.data(Qt.UserRole)
        if path and self.open_desktop(Path(path)):
            self.tabs.setCurrentIndex(0)

    def uninstall_webapp(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if not path:
            return

        desktop_path = Path(path)
        if not self._is_user_webapp(desktop_path):
            QMessageBox.information(
                self,
                APP_NAME,
                "Only user-installed web apps can be removed from here.",
            )
            return

        try:
            config = load_desktop_file(desktop_path)
        except Exception:
            config = WebAppConfig(desktop_path=str(desktop_path), desktop_filename=desktop_path.name)

        data_dir = Path(config.user_data_dir).expanduser() if config.user_data_dir.strip() else None

        message = (
            f"Remove '{config.name or config.desktop_filename}'?\n\n"
            f"This will delete:\n"
            f"- {desktop_path}\n"
        )
        icon_path = Path(config.icon_path).expanduser() if config.icon_path.strip() else None
        if icon_path and icon_path.exists() and self._is_managed_icon_path(icon_path):
            message += f"- {icon_path}\n"
        if data_dir and data_dir.exists():
            message += f"- {data_dir}\n"

        answer = QMessageBox.question(
            self,
            APP_NAME,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        errors: list[str] = []
        try:
            if desktop_path.exists():
                desktop_path.unlink()
        except OSError as exc:
            errors.append(f"Could not remove {desktop_path}: {exc}")

        if icon_path and icon_path.exists() and self._is_managed_icon_path(icon_path):
            try:
                icon_path.unlink()
            except OSError as exc:
                errors.append(f"Could not remove {icon_path}: {exc}")

        if data_dir and data_dir.exists():
            try:
                shutil.rmtree(data_dir)
            except OSError as exc:
                errors.append(f"Could not remove {data_dir}: {exc}")

        refresh_results = run_refresh_commands()
        self.refresh_webapps_list()

        if errors:
            QMessageBox.warning(self, APP_NAME, "\n".join(errors + ["", *refresh_results]))
        else:
            QMessageBox.information(self, APP_NAME, "Web app removed.\n\nThe application menu and desktop icons have been updated.")

    def _build_webapp_item_widget(self, config: WebAppConfig) -> QWidget:
        widget = QWidget()
        widget.setObjectName("WebAppItem")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 10, 12, 14)
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
        open_button.clicked.connect(lambda *_args, p=config.desktop_path: self.launch_webapp_by_path(p))
        layout.addWidget(open_button)

        if self._is_user_webapp(Path(config.desktop_path)):
            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(lambda *_args, p=config.desktop_path: self.open_webapp_by_path(p))
            layout.addWidget(edit_button)

            uninstall_button = QPushButton("Uninstall")
            uninstall_button.clicked.connect(lambda *_args, p=config.desktop_path: self.uninstall_webapp_by_path(p))
            layout.addWidget(uninstall_button)

        return widget

    def _show_webapp_context_menu(self, pos) -> None:
        item = self.webapps_list.itemAt(pos)
        if item is None:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        menu = QMenu(self)
        open_action = menu.addAction("Open")
        desktop_path = Path(str(data))
        uninstall_action = menu.addAction("Uninstall") if self._is_user_webapp(desktop_path) else None
        action = menu.exec(self.webapps_list.mapToGlobal(pos))
        if action == open_action:
            self.open_webapp_list_item(item)
        elif action == uninstall_action:
            self.uninstall_webapp(item)

    def uninstall_webapp_by_path(self, path: str) -> None:
        for index in range(self.webapps_list.count()):
            item = self.webapps_list.item(index)
            if item and item.data(Qt.UserRole) == path:
                self.uninstall_webapp(item)
                return

    def open_webapp_by_path(self, path: str) -> None:
        for index in range(self.webapps_list.count()):
            item = self.webapps_list.item(index)
            if item and item.data(Qt.UserRole) == path:
                self.open_webapp_list_item(item)
                return

    def _is_managed_icon_path(self, path: Path) -> bool:
        try:
            return path.resolve().is_relative_to(ICON_DIR.resolve())
        except AttributeError:
            try:
                path.resolve().relative_to(ICON_DIR.resolve())
                return True
            except ValueError:
                return False
        except OSError:
            return False

    def _is_user_webapp(self, path: Path) -> bool:
        try:
            return path.resolve().is_relative_to(USER_APPLICATIONS_DIR.resolve())
        except AttributeError:
            try:
                path.resolve().relative_to(USER_APPLICATIONS_DIR.resolve())
                return True
            except ValueError:
                return False
        except OSError:
            return False

    def mark_dirty(self, *_args) -> None:
        self._dirty = True
        self._update_target_label()

    def _on_name_changed(self, text: str) -> None:
        self.mark_dirty()
        if self._filename_auto_sync:
            suggested = f"{slugify(text)}.desktop"
            with QSignalBlocker(self.filename_input):
                self.filename_input.setText(suggested)
        self._sync_derived_paths()

    def _on_filename_changed(self, *_args) -> None:
        self._filename_auto_sync = False
        self.mark_dirty()
        self._sync_derived_paths()

    def _sync_derived_paths(self) -> None:
        if not self.user_data_dir_input["line_edit"].text().strip():
            filename = self.filename_input.text().strip() or "webapp.desktop"
            with QSignalBlocker(self.user_data_dir_input["line_edit"]):
                self.user_data_dir_input["line_edit"].setText(default_user_data_dir(filename))
        self._update_target_label()

    def _on_url_edit_finished(self) -> None:
        self.mark_dirty()
        url = self.url_input.text().strip()
        if url and not self.icon_input.text().strip() and url not in self._fetched_icon_urls:
            self._fetched_icon_urls.add(url)
            self.fetch_icon(silent=True)

    def _on_category_selected(self, index: int) -> None:
        if index <= 0:
            return
        updated = append_category_value(self.categories_input.text(), self.categories_select.itemText(index))
        self.categories_input.setText(updated)
        with QSignalBlocker(self.categories_select):
            self.categories_select.setCurrentIndex(0)
        self.mark_dirty()

    def _update_target_label(self) -> None:
        filename = self.filename_input.text().strip() or "webapp.desktop"
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        target = USER_APPLICATIONS_DIR / filename
        self.target_path_label.setText(f"Target: {target}")

    def update_icon_preview(self, icon_path: str) -> None:
        path = icon_path.strip()
        if not path:
            self.icon_preview_label.setPixmap(QPixmap())
            self.icon_preview_label.setText("No icon")
            return

        icon = QIcon(path)
        pixmap = icon.pixmap(ICON_PREVIEW_SIZE, ICON_PREVIEW_SIZE)
        if pixmap.isNull():
            pixmap = QPixmap(path)
        if pixmap.isNull():
            self.icon_preview_label.setPixmap(QPixmap())
            self.icon_preview_label.setText("Invalid icon")
            return

        scaled = pixmap.scaled(
            ICON_PREVIEW_SIZE,
            ICON_PREVIEW_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.icon_preview_label.setText("")
        self.icon_preview_label.setPixmap(scaled)

    def _get_widget(self, name: str) -> QWidget:
        return getattr(self, name)

    def _apply_config_to_ui(self, config: WebAppConfig) -> None:
        for attr_name, widget_name in _UI_TEXT_FIELDS:
            widget = self._get_widget(widget_name)
            value = getattr(config, attr_name, "")
            if widget_name == "user_data_dir_input":
                widget["line_edit"].setText(value or default_user_data_dir(config.desktop_filename))
            elif widget_name == "extra_args_input":
                widget.setPlainText(value)
            elif widget_name == "categories_select":
                widget.setCurrentIndex(0)
            else:
                widget.setText(value)

        for attr_name, widget_name in _UI_CHECKBOX_FIELDS:
            widget = self._get_widget(widget_name)
            value = getattr(config, attr_name, False)
            widget.setChecked(value)

    def _collect_ui_to_config(self) -> dict:
        data: dict[str, str | bool] = {}
        for attr_name, widget_name in _UI_TEXT_FIELDS:
            widget = self._get_widget(widget_name)
            if widget_name == "user_data_dir_input":
                data[attr_name] = widget["line_edit"].text().strip()
            elif widget_name == "extra_args_input":
                data[attr_name] = widget.toPlainText().strip()
            elif widget_name == "categories_input":
                data[attr_name] = serialize_categories(parse_categories(widget.text()))
            else:
                data[attr_name] = widget.text().strip()

        for attr_name, widget_name in _UI_CHECKBOX_FIELDS:
            widget = self._get_widget(widget_name)
            data[attr_name] = widget.isChecked()

        return data

    def load_config(self, config: WebAppConfig) -> None:
        self.current_config = config
        self._filename_auto_sync = not bool(config.opened_from_existing)
        self._fetched_icon_urls.clear()
        self._apply_config_to_ui(config)
        self._dirty = False
        self._update_target_label()
        self.update_icon_preview(config.icon_path)
        self._update_browser_ui()

    def gather_config(self) -> WebAppConfig:
        filename = self.filename_input.text().strip() or f"{slugify(self.name_input.text())}.desktop"
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        desktop_path = str(USER_APPLICATIONS_DIR / filename)
        user_data_dir = self.user_data_dir_input["line_edit"].text().strip() or default_user_data_dir(filename)
        data = self._collect_ui_to_config()
        data["desktop_filename"] = filename
        data["desktop_path"] = desktop_path
        data["user_data_dir"] = user_data_dir
        data["opened_from_existing"] = bool(self.current_config.opened_from_existing)
        return WebAppConfig(**data)

    def new_config(self, *_args) -> None:
        if not self._confirm_discard():
            return
        self.load_config(WebAppConfig(chromium_path=detect_chromium(), desktop_filename="webapp.desktop"))
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage("Form cleared.")

    def detect_chromium_path(self, *_args) -> None:
        found = detect_all_chromiums()
        if not found:
            QMessageBox.warning(self, APP_NAME, "Could not find a Chromium-based browser in PATH.")
            return
        if len(found) == 1:
            path = next(iter(found.values()))
            self.chromium_input.setText(path)
            self.mark_dirty()
            self._update_browser_ui()
            self.statusBar().showMessage(f"Detected: {path}")
            return
        items = [f"{name}  ({path})" for name, path in found.items()]
        item, ok = QInputDialog.getItem(
            self, "Select Browser",
            "Multiple browsers detected. Choose one:",
            items, 0, False,
        )
        if ok and item:
            path = item.split("  (", 1)[1].rstrip(")")
            self.chromium_input.setText(path)
            self.mark_dirty()
            self._update_browser_ui()
            self.statusBar().showMessage(f"Selected: {path}")

    def choose_icon_file(self, *_args) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Icon",
            str(Path.home()),
            "Images (*.png *.svg *.ico *.jpg *.jpeg *.webp)",
        )
        if path:
            filename = self.filename_input.text().strip() or f"{slugify(self.name_input.text())}.desktop"
            slug = icon_slug_for_desktop_filename(filename)
            try:
                icon_path = store_icon_file(path, slug)
            except Exception as exc:
                QMessageBox.warning(self, APP_NAME, str(exc))
                return
            self.icon_input.setText(str(icon_path))
            self.mark_dirty()
            self.statusBar().showMessage(f"Icon saved to {icon_path}")

    def choose_user_data_dir(self, *_args) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose user-data-dir", str(Path.home()))
        if path:
            self.user_data_dir_input["line_edit"].setText(path)
            self.mark_dirty()

    def fetch_icon(self, silent: bool = False) -> None:
        url = self.url_input.text().strip()
        if not url:
            if not silent:
                QMessageBox.warning(self, APP_NAME, "Enter a URL before fetching the icon.")
            return
        filename = self.filename_input.text().strip() or f"{slugify(self.name_input.text())}.desktop"
        slug = icon_slug_for_desktop_filename(filename)
        self.statusBar().showMessage("Downloading icon...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            icon_path = fetch_icon_for_url(
                url,
                slug,
                ignore_ssl_errors=self.ignore_icon_ssl_errors_check.isChecked(),
            )
            self.icon_input.setText(str(icon_path))
            self.mark_dirty()
            self.statusBar().showMessage(f"Icon saved to {icon_path}")
        except Exception as exc:
            self.statusBar().showMessage("Could not download the icon.")
            self.icon_input.setText("")
            if not silent:
                QMessageBox.warning(self, APP_NAME, str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def open_desktop(self, path: Path) -> bool:
        try:
            config = load_desktop_file(path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return False
        self.load_config(config)
        self.statusBar().showMessage(f"Loaded: {path}")
        return True

    def open_desktop_folder(self, *_args) -> None:
        filename = self.filename_input.text().strip() or "webapp.desktop"
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        target = USER_APPLICATIONS_DIR / filename
        try:
            reveal_in_file_manager(target)
            self.statusBar().showMessage(f"Opened folder: {target.parent}")
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))

    def save_desktop(self, *_args) -> None:
        config = self.gather_config()
        if not config.name:
            QMessageBox.warning(self, APP_NAME, "The title is required.")
            return
        if not config.url.strip():
            QMessageBox.warning(self, APP_NAME, "The URL is required.")
            return
        if not config.chromium_path:
            QMessageBox.warning(self, APP_NAME, "Configure the Chrome/Chromium executable.")
            return
        if not resolve_executable(config.chromium_path):
            QMessageBox.warning(self, APP_NAME, "The Chrome/Chromium executable does not exist.")
            return
        if not config.icon_path:
            self.fetch_icon(silent=True)
            config = self.gather_config()
        elif Path(config.icon_path).expanduser().parent != ICON_DIR:
            slug = icon_slug_for_desktop_filename(config.desktop_filename)
            try:
                icon_path = store_icon_file(config.icon_path, slug)
            except Exception as exc:
                QMessageBox.warning(self, APP_NAME, str(exc))
                return
            self.icon_input.setText(str(icon_path))
            config.icon_path = str(icon_path)

        try:
            entry = config.to_desktop_entry()
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return

        USER_APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        target = USER_APPLICATIONS_DIR / config.desktop_filename
        try:
            target.write_text(entry, encoding="utf-8")
            os.chmod(target, 0o755)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not save {target}.\n{exc}")
            return

        refresh_results = run_refresh_commands()
        self.current_config = config
        self.current_config.opened_from_existing = True
        self._dirty = False
        self._update_target_label()
        QMessageBox.information(
            self,
            APP_NAME,
            "Web app saved successfully.\n\nThe application menu and desktop icons have been updated.",
        )
        self.refresh_webapps_list()
        self.statusBar().showMessage(f"Saved: {target}")

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self,
            APP_NAME,
            "There are unsaved changes. Do you want to discard them?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def _show_about_dialog(self) -> None:
        icon_path = app_asset_path("icon.png")
        pixmap = QPixmap(str(icon_path)) if icon_path.exists() else QPixmap()
        icon_label = QLabel()
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaledToWidth(64, Qt.SmoothTransformation))
        icon_label.setAlignment(Qt.AlignCenter)

        name_label = QLabel(f"<b>{APP_NAME}</b>")
        name_label.setAlignment(Qt.AlignCenter)

        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel(APP_DESCRIPTION)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)

        layout = QVBoxLayout()
        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        layout.addWidget(version_label)
        layout.addWidget(desc_label)
        layout.addWidget(button_box)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"About {APP_NAME}")
        dialog.setLayout(layout)
        dialog.setFixedSize(400, 200)
        button_box.accepted.connect(dialog.accept)
        dialog.exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
