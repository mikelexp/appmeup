from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QThreadPool, QSignalBlocker, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.categories import (
    append_category_value,
    collect_existing_categories,
    invalidate_category_cache,
    parse_categories,
    serialize_categories,
)
from src.config import WebAppConfig, collect_existing_webapps, load_desktop_file
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
from src.browser import detect_all_chromiums, detect_chromium, resolve_browser_identity, resolve_executable
from src.desktop_env import reveal_in_file_manager, run_refresh_commands
from src.icon_fetcher import IconFetchWorker
from src.icons import app_asset_path, app_icon, icon_slug_for_desktop_filename, store_icon_file, webapp_icon
from src.logger import setup_logging
from src.settings import load_last_browser, restore_window_geometry, save_last_browser, save_window_geometry
from src.ui import build_basic_tab, build_browser_tab, build_webapp_item_widget, build_webapps_tab
from src.ui_fields import _UI_TEXT_FIELDS, _UI_CHECKBOX_FIELDS
from src.utils import default_user_data_dir, slugify, validate_url

logger = setup_logging()


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
        self._icon_fetching = False

        self._build_ui()
        self._restore_geometry()
        self._connect_signals()
        self.load_config(self.current_config)
        self.refresh_webapps_list()
        self.statusBar().showMessage("Ready.")
        logger.debug("MainWindow initialized")

    def _restore_geometry(self) -> None:
        geo = restore_window_geometry()
        if geo and geo.width() > 0 and geo.height() > 0:
            self.setGeometry(geo)

    def _build_ui(self) -> None:
        self.setStatusBar(QStatusBar(self))

        file_menu = self.menuBar().addMenu("File")

        new_action = QAction("New WebApp", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)

        save_action = QAction("Save WebApp", self)
        save_action.setShortcut("Ctrl+S")
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

        basic_tab, self._basic_widgets = build_basic_tab()
        self.tabs.addTab(basic_tab, "Web App Options")

        browser_tab, self._browser_widgets, self._chromium_rows, self._chromium_groups = build_browser_tab()
        self._options_tab_index = self.tabs.addTab(browser_tab, "Browser Options")

        webapps_tab, self.webapps_list, self.webapps_count_label = build_webapps_tab()
        self.webapps_tab = webapps_tab
        self.tabs.addTab(self.webapps_tab, "Installed Web Apps")
        self.tabs.setTabEnabled(self._options_tab_index, False)
        outer_layout.addWidget(self.tabs)

        actions_layout = QHBoxLayout()
        self.target_path_label = QLabel()
        self.target_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        actions_layout.addWidget(self.target_path_label, stretch=1)

        self.new_button = QPushButton("New WebApp")
        actions_layout.addWidget(self.new_button)

        self.save_button = QPushButton("Save WebApp")
        actions_layout.addWidget(self.save_button)
        outer_layout.addLayout(actions_layout)

        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self.findChild(QAction, "").triggered.connect(self.new_config)
        for action in self.menuBar().actions():
            if action.text() == "File":
                for sub in action.menu().actions():
                    if sub.text() == "New WebApp":
                        sub.triggered.connect(self.new_config)
                    elif sub.text() == "Save WebApp":
                        sub.triggered.connect(self.save_desktop)

        self._basic_widgets["name_input"].textEdited.connect(self._on_name_changed)
        self._basic_widgets["url_input"].textEdited.connect(self.mark_dirty)
        self._basic_widgets["url_input"].editingFinished.connect(self._on_url_edit_finished)
        self._basic_widgets["comment_input"].textEdited.connect(self.mark_dirty)
        self._basic_widgets["categories_select"].currentIndexChanged.connect(self._on_category_selected)
        self._basic_widgets["categories_input"].textEdited.connect(self.mark_dirty)
        self._basic_widgets["filename_input"].textEdited.connect(self._on_filename_changed)
        self._basic_widgets["open_folder_button"].clicked.connect(self.open_desktop_folder)
        self._basic_widgets["chromium_input"].textEdited.connect(self.mark_dirty)
        self._basic_widgets["chromium_input"].textEdited.connect(self._update_browser_ui)
        self._basic_widgets["chromium_detect_button"].clicked.connect(self.detect_chromium_path)
        self._basic_widgets["icon_input"].textEdited.connect(self.mark_dirty)
        self._basic_widgets["icon_input"].textChanged.connect(self.update_icon_preview)
        self._basic_widgets["browse_icon_button"].clicked.connect(self.choose_icon_file)
        self._basic_widgets["fetch_icon_button"].clicked.connect(self.fetch_icon)
        self._basic_widgets["ignore_icon_ssl_errors_check"].toggled.connect(self.mark_dirty)

        self._browser_widgets["chromium_search_input"].textChanged.connect(self._filter_chromium)
        for w in self._browser_widgets.values():
            if isinstance(w, QLineEdit):
                w.textEdited.connect(self.mark_dirty)
            elif isinstance(w, QCheckBox):
                w.toggled.connect(self.mark_dirty)
            elif isinstance(w, dict) and "line_edit" in w:
                w["line_edit"].textEdited.connect(self.mark_dirty)
        self._browser_widgets["extra_args_input"].textChanged.connect(self.mark_dirty)

        self.webapps_list.itemDoubleClicked.connect(self.open_webapp_list_item)
        self.webapps_list.customContextMenuRequested.connect(self._show_webapp_context_menu)
        self.webapps_tab.findChild(QPushButton, "").clicked.connect(self.refresh_webapps_list)
        for btn in self.webapps_tab.findChildren(QPushButton):
            if btn.text() == "Refresh":
                btn.clicked.connect(self.refresh_webapps_list)

        self.new_button.clicked.connect(self.new_config)
        self.save_button.clicked.connect(self.save_desktop)

        self.tabs.currentChanged.connect(self._on_tab_changed)

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
        path = self._basic_widgets["chromium_input"].text().strip()
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

        self._filter_chromium(self._browser_widgets["chromium_search_input"].text())

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
        try:
            subprocess.Popen(['gtk-launch', desktop_path.name], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            subprocess.Popen(['xdg-open', str(desktop_path)], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Launched web app: %s", desktop_path)

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
        invalidate_category_cache()
        self.refresh_webapps_list()

        if errors:
            QMessageBox.warning(self, APP_NAME, "\n".join(errors + ["", *refresh_results]))
        else:
            QMessageBox.information(self, APP_NAME, "Web app removed.\n\nThe application menu and desktop icons have been updated.")
            logger.info("Uninstalled web app: %s", desktop_path)

    def _build_webapp_item_widget(self, config: WebAppConfig) -> QWidget:
        widget = build_webapp_item_widget(config)
        layout = widget.layout()

        open_button = layout.itemAt(2).widget()
        open_button.clicked.connect(lambda *_args, p=config.desktop_path: self.launch_webapp_by_path(p))

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
            with QSignalBlocker(self._basic_widgets["filename_input"]):
                self._basic_widgets["filename_input"].setText(suggested)
        self._sync_derived_paths()

    def _on_filename_changed(self, *_args) -> None:
        self._filename_auto_sync = False
        self.mark_dirty()
        self._sync_derived_paths()

    def _sync_derived_paths(self) -> None:
        if not self._browser_widgets["user_data_dir_input"]["line_edit"].text().strip():
            filename = self._basic_widgets["filename_input"].text().strip() or "webapp.desktop"
            with QSignalBlocker(self._browser_widgets["user_data_dir_input"]["line_edit"]):
                self._browser_widgets["user_data_dir_input"]["line_edit"].setText(default_user_data_dir(filename))
        self._update_target_label()

    def _on_url_edit_finished(self) -> None:
        self.mark_dirty()
        url = self._basic_widgets["url_input"].text().strip()
        validated = validate_url(url)
        if validated:
            with QSignalBlocker(self._basic_widgets["url_input"]):
                self._basic_widgets["url_input"].setText(validated)
        if validated and not self._basic_widgets["icon_input"].text().strip() and validated not in self._fetched_icon_urls:
            self._fetched_icon_urls.add(validated)
            self.fetch_icon(silent=True)

    def _on_category_selected(self, index: int) -> None:
        if index <= 0:
            return
        updated = append_category_value(self._basic_widgets["categories_input"].text(), self._basic_widgets["categories_select"].itemText(index))
        self._basic_widgets["categories_input"].setText(updated)
        with QSignalBlocker(self._basic_widgets["categories_select"]):
            self._basic_widgets["categories_select"].setCurrentIndex(0)
        self.mark_dirty()

    def _update_target_label(self) -> None:
        filename = self._basic_widgets["filename_input"].text().strip() or "webapp.desktop"
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        target = USER_APPLICATIONS_DIR / filename
        self.target_path_label.setText(f"Target: {target}")

    def update_icon_preview(self, icon_path: str) -> None:
        path = icon_path.strip()
        if not path:
            self._basic_widgets["icon_preview_label"].setPixmap(QPixmap())
            self._basic_widgets["icon_preview_label"].setText("No icon")
            return

        icon = QIcon(path)
        pixmap = icon.pixmap(ICON_PREVIEW_SIZE, ICON_PREVIEW_SIZE)
        if pixmap.isNull():
            pixmap = QPixmap(path)
        if pixmap.isNull():
            self._basic_widgets["icon_preview_label"].setPixmap(QPixmap())
            self._basic_widgets["icon_preview_label"].setText("Invalid icon")
            return

        scaled = pixmap.scaled(
            ICON_PREVIEW_SIZE,
            ICON_PREVIEW_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._basic_widgets["icon_preview_label"].setText("")
        self._basic_widgets["icon_preview_label"].setPixmap(scaled)

    def _get_widget(self, name: str) -> QWidget:
        if name in self._basic_widgets:
            return self._basic_widgets[name]
        if name in self._browser_widgets:
            return self._browser_widgets[name]
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
        filename = self._basic_widgets["filename_input"].text().strip() or f"{slugify(self._basic_widgets['name_input'].text())}.desktop"
        if not filename.endswith(".desktop"):
            filename = f"{filename}.desktop"
        desktop_path = str(USER_APPLICATIONS_DIR / filename)
        user_data_dir = self._browser_widgets["user_data_dir_input"]["line_edit"].text().strip() or default_user_data_dir(filename)
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
        logger.debug("New config created")

    def detect_chromium_path(self, *_args) -> None:
        found = detect_all_chromiums()
        if not found:
            QMessageBox.warning(self, APP_NAME, "Could not find a Chromium-based browser in PATH.")
            return
        if len(found) == 1:
            path = next(iter(found.values()))
            self._basic_widgets["chromium_input"].setText(path)
            save_last_browser(path)
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
            self._basic_widgets["chromium_input"].setText(path)
            save_last_browser(path)
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
            filename = self._basic_widgets["filename_input"].text().strip() or f"{slugify(self._basic_widgets['name_input'].text())}.desktop"
            slug = icon_slug_for_desktop_filename(filename)
            try:
                icon_path = store_icon_file(path, slug)
            except Exception as exc:
                QMessageBox.warning(self, APP_NAME, str(exc))
                return
            self._basic_widgets["icon_input"].setText(str(icon_path))
            self.mark_dirty()
            self.statusBar().showMessage(f"Icon saved to {icon_path}")

    def choose_user_data_dir(self, *_args) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose user-data-dir", str(Path.home()))
        if path:
            self._browser_widgets["user_data_dir_input"]["line_edit"].setText(path)
            self.mark_dirty()

    def fetch_icon(self, silent: bool = False) -> None:
        url = self._basic_widgets["url_input"].text().strip()
        validated = validate_url(url)
        if not validated:
            if not silent:
                QMessageBox.warning(self, APP_NAME, "Enter a valid URL before fetching the icon.")
            return
        if self._icon_fetching:
            return
        filename = self._basic_widgets["filename_input"].text().strip() or f"{slugify(self._basic_widgets['name_input'].text())}.desktop"
        self.statusBar().showMessage("Downloading icon...")
        self._icon_fetching = True

        worker = IconFetchWorker(validated, filename, self._basic_widgets["ignore_icon_ssl_errors_check"].isChecked())
        worker.signals.finished.connect(self._on_icon_fetch_success)
        worker.signals.error.connect(lambda err: self._on_icon_fetch_error(err, silent))
        QThreadPool.globalInstance().start(worker)

    def _on_icon_fetch_success(self, icon_path: str) -> None:
        self._icon_fetching = False
        self._basic_widgets["icon_input"].setText(icon_path)
        self.mark_dirty()
        self.statusBar().showMessage(f"Icon saved to {icon_path}")
        logger.info("Icon fetched successfully: %s", icon_path)

    def _on_icon_fetch_error(self, error: str, silent: bool) -> None:
        self._icon_fetching = False
        self.statusBar().showMessage("Could not download the icon.")
        self._basic_widgets["icon_input"].setText("")
        if not silent:
            QMessageBox.warning(self, APP_NAME, error)

    def open_desktop(self, path: Path) -> bool:
        try:
            config = load_desktop_file(path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return False
        self.load_config(config)
        self.statusBar().showMessage(f"Loaded: {path}")
        logger.info("Loaded desktop file: %s", path)
        return True

    def open_desktop_folder(self, *_args) -> None:
        filename = self._basic_widgets["filename_input"].text().strip() or "webapp.desktop"
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
        url_validated = validate_url(config.url)
        if not config.name:
            QMessageBox.warning(self, APP_NAME, "The title is required.")
            return
        if not url_validated:
            QMessageBox.warning(self, APP_NAME, "The URL is required and must be valid.")
            return
        config.url = url_validated
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
            self._basic_widgets["icon_input"].setText(str(icon_path))
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
        invalidate_category_cache()
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
        logger.info("Saved web app: %s", target)

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
            save_window_geometry(self.geometry())
            super().closeEvent(event)
        else:
            event.ignore()
