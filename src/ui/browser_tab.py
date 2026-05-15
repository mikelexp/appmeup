from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.constants import CHROMIUM_SWITCH_TOOLTIPS


def build_browser_tab() -> tuple[QWidget, dict[str, QWidget], list[dict]]:
    widgets: dict[str, QWidget] = {}
    chromium_rows: list[dict] = []
    chromium_groups: list[QGroupBox] = []

    container = QWidget()

    search_layout = QHBoxLayout()
    chromium_search_input = QLineEdit()
    chromium_search_input.setPlaceholderText("Search parameters and tooltips...")
    widgets["chromium_search_input"] = chromium_search_input
    search_layout.addWidget(QLabel("Filter:"))
    search_layout.addWidget(chromium_search_input, stretch=1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)

    inner = QWidget()
    inner_layout = QVBoxLayout(inner)

    app_group, app_widgets, app_rows = _build_app_window_group()
    widgets.update(app_widgets)
    chromium_rows.extend(app_rows)
    chromium_groups.append(app_group)
    inner_layout.addWidget(app_group)

    identity_group, identity_widgets, identity_rows = _build_identity_group()
    widgets.update(identity_widgets)
    chromium_rows.extend(identity_rows)
    chromium_groups.append(identity_group)
    inner_layout.addWidget(identity_group)

    rendering_group, rendering_widgets, rendering_rows = _build_rendering_group()
    widgets.update(rendering_widgets)
    chromium_rows.extend(rendering_rows)
    chromium_groups.append(rendering_group)
    inner_layout.addWidget(rendering_group)

    network_group, network_widgets, network_rows = _build_network_group()
    widgets.update(network_widgets)
    chromium_rows.extend(network_rows)
    chromium_groups.append(network_group)
    inner_layout.addWidget(network_group)

    debug_group, debug_widgets, debug_rows = _build_debug_group()
    widgets.update(debug_widgets)
    chromium_rows.extend(debug_rows)
    chromium_groups.append(debug_group)
    inner_layout.addWidget(debug_group)

    extra_group = QGroupBox("Extra Flags")
    extra_layout = QVBoxLayout(extra_group)
    extra_args_input = QPlainTextEdit()
    extra_args_input.setPlaceholderText("--force-device-scale-factor=1.25 --ozone-platform-hint=auto")
    widgets["extra_args_input"] = extra_args_input
    extra_layout.addWidget(extra_args_input)
    inner_layout.addWidget(extra_group)
    inner_layout.addStretch(1)

    scroll.setWidget(inner)
    wrapper_layout = QVBoxLayout(container)
    wrapper_layout.addLayout(search_layout)
    wrapper_layout.addWidget(scroll)

    return container, widgets, chromium_rows, chromium_groups


def _add_value_row(group: QGroupBox, layout: QGridLayout, row: int, label: str, widget: QWidget, rows: list[dict]) -> None:
    label_widget = QLabel(label)
    tooltip = CHROMIUM_SWITCH_TOOLTIPS.get(label, "")
    if tooltip:
        label_widget.setToolTip(tooltip)
        widget.setToolTip(tooltip)
    layout.addWidget(label_widget, row, 0)
    layout.addWidget(widget, row, 1)
    rows.append({
        "group": group,
        "label": label_widget,
        "widget": widget,
        "tooltip": tooltip,
        "flag_name": label,
    })


def _add_check_row(group: QGroupBox, layout: QGridLayout, row: int, label: str, checkbox: QCheckBox, rows: list[dict]) -> None:
    label_widget = QLabel(label)
    tooltip = CHROMIUM_SWITCH_TOOLTIPS.get(label, "")
    if tooltip:
        label_widget.setToolTip(tooltip)
        checkbox.setToolTip(tooltip)
    layout.addWidget(label_widget, row, 0)
    layout.addWidget(checkbox, row, 1, alignment=Qt.AlignLeft | Qt.AlignVCenter)
    rows.append({
        "group": group,
        "label": label_widget,
        "widget": checkbox,
        "tooltip": tooltip,
        "flag_name": label,
    })


def _make_line_edit(placeholder: str = "") -> QLineEdit:
    line_edit = QLineEdit()
    if placeholder:
        line_edit.setPlaceholderText(placeholder)
    return line_edit


