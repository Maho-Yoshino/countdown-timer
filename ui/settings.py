if __name__ == "__main__":
    from sys import path as sp
    from os import path
    sp.append(path.abspath(path.join(path.dirname(__file__), '..')))

from datetime import date, datetime, timedelta
from logging import getLogger
from os import environ
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QRadioButton,
    QTabWidget,
    QGroupBox,
    QListWidget,
    QPlainTextEdit,
    QMessageBox,
    QColorDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QFrame,
    QDialog,
)

import modules.state as state

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
NONE_TOKEN = "<none>"


class ClassBox(QFrame):
    def __init__(self, *, lines, substituted, command, parent=None):
        super().__init__(parent)
        self._command = command
        self.setObjectName("classBox")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(56, 50)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        for line in lines:
            label = QLabel(line or "-", self)
            label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            label.setWordWrap(True)
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(label)
        if substituted:
            sep = QFrame(self)
            sep.setFrameShape(QFrame.HLine)
            sep.setFixedHeight(2)
            sep.setStyleSheet("background-color: #89470C; border: none;")
            layout.addWidget(sep)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._command is not None:
            self._command()
        super().mousePressEvent(event)


class ClickArea(QWidget):
    def __init__(self, *, on_click=None, on_double_click=None, parent=None):
        super().__init__(parent)
        self._on_click = on_click
        self._on_double_click = on_double_click
        self.setObjectName("emptySlot")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(46)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._on_click is not None:
            self._on_click()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._on_double_click is not None:
            self._on_double_click()
        super().mouseDoubleClickEvent(event)