def _make_check_box() -> QCheckBox:
    checkbox = QCheckBox()
    checkbox.setText("")
    return checkbox


def _build_app_window_group() -> tuple[QGroupBox, dict[str, QWidget], list[dict]]:
    group = QGroupBox("App And Window")
    layout = QGridLayout(group)
    layout.setColumnStretch(1, 1)
    widgets: dict[str, QWidget] = {}
    rows: list[dict] = []

    app_id_input = _make_line_edit()
    widgets["app_id_input"] = app_id_input
    _add_value_row(group, layout, 0, "app-id", app_id_input, rows)

    app_launch_url_input = _make_line_edit()
    widgets["app_launch_url_input"] = app_launch_url_input
    _add_value_row(group, layout, 1, "app-launch-url-for-shortcuts-menu-item", app_launch_url_input, rows)

    wm_class_input = _make_line_edit()
    widgets["wm_class_input"] = wm_class_input
    _add_value_row(group, layout, 2, "class", wm_class_input, rows)

    guest_check = _make_check_box()
    widgets["guest_check"] = guest_check
    _add_check_row(group, layout, 3, "guest", guest_check, rows)

    incognito_check = _make_check_box()
    widgets["incognito_check"] = incognito_check
    _add_check_row(group, layout, 4, "incognito", incognito_check, rows)

    kiosk_check = _make_check_box()
    widgets["kiosk_check"] = kiosk_check
    _add_check_row(group, layout, 5, "kiosk", kiosk_check, rows)

    wm_name_input = _make_line_edit()
    widgets["wm_name_input"] = wm_name_input
    _add_value_row(group, layout, 6, "name", wm_name_input, rows)

    new_window_check = _make_check_box()
    widgets["new_window_check"] = new_window_check
    _add_check_row(group, layout, 7, "new-window", new_window_check, rows)

    no_first_run_check = _make_check_box()
    widgets["no_first_run_check"] = no_first_run_check
    _add_check_row(group, layout, 8, "no-first-run", no_first_run_check, rows)

    start_fullscreen_check = _make_check_box()
    widgets["start_fullscreen_check"] = start_fullscreen_check
    _add_check_row(group, layout, 9, "start-fullscreen", start_fullscreen_check, rows)

    start_maximized_check = _make_check_box()
    widgets["start_maximized_check"] = start_maximized_check
    _add_check_row(group, layout, 10, "start-maximized", start_maximized_check, rows)

    window_position_input = _make_line_edit("50,50")
    widgets["window_position_input"] = window_position_input
    _add_value_row(group, layout, 11, "window-position", window_position_input, rows)

    window_size_input = _make_line_edit("1280,800")
    widgets["window_size_input"] = window_size_input
    _add_value_row(group, layout, 12, "window-size", window_size_input, rows)

    return group, widgets, rows


def _build_identity_group() -> tuple[QGroupBox, dict[str, QWidget], list[dict]]:
    group = QGroupBox("Identity And Profile")
    layout = QGridLayout(group)
    layout.setColumnStretch(1, 1)
    widgets: dict[str, QWidget] = {}
    rows: list[dict] = []

    disable_features_input = _make_line_edit()
    widgets["disable_features_input"] = disable_features_input
    _add_value_row(group, layout, 0, "disable-features", disable_features_input, rows)

    enable_features_input = _make_line_edit()
    widgets["enable_features_input"] = enable_features_input
    _add_value_row(group, layout, 1, "enable-features", enable_features_input, rows)

    lang_input = _make_line_edit("en-US")
    widgets["lang_input"] = lang_input
    _add_value_row(group, layout, 2, "lang", lang_input, rows)

    profile_directory_input = _make_line_edit("Default")
    widgets["profile_directory_input"] = profile_directory_input
    _add_value_row(group, layout, 3, "profile-directory", profile_directory_input, rows)

    user_data_dir_widget = _path_row_button("Browse")
    widgets["user_data_dir_input"] = user_data_dir_widget
    _add_value_row(group, layout, 4, "user-data-dir", user_data_dir_widget["widget"], rows)

    user_agent_input = _make_line_edit()
    widgets["user_agent_input"] = user_agent_input
    _add_value_row(group, layout, 5, "user-agent", user_agent_input, rows)

    return group, widgets, rows