class settingsGUI(QMainWindow):
    content: QWidget

    def __init__(self):
        self.logger = getLogger(__name__)
        if state.openGUIs.get("settings") is not None:
            state.openGUIs["settings"]._focus_window()
            return self.logger.debug("Settings opened more than once. Focus set to older window")

        super().__init__()
        state.openGUIs["settings"] = self

        self.bg = "#202020"
        self.fg = "#FFFFFF"
        self.surface = "#2B2B2B"
        self.accent = "#3A3A3A"

        self.setWindowTitle(state.settings.localization.settings.title)
        self.setStyleSheet(self._styleSheet())

        loc = state.settings.localization
        menu = self.menuBar()
        menu.addAction(loc.settings.topbar["schedule"], lambda: self._openSchedule())
        menu.addAction(loc.settings.topbar["classes"], lambda: self._openClasses())
        menu.addAction(loc.settings.topbar["special_days"], lambda: self._openSpecialDays())
        menu.addAction(loc.settings.topbar["general"], lambda: self._openGeneral())

        self.content = QWidget(self)
        self.setCentralWidget(self.content)
        self._content_layout = QVBoxLayout(self.content)
        self._content_layout.setContentsMargins(12, 12, 12, 12)

        self._confirm_class_delete = True
        self._schedule_anchor_date = state.getTime().date()
        self._schedule_view_mode = "week"
        self._settings_ui = getattr(state.settings.localization.settings, "ui", {})

        self._openSchedule()
        self.showMaximized()
        self._focus_window()

    def _styleSheet(self) -> str:
        return f"""
        QMainWindow, QDialog {{ background-color: {self.bg}; }}
        QWidget {{ color: {self.fg}; }}
        QLabel {{ background: transparent; color: {self.fg}; }}
        QPushButton {{ background-color: {self.surface}; color: {self.fg}; border: 1px solid {self.accent}; padding: 6px 10px; }}
        QPushButton:hover {{ background-color: {self.accent}; }}
        QLineEdit, QPlainTextEdit, QSpinBox {{ background-color: {self.surface}; color: {self.fg}; border: 1px solid {self.accent}; padding: 4px; }}
        QComboBox {{ background-color: {self.surface}; color: {self.fg}; border: 1px solid {self.accent}; padding: 4px; }}
        QListWidget {{ background-color: {self.surface}; color: {self.fg}; border: 1px solid {self.accent}; }}
        QListWidget::item:selected {{ background-color: {self.accent}; }}
        QCheckBox, QRadioButton {{ color: {self.fg}; }}
        QTabWidget::pane {{ border: 1px solid {self.accent}; }}
        QTabBar::tab {{ background-color: {self.surface}; color: {self.fg}; padding: 6px 12px; }}
        QTabBar::tab:selected {{ background-color: {self.accent}; }}
        QGroupBox {{ border: 1px solid {self.accent}; margin-top: 10px; padding-top: 8px; }}
        QGroupBox::title {{ color: {self.fg}; subcontrol-origin: margin; left: 8px; }}
        QMenuBar {{ background-color: {self.surface}; color: {self.fg}; }}
        QMenuBar::item:selected {{ background-color: {self.accent}; }}
        QMenu {{ background-color: {self.surface}; color: {self.fg}; }}
        QMenu::item:selected {{ background-color: {self.accent}; }}
        QScrollArea {{ border: none; }}
        #classBox {{ background-color: {self.surface}; border: 1px solid {self.accent}; }}
        #emptySlot {{ border: 1px dashed {self.accent}; }}
        """

    def _error(self, title: str, message: str, parent: QWidget | None = None):
        QMessageBox.critical(parent or self, title, message)

    def closeEvent(self, event):
        state.openGUIs.pop("settings", None)
        super().closeEvent(event)

    def _focus_window(self):
        try:
            self.show()
            self.raise_()
            self.activateWindow()
        except Exception:
            self.logger.exception("Could not force settings window focus")

    def _close_child_window(self, dialog: QWidget):
        dialog.close()
        dialog.deleteLater()
        self._focus_window()

    def _refresh_clock_runtime(self):
        state.settings.reload()
        state.clock.refreshFromSettings()

    def _clearContent(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _current_week_start(self) -> date:
        return self._schedule_anchor_date - timedelta(days=self._schedule_anchor_date.weekday())

    def _ui(self, key: str, default: str, **values) -> str:
        text = self._settings_ui.get(key, default)
        if values:
            return state.settings.localization.format(text, **values)
        return text

    def _day_name(self, day_index: int) -> str:
        return self._ui(f"day.{day_index}", DAY_NAMES[day_index])

    def _schedule_reference_datetime(self) -> datetime:
        return datetime.combine(self._schedule_anchor_date, datetime.min.time())

    def _visible_schedule_days(self) -> list[int]:
        if self._schedule_view_mode == "day":
            return [self._schedule_anchor_date.weekday()]
        if self._schedule_view_mode == "week":
            return [0, 1, 2, 3, 4]
        if self._schedule_view_mode == "week_with_saturday":
            return [0, 1, 2, 3, 4, 5]
        return [0, 1, 2, 3, 4, 5, 6]

    def _set_schedule_view_mode(self, mode: str):
        self._schedule_view_mode = mode
        self._openSchedule()

    def _navigate_schedule(self, direction: int):
        delta = 1 if self._schedule_view_mode == "day" else 7
        self._schedule_anchor_date += timedelta(days=direction * delta)
        self._openSchedule()

    def _show_schedule_today(self):
        today = state.getTime().date()
        if self._schedule_view_mode == "day":
            self._schedule_anchor_date = today
        else:
            self._schedule_anchor_date = today - timedelta(days=today.weekday())
        self._openSchedule()

    def _format_class_value(self, value) -> str:
        classes = state.settings.classes
        if value is None:
            return NONE_TOKEN
        if isinstance(value, list):
            formatted = []
            for item in value:
                if item is None:
                    formatted.append(NONE_TOKEN)
                elif isinstance(item, str):
                    formatted.append(item)
                elif isinstance(item, dict):
                    formatted.append(item.get("name", "custom"))
            return ", ".join(formatted)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            name = value.get("name", self._ui("common.custom", "custom"))
            teacher = value.get("teacher")
            return f"{name} ({teacher})" if teacher else name
        return str(value)

    def _class_option_label(self, code: str, data: dict[str, str]) -> str:
        return f"{data.get('teacher', '')}: {data.get('name', code)} ({data.get('room', '')})"

    def _class_option_lookup(self) -> dict[str, str | None]:
        return {self._ui("common.null_option", "Null"): None} | {
            self._class_option_label(code, data): code
            for code, data in sorted(state.settings.classes.items(), key=lambda item: self._class_option_label(item[0], item[1]).lower())
        }

    def _class_label_for_value(self, value, class_options: dict[str, str | None]) -> str:
        null_label = self._ui("common.null_option", "Null")
        if value is None:
            return null_label
        if isinstance(value, str) and value in state.settings.classes:
            label = self._class_option_label(value, state.settings.classes[value])
            if label in class_options:
                return label
        return null_label

    def _group_values_for_slot(self, value) -> list[object]:
        if isinstance(value, list):
            return value or [None]
        if value is None:
            return [None]
        return [value]

    def _visible_group_count(self, values: list[object]) -> int:
        if len(values) > 1:
            return len(values)
        return 1

    def _schedule_class_width(self, entries_by_day: dict[int, dict[int, object]]) -> int:
        longest = len("Wed")
        for day_entries in entries_by_day.values():
            for entry in day_entries.values():
                for value in entry.data or [None]:
                    if value is None:
                        continue
                    class_data = self._class_display_data(value)
                    longest = max(
                        longest,
                        len(class_data["name"]),
                        len(class_data["teacher"]),
                        len(class_data["room"]),
                    )
        return min(max(longest * 3 + 10, 48), 84)

    def _class_display_data(self, value) -> dict[str, str]:
        if all(hasattr(value, attr) for attr in ("name", "teacher", "room")):
            return {
                "name": value.name or "",
                "teacher": value.teacher or "",
                "room": value.room or "",
            }
        if isinstance(value, str):
            data = state.settings.classes.get(value, {})
            return {
                "name": data.get("name", value),
                "teacher": data.get("teacher", ""),
                "room": data.get("room", ""),
            }
        if isinstance(value, dict):
            return {
                "name": value.get("name", ""),
                "teacher": value.get("teacher", ""),
                "room": value.get("room", ""),
            }
        if isinstance(value, list):
            items = [self._class_display_data(item) for item in value if item is not None]
            return {
                "name": " / ".join(item["name"] for item in items if item["name"]),
                "teacher": " / ".join(item["teacher"] for item in items if item["teacher"]),
                "room": " / ".join(item["room"] for item in items if item["room"]),
            }
        return {"name": NONE_TOKEN, "teacher": "", "room": ""}

    def _teacher_display_value(self, value) -> str:
        return self._class_display_data(value)["teacher"].strip()

    def _substituted_groups(self, day_index: int, slot: int, week_start: date, value_count: int) -> list[bool]:
        key = (week_start + timedelta(days=day_index)).strftime("%Y-%m-%d")
        special_day = state.settings.events._data["specialDays"].get(key, {})
        classes = special_day.get("classes", {}) if isinstance(special_day, dict) else {}
        slot_key = str(slot)
        if slot_key not in classes:
            return [False] * value_count

        special_values = self._group_values_for_slot(classes[slot_key])
        usual_values = self._group_values_for_slot(self._raw_weekly_value(day_index, slot))
        substitutions = []
        for index in range(value_count):
            special_value = special_values[index] if index < len(special_values) else None
            usual_value = usual_values[index] if index < len(usual_values) else None
            special_teacher = self._teacher_display_value(special_value)
            usual_teacher = self._teacher_display_value(usual_value)
            substitutions.append(bool(special_teacher) and special_teacher != usual_teacher)
        return substitutions

    def _event_items(self, kind: str, date_key: str, slot: int) -> list[dict[str, object]]:
        return [
            item
            for item in state.settings.events._data[kind].get(date_key, [])
            if item.get("class") == slot
        ]

    def _class_alert_items(self, date_key: str, slot: int) -> list[tuple[int, dict[str, object]]]:
        return [
            (index, item)
            for index, item in enumerate(state.settings.events._data["alerts"])
            if item.get("classDate", item.get("date")) == date_key and item.get("class") == slot
        ]

    def _format_class_alert(self, alert: dict[str, object]) -> str:
        relative_to = "end" if alert.get("relativeTo") == "end" else "start"
        minutes = alert.get("minutes", 0)
        message = alert.get("message", "")
        base = self._ui("alerts.format.before_end", "before end") if relative_to == "end" else self._ui("alerts.format.since_start", "since start")
        keep = self._ui("common.keep", "keep") if alert.get("keep", False) else self._ui("common.once", "once")
        return f"{alert.get('time', '--:--')} | {minutes} min {base} | {keep} | {message}"

    def _create_grouped_class_cell(self, parent, *, values: list[object], substitutions: list[bool], command):
        cell = QWidget(parent)
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.setSpacing(2)
        values = values or [None]
        is_split = len(values) > 1
        for index, value in enumerate(values, start=1):
            group = QWidget(cell)
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(2)
            if is_split:
                group_label = QLabel(self._ui("schedule.group", "Group {index}", index=index), group)
                group_label.setAlignment(Qt.AlignLeft)
                group_layout.addWidget(group_label)
            if value is None:
                area = ClickArea(on_click=command, parent=group)
                group_layout.addWidget(area, stretch=1)
            else:
                class_data = self._class_display_data(value)
                box = ClassBox(
                    lines=[class_data["name"], class_data["teacher"], class_data["room"]],
                    substituted=substitutions[index - 1] if index - 1 < len(substitutions) else False,
                    command=command,
                    parent=group,
                )
                group_layout.addWidget(box, stretch=1)
            cell_layout.addWidget(group, stretch=1)
        return cell

    def _create_empty_slot_area(self, parent, *, day_index: int, slot: int):
        return ClickArea(
            on_double_click=lambda: self._open_assignment_prompt(day_index, slot),
            parent=parent,
        )

    def _slot_time_string(self, slot: int) -> str:
        return state.settings.schedule._data["timeSlots"].get(str(slot), "00:00-00:00")

    def _slot_time_parts(self, slot: int) -> tuple[str, str]:
        value = self._slot_time_string(slot)
        if "-" in value:
            start, end = value.split("-", 1)
            return start, end
        return "00:00", "00:00"

    def _open_time_slot_prompt(self, slot: int):
        start, end = self._slot_time_parts(slot)
        dialog = QDialog(self)
        dialog.setWindowTitle(self._ui("schedule.time_slot.title", "Set time for class {slot}", slot=slot))
        layout = QVBoxLayout(dialog)

        form = QGridLayout()
        form.addWidget(QLabel(self._ui("schedule.time_slot.start", "Start")), 0, 0)
        start_container, start_hour, start_minute = self._create_time_inputs(dialog, start=start)
        form.addWidget(start_container, 0, 1)
        form.addWidget(QLabel(self._ui("schedule.time_slot.end", "End")), 1, 0)
        end_container, end_hour, end_minute = self._create_time_inputs(dialog, start=end)
        form.addWidget(end_container, 1, 1)
        layout.addLayout(form)

        def save_time():
            try:
                start_str = self._time_from_vars(start_hour, start_minute)
                end_str = self._time_from_vars(end_hour, end_minute)
            except ValueError as exc:
                self._error(self._ui("schedule.time_slot.invalid.title", "Invalid time"), str(exc), dialog)
                return
            state.settings.schedule._data["timeSlots"][str(slot)] = f"{start_str}-{end_str}"
            state.settings.schedule.save()
            self._refresh_clock_runtime()
            self._openSchedule()
            dialog.accept()

        buttons = QHBoxLayout()
        save_btn = QPushButton(self._ui("assignment.save", "Save"))
        save_btn.clicked.connect(save_time)
        cancel_btn = QPushButton(self._ui("assignment.cancel", "Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        dialog.exec()

    def _open_assignment_prompt(self, day_index: int, slot: int, *, add_group: bool = False):
        class_options = self._class_option_lookup()
        option_labels = list(class_options.keys())
        if not option_labels:
            self._error(
                self._ui("assignment.no_classes.title", "No classes"),
                self._ui("assignment.no_classes.message", "Add classes to config/classes.json before assigning schedule slots."),
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(self._ui("assignment.dialog.title", "Add class to {day_name}", day_name=self._day_name(day_index)))
        layout = QVBoxLayout(dialog)

        current_value = self._raw_weekly_value(day_index, slot)
        group_values = self._group_values_for_slot(current_value)
        if add_group:
            group_values.append(None)
        secondary_var = str(slot) in state.settings.schedule._data["secondary"].get(str(day_index), {})

        class_selections: list[str] = []
        for value in group_values:
            class_selections.append(self._class_label_for_value(value, class_options))

        header = QHBoxLayout()
        header.addWidget(QLabel(self._ui("assignment.class_number", "Class number")))
        header.addWidget(QLabel(str(slot)))
        header.addStretch(1)
        layout.addLayout(header)

        start_str, end_str = self._slot_time_parts(slot)
        time_form = QGridLayout()
        time_form.addWidget(QLabel(self._ui("schedule.time_slot.start", "Start")), 0, 0)
        start_container, start_hour, start_minute = self._create_time_inputs(dialog, start=start_str)
        time_form.addWidget(start_container, 0, 1)
        time_form.addWidget(QLabel(self._ui("schedule.time_slot.end", "End")), 1, 0)
        end_container, end_hour, end_minute = self._create_time_inputs(dialog, start=end_str)
        time_form.addWidget(end_container, 1, 1)
        layout.addLayout(time_form)

        class_rows = QWidget(dialog)
        class_rows_layout = QVBoxLayout(class_rows)
        class_rows_layout.setContentsMargins(0, 0, 0, 0)
        class_rows_layout.setSpacing(4)
        layout.addWidget(class_rows)

        def set_selection(index: int, text: str):
            if index < len(class_selections):
                class_selections[index] = text

        def redraw_class_rows():
            while class_rows_layout.count():
                item = class_rows_layout.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()
                elif item.layout() is not None:
                    sub = item.layout()
                    while sub.count():
                        sub_item = sub.takeAt(0)
                        if sub_item.widget() is not None:
                            sub_item.widget().deleteLater()
            for index in range(len(class_selections)):
                row = QHBoxLayout()
                row.addWidget(QLabel(self._ui("assignment.class_label", "Class ({index})", index=index + 1)))
                combo = QComboBox()
                combo.addItems(option_labels)
                combo.setCurrentText(class_selections[index])
                combo.currentTextChanged.connect(lambda text, i=index: set_selection(i, text))
                row.addWidget(combo, stretch=1)
                class_rows_layout.addLayout(row)

        redraw_class_rows()

        secondary_check = QCheckBox(self._ui("assignment.secondary_only", "Set only for secondary week"))
        secondary_check.setChecked(secondary_var)
        layout.addWidget(secondary_check)

        one_day_check = QCheckBox(self._ui("assignment.day_only", "Set only for this day"))
        one_day_check.toggled.connect(lambda checked: secondary_check.setEnabled(not checked))
        layout.addWidget(one_day_check)

        def save_assignment():
            try:
                start_time = self._time_from_vars(start_hour, start_minute)
                end_time = self._time_from_vars(end_hour, end_minute)
            except ValueError as exc:
                self._error(self._ui("schedule.time_slot.invalid.title", "Invalid time"), str(exc), dialog)
                return
            time_value = f"{start_time}-{end_time}"
            selected_groups = [class_options[sel] for sel in class_selections]
            class_code = selected_groups[0] if len(selected_groups) == 1 else selected_groups
            if one_day_check.isChecked():
                date_key = (self._current_week_start() + timedelta(days=day_index)).strftime("%Y-%m-%d")
                special_day = state.settings.events._data["specialDays"].setdefault(date_key, {"full": False})
                special_day.setdefault("full", False)
                special_day.setdefault("classes", {})[str(slot)] = class_code
                special_day.setdefault("timeSlots", {})[str(slot)] = time_value
                state.settings.events.save()
            else:
                state.settings.schedule._data["timeSlots"][str(slot)] = time_value
                while len(state.settings.schedule._data["default"]) <= day_index:
                    state.settings.schedule._data["default"].append({})
                if secondary_check.isChecked():
                    state.settings.schedule._data["secondary"].setdefault(str(day_index), {})[str(slot)] = class_code
                else:
                    state.settings.schedule._data["default"][day_index][str(slot)] = class_code
                    state.settings.schedule._data["secondary"].get(str(day_index), {}).pop(str(slot), None)
                state.settings.schedule.save()
            self._openSchedule()
            dialog.accept()

        buttons = QHBoxLayout()
        save_btn = QPushButton(self._ui("assignment.save", "Save"))
        save_btn.clicked.connect(save_assignment)
        cancel_btn = QPushButton(self._ui("assignment.cancel", "Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)

        def split_class():
            class_selections.append(self._ui("common.null_option", "Null"))
            redraw_class_rows()
            dialog.adjustSize()

        def remove_split():
            if len(class_selections) > 1:
                class_selections.pop()
                redraw_class_rows()
                dialog.adjustSize()

        split_btn = QPushButton(self._ui("assignment.split", "Split class"))
        split_btn.clicked.connect(split_class)
        remove_split_btn = QPushButton(self._ui("assignment.remove_split", "Remove split"))
        remove_split_btn.clicked.connect(remove_split)
        buttons.addWidget(split_btn)
        buttons.addWidget(remove_split_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        dialog.exec()

    def _parse_class_entry(self, raw: str):
        text = raw.strip()
        if not text:
            return None
        parts = [part.strip() for part in text.split(",")]
        parsed = []
        for part in parts:
            if not part:
                continue
            if part.lower() == NONE_TOKEN.lower():
                parsed.append(None)
                continue
            if part not in state.settings.classes:
                raise ValueError(f"Unknown class code: {part}")
            parsed.append(part)
        if not parsed:
            return None
        if len(parsed) == 1:
            return parsed[0]
        return parsed

    def _parse_timestring(self, value: str) -> str:
        text = value.strip()
        datetime.strptime(text, "%H:%M")
        return text

    def _available_languages(self) -> list[str]:
        return sorted(path.stem for path in Path("lang").glob("*.json"))

    def _create_time_inputs(self, parent, *, start: str = ""):
        hour = 0
        minute = 0
        if start:
            parsed = datetime.strptime(start, "%H:%M")
            hour = parsed.hour
            minute = parsed.minute
        container = QWidget(parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        hour_spin = QSpinBox(container)
        hour_spin.setRange(0, 23)
        hour_spin.setWrapping(True)
        hour_spin.setValue(hour)
        hour_spin.setFixedWidth(60)
        minute_spin = QSpinBox(container)
        minute_spin.setRange(0, 59)
        minute_spin.setWrapping(True)
        minute_spin.setValue(minute)
        minute_spin.setFixedWidth(60)
        layout.addWidget(hour_spin)
        layout.addWidget(QLabel(":"))
        layout.addWidget(minute_spin)
        return container, hour_spin, minute_spin

    def _time_from_vars(self, hour_spin: QSpinBox, minute_spin: QSpinBox) -> str:
        hour = hour_spin.value()
        minute = minute_spin.value()
        if hour not in range(24) or minute not in range(60):
            raise ValueError("Invalid time value.")
        return f"{hour:02}:{minute:02}"

    def _create_date_inputs(self, parent, *, value: str | None = None):
        today = state.getTime().date()
        parsed = today
        if value:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        container = QWidget(parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        year_spin = QSpinBox(container)
        year_spin.setRange(today.year - 10, today.year + 10)
        year_spin.setWrapping(True)
        year_spin.setValue(parsed.year)
        year_spin.setFixedWidth(80)
        month_spin = QSpinBox(container)
        month_spin.setRange(1, 12)
        month_spin.setWrapping(True)
        month_spin.setValue(parsed.month)
        month_spin.setFixedWidth(60)
        day_spin = QSpinBox(container)
        day_spin.setRange(1, 31)
        day_spin.setWrapping(True)
        day_spin.setValue(parsed.day)
        day_spin.setFixedWidth(60)
        layout.addWidget(year_spin)
        layout.addWidget(QLabel("-"))
        layout.addWidget(month_spin)
        layout.addWidget(QLabel("-"))
        layout.addWidget(day_spin)
        layout.addStretch(1)
        return container, year_spin, month_spin, day_spin

    def _date_from_vars(self, year_spin: QSpinBox, month_spin: QSpinBox, day_spin: QSpinBox) -> str:
        value = date(year_spin.value(), month_spin.value(), day_spin.value())
        return value.strftime("%Y-%m-%d")

    def _class_editor_label(self, code: str, data: dict[str, str]) -> str:
        name = data.get("name", "").strip() or self._ui("classes.placeholder.name", "New class")
        teacher = data.get("teacher", "").strip()
        room = data.get("room", "").strip()
        details = " | ".join(part for part in (teacher, room) if part)
        return name + (f" ({details})" if details else "")

    def _new_class_code(self) -> str:
        base = self._ui("classes.placeholder.code", "NEW_CLASS").strip() or "NEW_CLASS"
        code = base
        index = 2
        while code in state.settings.classes:
            code = f"{base}_{index}"
            index += 1
        return code

    def _confirm_remove_class(self, class_label: str) -> bool:
        if not self._confirm_class_delete:
            return True

        dialog = QDialog(self)
        dialog.setWindowTitle(self._ui("classes.remove.title", "Remove class"))
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(self._ui("classes.remove.message", "Remove {class_label}?", class_label=class_label)))
        result = {"confirmed": False}

        def finish(confirmed: bool, disable_prompt: bool = False):
            result["confirmed"] = confirmed
            if confirmed and disable_prompt:
                self._confirm_class_delete = False
            dialog.accept()

        buttons = QHBoxLayout()
        remove_btn = QPushButton(self._ui("classes.button.remove", "Remove"))
        remove_btn.clicked.connect(lambda: finish(True))
        remove_no_prompt_btn = QPushButton(self._ui("classes.button.remove_no_prompt", "Remove and do not ask again"))
        remove_no_prompt_btn.clicked.connect(lambda: finish(True, True))
        cancel_btn = QPushButton(self._ui("assignment.cancel", "Cancel"))
        cancel_btn.clicked.connect(lambda: finish(False))
        buttons.addWidget(remove_btn)
        buttons.addWidget(remove_no_prompt_btn)
        buttons.addStretch(1)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        dialog.exec()
        return result["confirmed"]

    def _openClasses(self, selected_code: str | None = None):
        self._clearContent()
        if selected_code not in state.settings.classes:
            selected_code = None

        root = QWidget(self.content)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.addWidget(root)

        list_panel = QWidget(root)
        list_panel_layout = QVBoxLayout(list_panel)
        list_panel_layout.setContentsMargins(0, 0, 0, 0)
        list_panel_layout.setSpacing(6)
        root_layout.addWidget(list_panel, stretch=3 if selected_code else 1)

        list_panel_layout.addWidget(QLabel(self._ui("classes.title", "Classes")))
        class_list = QListWidget(list_panel)
        class_list.setObjectName("listBox")
        class_list.setMinimumWidth(220)
        list_panel_layout.addWidget(class_list, stretch=1)

        code_order = [
            code
            for code, _data in sorted(
                state.settings.classes.items(),
                key=lambda item: self._class_editor_label(item[0], item[1]).lower(),
            )
        ]
        for code in code_order:
            class_list.addItem(self._class_editor_label(code, state.settings.classes[code]))

        class_list.blockSignals(True)
        if selected_code in code_order:
            class_list.setCurrentRow(code_order.index(selected_code))
        class_list.blockSignals(False)
        class_list.currentRowChanged.connect(lambda row: self._openClasses(code_order[row]) if 0 <= row < len(code_order) else None)

        def add_class():
            code = self._new_class_code()
            state.settings.classes[code] = {
                "name": self._ui("classes.placeholder.name", "New class"),
                "room": self._ui("classes.placeholder.location", "New location"),
                "teacher": self._ui("classes.placeholder.teacher", "New teacher"),
            }
            state.settings.classes.save()
            self._refresh_clock_runtime()
            self._openClasses(code)

        add_btn = QPushButton(self._ui("classes.button.add", "Add"))
        add_btn.clicked.connect(add_class)
        list_panel_layout.addWidget(add_btn)

        if not selected_code:
            return

        selected_data = state.settings.classes[selected_code]
        editor = QWidget(root)
        editor_layout = QGridLayout(editor)
        root_layout.addWidget(editor, stretch=1)

        editor_layout.addWidget(QLabel(self._ui("classes.editor.title", "Edit class")), 0, 0, 1, 2)

        name_var = QLineEdit(selected_data.get("name", ""))
        location_var = QLineEdit(selected_data.get("room", ""))
        teacher_var = QLineEdit(selected_data.get("teacher", ""))

        fields = [
            (self._ui("classes.field.name", "Class name"), name_var),
            (self._ui("classes.field.location", "Class location"), location_var),
            (self._ui("classes.field.teacher", "Class teacher"), teacher_var),
        ]
        for row, (label, var) in enumerate(fields, start=1):
            editor_layout.addWidget(QLabel(label), row, 0)
            editor_layout.addWidget(var, row, 1)
        editor_layout.setColumnStretch(1, 1)

        def remove_class():
            class_label = self._class_editor_label(selected_code, selected_data)
            if not self._confirm_remove_class(class_label):
                return
            state.settings.classes.pop(selected_code, None)
            state.settings.classes.save()
            self._refresh_clock_runtime()
            self._openClasses()

        def save_class():
            state.settings.classes[selected_code] = {
                "name": name_var.text().strip(),
                "room": location_var.text().strip(),
                "teacher": teacher_var.text().strip(),
            }
            state.settings.classes.save()
            self._refresh_clock_runtime()
            self._openClasses(selected_code)

        buttons = QHBoxLayout()
        remove_btn = QPushButton(self._ui("classes.button.remove", "Remove"))
        remove_btn.clicked.connect(remove_class)
        save_btn = QPushButton(self._ui("classes.button.save", "Save"))
        save_btn.clicked.connect(save_class)
        buttons.addWidget(remove_btn)
        buttons.addStretch(1)
        buttons.addWidget(save_btn)
        editor_layout.addLayout(buttons, 4, 0, 1, 2)

    def _openSchedule(self):
        self._clearContent()
        root = QWidget(self.content)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.addWidget(root)

        week_start = self._current_week_start()
        visible_days = self._visible_schedule_days()

        top_bar = QWidget(root)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(top_bar)

        nav_section = QHBoxLayout()
        prev_btn = QPushButton(self._ui("schedule.nav.prev", "<"))
        prev_btn.setFixedWidth(36)
        prev_btn.clicked.connect(lambda: self._navigate_schedule(-1))
        next_btn = QPushButton(self._ui("schedule.nav.next", ">"))
        next_btn.setFixedWidth(36)
        next_btn.clicked.connect(lambda: self._navigate_schedule(1))
        today_btn = QPushButton(self._ui("schedule.nav.today", "Today"))
        today_btn.clicked.connect(self._show_schedule_today)
        nav_section.addWidget(prev_btn)
        nav_section.addWidget(next_btn)
        nav_section.addWidget(today_btn)
        nav_widget = QWidget()
        nav_widget.setLayout(nav_section)
        top_layout.addWidget(nav_widget)

        if self._schedule_view_mode == "day":
            center_text = self._ui(
                "schedule.title.day",
                "{day_name}, {date}",
                day_name=self._day_name(self._schedule_anchor_date.weekday()),
                date=self._schedule_anchor_date.strftime("%Y-%m-%d"),
            )
        else:
            last_day = week_start + timedelta(days=max(visible_days))
            center_text = self._ui(
                "schedule.title.week",
                "Week {week} ({start} - {end})",
                week=week_start.isocalendar().week,
                start=week_start.strftime("%Y-%m-%d"),
                end=last_day.strftime("%Y-%m-%d"),
            )
        center_section = QVBoxLayout()
        center_label = QLabel(center_text)
        center_label.setAlignment(Qt.AlignCenter)
        instruction_label = QLabel(self._ui(
            "schedule.instruction",
            "Click a class slot to edit the weekly schedule for that day. Use comma-separated class codes for grouped classes.",
        ))
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setWordWrap(True)
        center_section.addWidget(center_label)
        center_section.addWidget(instruction_label)
        center_widget = QWidget()
        center_widget.setLayout(center_section)
        top_layout.addWidget(center_widget, stretch=1)

        mode_section = QHBoxLayout()
        mode_buttons = [
            (self._ui("schedule.mode.day", "day"), "day"),
            (self._ui("schedule.mode.week", "week"), "week"),
            (self._ui("schedule.mode.week_with_saturday", "Week with Saturday"), "week_with_saturday"),
            (self._ui("schedule.mode.full_week", "Entire week"), "full_week"),
        ]
        for text, value in mode_buttons:
            radio = QRadioButton(text)
            radio.setChecked(value == self._schedule_view_mode)
            radio.toggled.connect(lambda checked, v=value: self._set_schedule_view_mode(v) if checked else None)
            mode_section.addWidget(radio)
        mode_widget = QWidget()
        mode_widget.setLayout(mode_section)
        top_layout.addWidget(mode_widget)

        unified = state.settings.schedule.getUnifiedSchedule(week_of=self._schedule_reference_datetime())
        entries_by_day = {
            day_index: {entry.classIndex: entry for entry in sorted(unified[day_index], key=lambda item: item.classIndex)}
            if day_index < len(unified)
            else {}
            for day_index in range(7)
        }
        slot_indexes = sorted({slot for day_index in visible_days for slot in entries_by_day[day_index]})
        max_groups_by_slot = {
            slot: max(
                self._visible_group_count(entries_by_day[day_index][slot].data or [None])
                for day_index in visible_days
                if slot in entries_by_day[day_index]
            )
            for slot in slot_indexes
        }
        max_groups_by_day = {
            day_index: max((self._visible_group_count(entry.data or [None]) for entry in day_entries.values()), default=1)
            for day_index, day_entries in entries_by_day.items()
        }
        class_box_width = self._schedule_class_width(entries_by_day)

        scroll = QScrollArea(root)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root_layout.addWidget(scroll, stretch=1)

        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(2)
        scroll.setWidget(grid_host)

        time_column_width = 104
        grid.setColumnMinimumWidth(0, time_column_width)
        grid.addWidget(QLabel(""), 0, 0)

        for column_index, day_index in enumerate(visible_days, start=1):
            header = (week_start + timedelta(days=day_index)).strftime("%a\n%Y-%m-%d")
            header_label = QLabel(header)
            header_label.setAlignment(Qt.AlignCenter)
            header_label.setWordWrap(True)
            header_label.setMinimumWidth(max(class_box_width * max_groups_by_day[day_index], 48))
            grid.addWidget(header_label, 0, column_index)

        for row_index, slot_index in enumerate(slot_indexes, start=1):
            slot_btn = QPushButton(f"{slot_index}\n{self._slot_time_string(slot_index)}")
            slot_btn.setFlat(True)
            slot_btn.setCursor(Qt.PointingHandCursor)
            slot_btn.setToolTip(self._ui("schedule.time_slot.tooltip", "Click to set the start and end time"))
            slot_btn.clicked.connect(lambda checked, s=slot_index: self._open_time_slot_prompt(s))
            grid.addWidget(slot_btn, row_index, 0)

            for column_index, day_index in enumerate(visible_days, start=1):
                entry = entries_by_day[day_index].get(slot_index)
                if entry is None:
                    cell = self._create_empty_slot_area(grid_host, day_index=day_index, slot=slot_index)
                    grid.addWidget(cell, row_index, column_index)
                else:
                    values = entry.data or [None]
                    cell = self._create_grouped_class_cell(
                        grid_host,
                        values=values,
                        substitutions=self._substituted_groups(day_index, entry.classIndex, week_start, len(values)),
                        command=lambda d=day_index, s=entry.classIndex, e=entry: self._open_class_slot(d, s, e),
                    )
                    grid.addWidget(cell, row_index, column_index)

        add_row = len(slot_indexes) + 1
        grid.addWidget(QLabel(""), add_row, 0)
        for column_index, day_index in enumerate(visible_days, start=1):
            next_slot = max(entries_by_day[day_index], default=0) + 1
            add_slot_btn = QPushButton(self._ui("schedule.add_slot", "Add slot"))
            add_slot_btn.clicked.connect(lambda checked, d=day_index, s=next_slot: self._open_assignment_prompt(d, s))
            grid.addWidget(add_slot_btn, add_row, column_index)

    def _raw_weekly_value(self, day_index: int, slot: int):
        schedule_data = state.settings.schedule._data
        is_secondary = state.settings.schedule.currentlySecondaryWeek(self._schedule_anchor_date)
        if is_secondary:
            slot_value = schedule_data["secondary"].get(str(day_index), {}).get(str(slot), None)
            if slot_value is not None or str(slot) in schedule_data["secondary"].get(str(day_index), {}):
                return slot_value
        if day_index >= len(schedule_data["default"]):
            return None
        return schedule_data["default"][day_index].get(str(slot))

    def _open_class_slot(self, day_index: int, slot: int, entry):
        dialog = QDialog(self)
        dialog.setWindowTitle(self._ui("class_slot.dialog.title", "{day_name} class", day_name=self._day_name(day_index)))
        dialog.resize(520, 420)

        week_start = self._current_week_start()
        class_date = week_start + timedelta(days=day_index)
        date_key = class_date.strftime("%Y-%m-%d")
        class_data = self._class_display_data(entry.data)

        layout = QVBoxLayout(dialog)
        notebook = QTabWidget(dialog)
        layout.addWidget(notebook)

        class_tab = QWidget()
        events_tab = QWidget()
        alerts_tab = QWidget()
        notebook.addTab(class_tab, self._ui("class_slot.tab.class_data", "Class data"))
        notebook.addTab(events_tab, self._ui("class_slot.tab.events", "Events"))
        notebook.addTab(alerts_tab, self._ui("class_slot.tab.alerts", "Alerts"))

        rows = [
            (self._ui("class_slot.row.date", "Date"), date_key),
            (self._ui("class_slot.row.time", "Time"), f"{entry.start.strftime('%H:%M')}-{entry.end.strftime('%H:%M')}"),
            (self._ui("class_slot.row.class_name", "Class name"), class_data["name"]),
            (self._ui("class_slot.row.teacher_name", "Teacher name"), class_data["teacher"]),
            (self._ui("class_slot.row.room", "Room"), class_data["room"]),
            (self._ui("class_slot.row.class_index", "Class number in the day"), str(slot)),
        ]

        class_tab_layout = QVBoxLayout(class_tab)
        info_grid = QGridLayout()
        for row, (label, value) in enumerate(rows):
            info_grid.addWidget(QLabel(label), row, 0)
            info_grid.addWidget(QLabel(value or "-"), row, 1)
        info_grid.setColumnStretch(1, 1)
        class_tab_layout.addLayout(info_grid)

        class_buttons = QHBoxLayout()
        change_btn = QPushButton(self._ui("class_slot.button.change", "Change class"))
        change_btn.clicked.connect(lambda: (dialog.accept(), self._open_assignment_prompt(day_index, slot)))
        add_group_btn = QPushButton(self._ui("class_slot.button.add_group", "Add group"))
        add_group_btn.clicked.connect(lambda: (dialog.accept(), self._open_assignment_prompt(day_index, slot, add_group=True)))
        delete_slot_btn = QPushButton(self._ui("class_slot.button.delete_slot", "Delete slot"))
        delete_slot_btn.clicked.connect(lambda: self._delete_weekly_slot(day_index, slot, dialog))
        class_buttons.addWidget(change_btn)
        class_buttons.addWidget(add_group_btn)
        class_buttons.addWidget(delete_slot_btn)
        class_buttons.addStretch(1)
        class_tab_layout.addLayout(class_buttons)
        class_tab_layout.addStretch(1)

        homework_label = self._ui("events.type.homework", "Homework")
        exam_label = self._ui("events.type.exam", "Exam")

        events_tab_layout = QVBoxLayout(events_tab)
        homework_list = QListWidget()
        homework_list.setObjectName("listBox")
        exam_list = QListWidget()
        exam_list.setObjectName("listBox")

        def refresh_events():
            homework_list.clear()
            exam_list.clear()
            for item in self._event_items("homework", date_key, slot):
                homework_list.addItem(item.get("topic", ""))
            for item in self._event_items("exams", date_key, slot):
                exam_list.addItem(item.get("topic", ""))

        events_tab_layout.addWidget(QLabel(homework_label))
        events_tab_layout.addWidget(homework_list, stretch=1)
        events_tab_layout.addWidget(QLabel(exam_label))
        events_tab_layout.addWidget(exam_list, stretch=1)

        event_form = QHBoxLayout()
        event_type_combo = QComboBox()
        event_type_combo.addItems([homework_label, exam_label])
        event_topic = QLineEdit()
        event_form.addWidget(event_type_combo)
        event_form.addWidget(event_topic, stretch=1)
        events_tab_layout.addLayout(event_form)

        def add_event():
            topic = event_topic.text().strip()
            if not topic:
                self._error(
                    self._ui("events.invalid.title", "Invalid event"),
                    self._ui("events.invalid.message", "Event text is required."),
                    dialog,
                )
                return
            key = "homework" if event_type_combo.currentText() == homework_label else "exams"
            state.settings.events._data[key].setdefault(date_key, []).append({"class": slot, "topic": topic})
            state.settings.events.save()
            event_topic.clear()
            refresh_events()
            self._refresh_clock_runtime()

        def remove_event():
            if homework_list.currentRow() >= 0:
                key = "homework"
                listbox = homework_list
            elif exam_list.currentRow() >= 0:
                key = "exams"
                listbox = exam_list
            else:
                return
            selected_index = listbox.currentRow()
            seen = -1
            kept = []
            for item in state.settings.events._data[key].get(date_key, []):
                if item.get("class") == slot:
                    seen += 1
                    if seen == selected_index:
                        continue
                kept.append(item)
            if kept:
                state.settings.events._data[key][date_key] = kept
            else:
                state.settings.events._data[key].pop(date_key, None)
            state.settings.events.save()
            refresh_events()
            self._refresh_clock_runtime()

        event_buttons = QHBoxLayout()
        add_btn = QPushButton(self._ui("events.button.add", "Add"))
        add_btn.clicked.connect(add_event)
        remove_btn = QPushButton(self._ui("events.button.remove", "Remove"))
        remove_btn.clicked.connect(remove_event)
        event_buttons.addWidget(add_btn)
        event_buttons.addWidget(remove_btn)
        event_buttons.addStretch(1)
        events_tab_layout.addLayout(event_buttons)
        refresh_events()

        alerts_tab_layout = QVBoxLayout(alerts_tab)
        info_label = QLabel(self._ui("alerts.info", "Alert time is calculated relative to the beginning or end of this class."))
        info_label.setWordWrap(True)
        alerts_tab_layout.addWidget(info_label)
        alert_list = QListWidget()
        alert_list.setObjectName("listBox")
        alerts_tab_layout.addWidget(alert_list, stretch=1)
        current_alert_indexes: list[int] = []

        def refresh_alerts():
            current_alert_indexes.clear()
            alert_list.clear()
            for alert_index, alert in self._class_alert_items(date_key, slot):
                current_alert_indexes.append(alert_index)
                alert_list.addItem(self._format_class_alert(alert))

        def remove_alert():
            if alert_list.currentRow() < 0:
                return
            alert_index = current_alert_indexes[alert_list.currentRow()]
            state.settings.events._data["alerts"].pop(alert_index)
            state.settings.events.save()
            refresh_alerts()
            self._refresh_clock_runtime()

        def open_alert_prompt(alert_index: int | None = None):
            existing_alert = state.settings.events._data["alerts"][alert_index] if alert_index is not None else {}
            alert_dialog = QDialog(dialog)
            alert_dialog.setWindowTitle(
                self._ui("alerts.dialog.edit_title", "Edit alert")
                if alert_index is not None
                else self._ui("alerts.dialog.add_title", "Add alert")
            )
            alert_layout = QGridLayout(alert_dialog)

            relative_group = QGroupBox(self._ui("alerts.calculate_from", "Calculate from"))
            rg_layout = QVBoxLayout(relative_group)
            relative_end_rb = QRadioButton(self._ui("alerts.from_end", "End of class"))
            relative_start_rb = QRadioButton(self._ui("alerts.from_start", "Beginning of class"))
            if existing_alert.get("relativeTo", "end") == "end":
                relative_end_rb.setChecked(True)
            else:
                relative_start_rb.setChecked(True)
            rg_layout.addWidget(relative_end_rb)
            rg_layout.addWidget(relative_start_rb)
            alert_layout.addWidget(relative_group, 0, 0, 1, 2)

            alert_layout.addWidget(QLabel(self._ui("alerts.message", "Message")), 1, 0)
            message_box = QPlainTextEdit()
            message_box.setPlainText(existing_alert.get("message", ""))
            message_box.setFixedHeight(70)
            alert_layout.addWidget(message_box, 1, 1)

            keep_check = QCheckBox(self._ui("alerts.keep_after", "Keep alert after firing"))
            keep_check.setChecked(bool(existing_alert.get("keep", False)))
            alert_layout.addWidget(keep_check, 2, 0, 1, 2)

            alert_layout.addWidget(QLabel(self._ui("alerts.minutes", "Minutes since start/before end")), 3, 0)
            minutes_spin = QSpinBox()
            minutes_spin.setRange(0, 240)
            minutes_spin.setValue(int(existing_alert.get("minutes", 5)))
            alert_layout.addWidget(minutes_spin, 3, 1)

            def relative_value() -> str:
                return "end" if relative_end_rb.isChecked() else "start"

            def save_alert():
                try:
                    minutes = minutes_spin.value()
                    base_time = entry.end if relative_value() == "end" else entry.start
                    class_dt = datetime.combine(class_date, base_time) + timedelta(seconds=state.settings.schedule.delay)
                    alert_dt = class_dt - timedelta(minutes=minutes) if relative_value() == "end" else class_dt + timedelta(minutes=minutes)
                    message = message_box.toPlainText().strip()
                    payload = {
                        "date": alert_dt.strftime("%Y-%m-%d"),
                        "classDate": date_key,
                        "class": slot,
                        "time": alert_dt.strftime("%H:%M"),
                        "message": message or state.settings.localization.alert.defaultText,
                        "keep": keep_check.isChecked(),
                        "relativeTo": relative_value(),
                        "minutes": minutes,
                    }
                    if alert_index is None:
                        state.settings.events._data["alerts"].append(payload)
                    else:
                        state.settings.events._data["alerts"][alert_index] = payload
                    state.settings.events.save()
                    refresh_alerts()
                    self._refresh_clock_runtime()
                    alert_dialog.accept()
                except Exception as exc:
                    self._error(self._ui("alerts.invalid.title", "Invalid alert"), str(exc), alert_dialog)

            button_row = QHBoxLayout()
            save_alert_btn = QPushButton(self._ui("assignment.save", "Save"))
            save_alert_btn.clicked.connect(save_alert)
            cancel_alert_btn = QPushButton(self._ui("assignment.cancel", "Cancel"))
            cancel_alert_btn.clicked.connect(alert_dialog.reject)
            button_row.addWidget(save_alert_btn)
            button_row.addWidget(cancel_alert_btn)
            button_row.addStretch(1)
            alert_layout.addLayout(button_row, 4, 0, 1, 2)
            alert_dialog.exec()

        def edit_selected_alert(_item=None):
            if alert_list.currentRow() >= 0:
                open_alert_prompt(current_alert_indexes[alert_list.currentRow()])

        alert_list.itemDoubleClicked.connect(edit_selected_alert)

        alert_buttons = QHBoxLayout()
        remove_selected_btn = QPushButton(self._ui("alerts.button.remove_selected", "Remove selected alert"))
        remove_selected_btn.clicked.connect(remove_alert)
        add_new_btn = QPushButton(self._ui("alerts.button.add_new", "Add new alert"))
        add_new_btn.clicked.connect(lambda: open_alert_prompt())
        alert_buttons.addWidget(remove_selected_btn)
        alert_buttons.addWidget(add_new_btn)
        alert_buttons.addStretch(1)
        alerts_tab_layout.addLayout(alert_buttons)
        refresh_alerts()

        dialog.exec()

    def _delete_weekly_slot(self, day_index: int, slot: int, dialog: QDialog | None = None):
        if day_index < len(state.settings.schedule._data["default"]):
            state.settings.schedule._data["default"][day_index].pop(str(slot), None)
        state.settings.schedule._data["secondary"].get(str(day_index), {}).pop(str(slot), None)
        state.settings.schedule.save()
        if dialog is not None:
            dialog.accept()
        self._refresh_clock_runtime()
        self._openSchedule()

    def _openSpecialDays(self):
        self._clearContent()
        root = QWidget(self.content)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.addWidget(root)

        left = QWidget(root)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        root_layout.addWidget(left)

        left_layout.addWidget(QLabel(self._ui("special_days.title", "Special days")))
        day_list = QListWidget(left)
        day_list.setObjectName("listBox")
        day_list.setMinimumWidth(180)
        left_layout.addWidget(day_list, stretch=1)
        for key in sorted(state.settings.events._data["specialDays"]):
            day_list.addItem(key)

        right = QWidget(root)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(6)
        root_layout.addWidget(right, stretch=1)

        right_layout.addWidget(QLabel(self._ui("special_days.date", "Date")))
        date_frame, year_spin, month_spin, day_spin = self._create_date_inputs(right, value=state.getTime().strftime("%Y-%m-%d"))
        right_layout.addWidget(date_frame)

        full_check = QCheckBox(self._ui("special_days.replace_day", "Replace entire day"))
        right_layout.addWidget(full_check)

        right_layout.addWidget(QLabel(self._ui("special_days.rows_help", "Rows: slot | start | end | classes")))

        row_container = QWidget(right)
        row_container_layout = QVBoxLayout(row_container)
        row_container_layout.setContentsMargins(0, 0, 0, 0)
        row_container_layout.setSpacing(4)
        right_layout.addWidget(row_container, stretch=1)
        rows: list[dict[str, object]] = []

        def add_row(slot="", start="", end="", value=""):
            row_frame = QWidget(row_container)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(0, 0, 0, 0)
            slot_edit = QLineEdit(str(slot))
            slot_edit.setFixedWidth(50)
            start_container, start_hour_spin, start_minute_spin = self._create_time_inputs(row_frame, start=start)
            end_container, end_hour_spin, end_minute_spin = self._create_time_inputs(row_frame, start=end)
            value_edit = QLineEdit(value)
            remove_btn = QPushButton(self._ui("special_days.button.remove_row", "X"))
            remove_btn.setFixedWidth(32)
            remove_btn.clicked.connect(lambda checked, frame=row_frame: remove_row(frame))
            row_layout.addWidget(slot_edit)
            row_layout.addWidget(start_container)
            row_layout.addWidget(end_container)
            row_layout.addWidget(value_edit, stretch=1)
            row_layout.addWidget(remove_btn)
            row_container_layout.addWidget(row_frame)
            rows.append({
                "frame": row_frame,
                "slot": slot_edit,
                "start_hour": start_hour_spin,
                "start_minute": start_minute_spin,
                "end_hour": end_hour_spin,
                "end_minute": end_minute_spin,
                "value": value_edit,
            })

        def remove_row(row_frame: QWidget):
            for index, row in enumerate(list(rows)):
                if row["frame"] is row_frame:
                    rows.pop(index)
                    break
            row_frame.deleteLater()

        def clear_rows():
            for row in list(rows):
                row["frame"].deleteLater()
            rows.clear()

        def load_special_day(_row=None):
            clear_rows()
            if day_list.currentRow() < 0:
                return
            key = day_list.currentItem().text()
            parsed_date = datetime.strptime(key, "%Y-%m-%d").date()
            year_spin.setValue(parsed_date.year)
            month_spin.setValue(parsed_date.month)
            day_spin.setValue(parsed_date.day)
            data = state.settings.events._data["specialDays"].get(key, {})
            full_check.setChecked(bool(data.get("full", False)))
            classes = data.get("classes", {}) or {}
            slot_times = data.get("timeSlots", {}) or {}
            slot_keys = sorted({*classes.keys(), *slot_times.keys()}, key=lambda item: int(item))
            for slot_key in slot_keys:
                times = slot_times.get(slot_key, state.settings.schedule._data["timeSlots"].get(slot_key, "-"))
                start, end = times.split("-", 1) if "-" in times else ("", "")
                class_value = self._format_class_value(classes[slot_key]) if slot_key in classes else ""
                add_row(slot_key, start, end, class_value)
            if not slot_keys:
                add_row()

        day_list.currentRowChanged.connect(load_special_day)

        def new_special_day():
            try:
                key = self._date_from_vars(year_spin, month_spin, day_spin)
            except ValueError:
                self._error(
                    self._ui("special_days.invalid_date.title", "Invalid date"),
                    self._ui("special_days.invalid_date.message", "Use a valid date."),
                )
                return
            if not any(day_list.item(i).text() == key for i in range(day_list.count())):
                day_list.addItem(key)
            state.settings.events._data["specialDays"].setdefault(key, {"full": False})
            self._refresh_clock_runtime()
            day_list.setCurrentRow(day_list.count() - 1)

        button_bar = QHBoxLayout()
        add_row_btn = QPushButton(self._ui("special_days.button.add_row", "Add row"))
        add_row_btn.clicked.connect(lambda: add_row())
        new_date_btn = QPushButton(self._ui("special_days.button.new_date", "New date"))
        new_date_btn.clicked.connect(new_special_day)
        button_bar.addWidget(add_row_btn)
        button_bar.addWidget(new_date_btn)
        button_bar.addStretch(1)
        right_layout.addLayout(button_bar)

        def save_special_day():
            try:
                key = self._date_from_vars(year_spin, month_spin, day_spin)
            except ValueError:
                self._error(
                    self._ui("special_days.invalid_date.title", "Invalid date"),
                    self._ui("special_days.invalid_date.message", "Use a valid date."),
                )
                return

            payload: dict[str, object] = {"full": full_check.isChecked()}
            classes: dict[str, object] = {}
            time_slots: dict[str, str] = {}
            try:
                for row in rows:
                    slot = row["slot"].text().strip()
                    if not slot:
                        continue
                    int(slot)
                    start = self._time_from_vars(row["start_hour"], row["start_minute"])
                    end = self._time_from_vars(row["end_hour"], row["end_minute"])
                    value = row["value"].text().strip()
                    time_slots[slot] = f"{start}-{end}"
                    if value:
                        classes[slot] = self._parse_class_entry(value)
            except Exception as exc:
                self._error(self._ui("special_days.invalid_day.title", "Invalid special day"), str(exc))
                return

            if classes:
                payload["classes"] = classes
            if time_slots:
                payload["timeSlots"] = time_slots
            state.settings.events._data["specialDays"][key] = payload
            state.settings.events.save()
            self._refresh_clock_runtime()
            self._openSpecialDays()

        def delete_special_day():
            if day_list.currentRow() < 0:
                return
            key = day_list.currentItem().text()
            state.settings.events._data["specialDays"].pop(key, None)
            state.settings.events.save()
            self._refresh_clock_runtime()
            self._openSpecialDays()

        footer = QHBoxLayout()
        save_btn = QPushButton(self._ui("special_days.button.save", "Save special day"))
        save_btn.clicked.connect(save_special_day)
        delete_btn = QPushButton(self._ui("special_days.button.delete", "Delete"))
        delete_btn.clicked.connect(delete_special_day)
        footer.addWidget(save_btn)
        footer.addWidget(delete_btn)
        footer.addStretch(1)
        right_layout.addLayout(footer)

        add_row()

    def _openGeneral(self):
        self._clearContent()
        root = QWidget(self.content)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.addWidget(root)

        cfg = state.settings.config
        background_edit = QLineEdit(f"#{cfg.background:06X}")
        foreground_edit = QLineEdit(f"#{cfg.foreground:06X}")
        lang_options = self._available_languages()
        lang_combo = QComboBox()
        lang_combo.addItems(lang_options)
        lang_combo.setCurrentText(cfg.lang if cfg.lang in lang_options else (lang_options[0] if lang_options else cfg.lang))
        ignore_updates_check = QCheckBox(self._ui("general.ignore_updates", "Ignore updates"))
        ignore_updates_check.setChecked(cfg.ignoreUpdates)
        show_teacher_check = QCheckBox(self._ui("general.show_teacher", "Show teacher"))
        show_teacher_check.setChecked(cfg.showTeacher)
        alpha_default_edit = QLineEdit(str(cfg.alpha.get("default", 0.75)))
        alpha_hover_edit = QLineEdit(str(cfg.alpha.get("onHover", 0.25)))
        wayland_session = bool(
            environ.get("WAYLAND_DISPLAY") or
            environ.get("XDG_SESSION_TYPE") == "wayland"
        )
        alpha_hover_edit.setEnabled(not wayland_session)

        fields = QGridLayout()
        items = [
            (self._ui("general.label.background", "Background"), background_edit),
            (self._ui("general.label.foreground", "Foreground"), foreground_edit),
            (self._ui("general.label.language", "Language"), lang_combo),
            (self._ui("general.label.alpha_default", "Alpha default"), alpha_default_edit),
            (self._ui("general.label.alpha_hover", "Alpha on hover"), alpha_hover_edit),
        ]
        for row, (label, widget) in enumerate(items):
            fields.addWidget(QLabel(label), row, 0)
            fields.addWidget(widget, row, 1)
        fields.setColumnStretch(1, 1)
        fields.addWidget(ignore_updates_check, 5, 0, 1, 2)
        fields.addWidget(show_teacher_check, 6, 0, 1, 2)
        root_layout.addLayout(fields)

        def choose_color(edit: QLineEdit):
            initial = QColor(edit.text()) if edit.text() else QColor("#FFFFFF")
            color = QColorDialog.getColor(initial, self)
            if color.isValid():
                edit.setText(color.name().upper())

        color_buttons = QHBoxLayout()
        pick_bg_btn = QPushButton(self._ui("general.pick_background", "Pick background"))
        pick_bg_btn.clicked.connect(lambda: choose_color(background_edit))
        pick_fg_btn = QPushButton(self._ui("general.pick_foreground", "Pick foreground"))
        pick_fg_btn.clicked.connect(lambda: choose_color(foreground_edit))
        color_buttons.addWidget(pick_bg_btn)
        color_buttons.addWidget(pick_fg_btn)
        color_buttons.addStretch(1)
        root_layout.addLayout(color_buttons)

        def save_general():
            try:
                bg = background_edit.text().strip()
                fg = foreground_edit.text().strip()
                if not (bg.startswith("#") and len(bg) == 7):
                    raise ValueError(self._ui("general.invalid.background", "Background must be #RRGGBB"))
                if not (fg.startswith("#") and len(fg) == 7):
                    raise ValueError(self._ui("general.invalid.foreground", "Foreground must be #RRGGBB"))
                int(bg.removeprefix("#"), 16)
                int(fg.removeprefix("#"), 16)
                cfg._data["background"] = bg.upper()
                cfg._data["foreground"] = fg.upper()
                cfg._data["lang"] = lang_combo.currentText().strip() or cfg._data["lang"]
                cfg._data["ignoreUpdates"] = ignore_updates_check.isChecked()
                cfg._data["showTeacher"] = show_teacher_check.isChecked()
                cfg.setAlpha("default", float(alpha_default_edit.text().strip()))
                cfg.setAlpha("onHover", float(alpha_hover_edit.text().strip()))
                cfg.save()
                try:
                    state.clock.setWindowOpacity(cfg.alpha["default"])
                except Exception:
                    self.logger.exception("Could not refresh clock colors from settings UI")
                self._openGeneral()
            except Exception as exc:
                self._error(self._ui("general.invalid.title", "Invalid settings"), str(exc))
            self._refresh_clock_runtime()

        save_btn = QPushButton(self._ui("general.save", "Save general settings"))
        save_btn.clicked.connect(save_general)
        root_layout.addWidget(save_btn, alignment=Qt.AlignLeft)
        root_layout.addStretch(1)