def _build_rendering_group() -> tuple[QGroupBox, dict[str, QWidget], list[dict]]:
    group = QGroupBox("Rendering And Performance")
    layout = QGridLayout(group)
    layout.setColumnStretch(1, 1)
    widgets: dict[str, QWidget] = {}
    rows: list[dict] = []

    autoplay_policy_input = _make_line_edit()
    widgets["autoplay_policy_input"] = autoplay_policy_input
    _add_value_row(group, layout, 0, "autoplay-policy", autoplay_policy_input, rows)

    disable_dev_shm_usage_check = _make_check_box()
    widgets["disable_dev_shm_usage_check"] = disable_dev_shm_usage_check
    _add_check_row(group, layout, 1, "disable-dev-shm-usage", disable_dev_shm_usage_check, rows)

    disable_extensions_check = _make_check_box()
    widgets["disable_extensions_check"] = disable_extensions_check
    _add_check_row(group, layout, 2, "disable-extensions", disable_extensions_check, rows)

    disable_gpu_check = _make_check_box()
    widgets["disable_gpu_check"] = disable_gpu_check
    _add_check_row(group, layout, 3, "disable-gpu", disable_gpu_check, rows)

    disable_renderer_backgrounding_check = _make_check_box()
    widgets["disable_renderer_backgrounding_check"] = disable_renderer_backgrounding_check
    _add_check_row(group, layout, 4, "disable-renderer-backgrounding", disable_renderer_backgrounding_check, rows)

    disable_software_rasterizer_check = _make_check_box()
    widgets["disable_software_rasterizer_check"] = disable_software_rasterizer_check
    _add_check_row(group, layout, 5, "disable-software-rasterizer", disable_software_rasterizer_check, rows)

    disk_cache_dir_input = _make_line_edit()
    widgets["disk_cache_dir_input"] = disk_cache_dir_input
    _add_value_row(group, layout, 6, "disk-cache-dir", disk_cache_dir_input, rows)

    disk_cache_size_input = _make_line_edit()
    widgets["disk_cache_size_input"] = disk_cache_size_input
    _add_value_row(group, layout, 7, "disk-cache-size", disk_cache_size_input, rows)

    force_device_scale_factor_input = _make_line_edit("1.0")
    widgets["force_device_scale_factor_input"] = force_device_scale_factor_input
    _add_value_row(group, layout, 8, "force-device-scale-factor", force_device_scale_factor_input, rows)

    headless_check = _make_check_box()
    widgets["headless_check"] = headless_check
    _add_check_row(group, layout, 9, "headless", headless_check, rows)

    mute_audio_check = _make_check_box()
    widgets["mute_audio_check"] = mute_audio_check
    _add_check_row(group, layout, 10, "mute-audio", mute_audio_check, rows)

    ozone_platform_hint_input = _make_line_edit("auto")
    widgets["ozone_platform_hint_input"] = ozone_platform_hint_input
    _add_value_row(group, layout, 11, "ozone-platform-hint", ozone_platform_hint_input, rows)

    process_per_site_check = _make_check_box()
    widgets["process_per_site_check"] = process_per_site_check
    _add_check_row(group, layout, 12, "process-per-site", process_per_site_check, rows)

    single_process_check = _make_check_box()
    widgets["single_process_check"] = single_process_check
    _add_check_row(group, layout, 13, "single-process", single_process_check, rows)

    use_gl_input = _make_line_edit()
    widgets["use_gl_input"] = use_gl_input
    _add_value_row(group, layout, 14, "use-gl", use_gl_input, rows)

    virtual_time_budget_input = _make_line_edit()
    widgets["virtual_time_budget_input"] = virtual_time_budget_input
    _add_value_row(group, layout, 15, "virtual-time-budget", virtual_time_budget_input, rows)

    return group, widgets, rows


def _build_network_group() -> tuple[QGroupBox, dict[str, QWidget], list[dict]]:
    group = QGroupBox("Network And Security")
    layout = QGridLayout(group)
    layout.setColumnStretch(1, 1)
    widgets: dict[str, QWidget] = {}
    rows: list[dict] = []

    allow_insecure_localhost_check = _make_check_box()
    widgets["allow_insecure_localhost_check"] = allow_insecure_localhost_check
    _add_check_row(group, layout, 0, "allow-insecure-localhost", allow_insecure_localhost_check, rows)

    disable_background_networking_check = _make_check_box()
    widgets["disable_background_networking_check"] = disable_background_networking_check
    _add_check_row(group, layout, 1, "disable-background-networking", disable_background_networking_check, rows)

    disable_notifications_check = _make_check_box()
    widgets["disable_notifications_check"] = disable_notifications_check
    _add_check_row(group, layout, 2, "disable-notifications", disable_notifications_check, rows)

    disable_popup_blocking_check = _make_check_box()
    widgets["disable_popup_blocking_check"] = disable_popup_blocking_check
    _add_check_row(group, layout, 3, "disable-popup-blocking", disable_popup_blocking_check, rows)

    disable_web_security_check = _make_check_box()
    widgets["disable_web_security_check"] = disable_web_security_check
    _add_check_row(group, layout, 4, "disable-web-security", disable_web_security_check, rows)

    host_resolver_rules_input = _make_line_edit()
    widgets["host_resolver_rules_input"] = host_resolver_rules_input
    _add_value_row(group, layout, 5, "host-resolver-rules", host_resolver_rules_input, rows)

    ignore_certificate_errors_check = _make_check_box()
    widgets["ignore_certificate_errors_check"] = ignore_certificate_errors_check
    _add_check_row(group, layout, 6, "ignore-certificate-errors", ignore_certificate_errors_check, rows)

    no_sandbox_check = _make_check_box()
    widgets["no_sandbox_check"] = no_sandbox_check
    _add_check_row(group, layout, 7, "no-sandbox", no_sandbox_check, rows)

    proxy_bypass_input = _make_line_edit()
    widgets["proxy_bypass_input"] = proxy_bypass_input
    _add_value_row(group, layout, 8, "proxy-bypass-list", proxy_bypass_input, rows)

    proxy_pac_url_input = _make_line_edit()
    widgets["proxy_pac_url_input"] = proxy_pac_url_input
    _add_value_row(group, layout, 9, "proxy-pac-url", proxy_pac_url_input, rows)

    proxy_server_input = _make_line_edit()
    widgets["proxy_server_input"] = proxy_server_input
    _add_value_row(group, layout, 10, "proxy-server", proxy_server_input, rows)

    return group, widgets, rows


def _build_debug_group() -> tuple[QGroupBox, dict[str, QWidget], list[dict]]:
    group = QGroupBox("Debug And Automation")
    layout = QGridLayout(group)
    layout.setColumnStretch(1, 1)
    widgets: dict[str, QWidget] = {}
    rows: list[dict] = []

    auto_open_devtools_check = _make_check_box()
    widgets["auto_open_devtools_check"] = auto_open_devtools_check
    _add_check_row(group, layout, 0, "auto-open-devtools-for-tabs", auto_open_devtools_check, rows)

    enable_logging_check = _make_check_box()
    widgets["enable_logging_check"] = enable_logging_check
    _add_check_row(group, layout, 1, "enable-logging", enable_logging_check, rows)

    remote_debugging_port_input = _make_line_edit("9222")
    widgets["remote_debugging_port_input"] = remote_debugging_port_input
    _add_value_row(group, layout, 2, "remote-debugging-port", remote_debugging_port_input, rows)

    remote_debugging_pipe_check = _make_check_box()
    widgets["remote_debugging_pipe_check"] = remote_debugging_pipe_check
    _add_check_row(group, layout, 3, "remote-debugging-pipe", remote_debugging_pipe_check, rows)

    trace_startup_check = _make_check_box()
    widgets["trace_startup_check"] = trace_startup_check
    _add_check_row(group, layout, 4, "trace-startup", trace_startup_check, rows)

    trace_startup_file_input = _make_line_edit()
    widgets["trace_startup_file_input"] = trace_startup_file_input
    _add_value_row(group, layout, 5, "trace-startup-file", trace_startup_file_input, rows)

    vmodule_input = _make_line_edit()
    widgets["vmodule_input"] = vmodule_input
    _add_value_row(group, layout, 6, "vmodule", vmodule_input, rows)

    return group, widgets, rows


def _path_row_button(button_text: str) -> dict[str, QWidget]:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    line_edit = _make_line_edit()
    button = QPushButton(button_text)
    layout.addWidget(line_edit)
    layout.addWidget(button)
    return {"widget": widget, "line_edit": line_edit}
