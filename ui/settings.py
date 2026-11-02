if __name__ == "__main__":
    from sys import path as sp
    from os import path
    sp.append(path.abspath(path.join(path.dirname(__file__), '..')))

from ctypes import windll
from datetime import date, datetime, timedelta
from logging import getLogger
from pathlib import Path
from tkinter import (
    BooleanVar,
    Canvas,
    Checkbutton,
    END,
    Frame,
    Listbox,
    Menu,
    Radiobutton,
    StringVar,
    Text,
    Toplevel,
    colorchooser,
    messagebox,
)
from tkinter import ttk

import modules.state as state

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
NONE_TOKEN = "<none>"


class settingsGUI(Toplevel):
    content: Frame

    def __init__(self):
        self.logger = getLogger(__name__)
        if state.openGUIs.get("settings") is not None:
            state.openGUIs["settings"]._focus_window()
            return self.logger.debug("Settings opened more than once. Focus set to older window")

        super().__init__(state.clock)
        state.openGUIs["settings"] = self
        self.protocol("WM_DELETE_WINDOW", self._closeFunc)

        self.bg = "#202020"
        self.fg = "#FFFFFF"
        self.surface = "#2B2B2B"
        self.accent = "#3A3A3A"
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self.style.configure("TFrame", background=self.bg)
        self.style.configure("TLabel", foreground=self.fg, background=self.bg)
        self.style.configure("mainText.Label", foreground=self.fg, background=self.bg)
        self.style.configure("TButton", foreground=self.fg, background=self.surface)
        self.style.map("TButton", background=[("active", self.accent)])
        self.style.configure("scheduleElement.TButton", padding=8, foreground=self.fg, background=self.surface)
        self.style.map("scheduleElement.TButton", background=[("active", self.accent)])
        self.style.configure("TLabelframe", background=self.bg, foreground=self.fg)
        self.style.configure("TLabelframe.Label", background=self.bg, foreground=self.fg)
        self.style.configure("TEntry", fieldbackground=self.surface, foreground=self.fg, insertcolor=self.fg)
        self.style.configure("TCombobox", fieldbackground=self.surface, foreground=self.fg, background=self.surface, arrowcolor=self.fg)
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.surface)],
            foreground=[("readonly", self.fg)],
            selectbackground=[("readonly", self.accent)],
            selectforeground=[("readonly", self.fg)],
        )
        self.style.configure("TSpinbox", fieldbackground=self.surface, foreground=self.fg, background=self.surface, arrowcolor=self.fg)
        self.style.configure("TCheckbutton", background=self.bg, foreground=self.fg)
        self.style.configure("TRadiobutton", background=self.bg, foreground=self.fg)
        self.style.map("TRadiobutton", background=[("active", self.bg)], foreground=[("active", self.fg)])
        self.style.configure("TNotebook", background=self.bg)
        self.style.configure("TNotebook.Tab", foreground=self.fg, background=self.surface)
        self.configure(background=self.bg)
        self._schedule_anchor_date = state.getTime().date()
        self._schedule_view_mode = "week"

        loc = state.settings.localization
        self._settings_ui = getattr(loc.settings, "ui", {})
        self.title(loc.settings.title)
        self.state("zoomed")

        menu = Menu(self, background=self.bg, fg=self.fg, relief="ridge", activebackground=self.accent, activeforeground=self.fg)
        menu.add_command(label=loc.settings.topbar["schedule"], command=self._openSchedule)
        menu.add_command(label=loc.settings.topbar["classes"], command=self._openClasses)
        menu.add_command(label=loc.settings.topbar["general"], command=self._openGeneral)
        self.config(menu=menu)

        self.content = Frame(self, bg=self.bg)
        self.content.pack(fill="both", expand=True, padx=12, pady=12)
        self._confirm_class_delete = True
        self._openSchedule()
        self.after(0, self._focus_window)

    def _closeFunc(self):
        state.openGUIs.pop("settings", None)
        self.destroy()

    def _refresh_clock_runtime(self):
        state.settings.reload()
        state.clock.refreshFromSettings()

    def _focus_window(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(100, lambda: self.attributes("-topmost", False))
            windll.user32.ShowWindow(self.winfo_id(), 9)
            windll.user32.SetForegroundWindow(self.winfo_id())
        except Exception:
            self.logger.exception("Could not force settings window focus")

    def _close_child_window(self, dialog: Toplevel):
        dialog.destroy()
        self.after(0, self._focus_window)

    def _clearContent(self):
        self.unbind("<Up>")
        self.unbind("<Down>")
        for child in self.content.winfo_children():
            child.destroy()

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

    def _style_tk_frame(self, widget: Frame):
        widget.configure(bg=self.bg)

    def _style_listbox(self, widget: Listbox):
        widget.configure(
            bg=self.surface,
            fg=self.fg,
            selectbackground=self.accent,
            selectforeground=self.fg,
            highlightbackground=self.bg,
            highlightcolor=self.accent,
        )

    def _style_text(self, widget: Text):
        widget.configure(
            bg=self.surface,
            fg=self.fg,
            insertbackground=self.fg,
            highlightbackground=self.bg,
            highlightcolor=self.accent,
        )

    def _style_checkbutton(self, widget: Checkbutton):
        widget.configure(
            bg=self.bg,
            fg=self.fg,
            activebackground=self.bg,
            activeforeground=self.fg,
            selectcolor=self.surface,
        )

    def _style_radiobutton(self, widget: Radiobutton):
        widget.configure(
            bg=self.bg,
            fg=self.fg,
            activebackground=self.bg,
            activeforeground=self.fg,
            selectcolor=self.fg,
            highlightthickness=0,
        )

    def _style_dialog(self, widget: Toplevel):
        widget.configure(bg=self.bg)

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

    def _redraw_class_box(self, canvas: Canvas, lines: list[str], substituted: bool):
        canvas.delete("all")
        width = max(canvas.winfo_width(), 56)
        height = max(canvas.winfo_height(), 46)
        canvas.create_rectangle(1, 1, width - 2, height - 2, fill=self.surface, outline=self.accent)
        y = 8
        for line in lines:
            canvas.create_text(5, y, text=line or "-", anchor="w", fill=self.fg, font=state.fontSize(7), width=max(width - 10, 46))
            y += 14
        if substituted:
            canvas.create_line(5, height - 5, width - 5, height - 5, fill="#89470C", width=2, capstyle="round")

    def _create_class_box(self, parent, *, lines: list[str], substituted: bool, command):
        canvas = Canvas(parent, bg=self.bg, highlightthickness=0, width=56, height=50, cursor="hand2")
        canvas.bind("<Configure>", lambda _event: self._redraw_class_box(canvas, lines, substituted))
        canvas.bind("<Button-1>", lambda _event: command())
        return canvas

    def _create_grouped_class_cell(self, parent, *, values: list[object], substitutions: list[bool], command):
        cell = ttk.Frame(parent)
        cell.bind("<Button-1>", lambda _event: command())
        values = values or [None]
        is_split = len(values) > 1
        for index, value in enumerate(values, start=1):
            group = ttk.Frame(cell)
            group.pack(side="left", fill="both", expand=True, padx=(0 if index == 1 else 2, 0))
            if is_split:
                ttk.Label(group, text=self._ui("schedule.group", "Group {index}", index=index), anchor="w").pack(fill="x")
            if value is None:
                empty_area = Frame(group, bg=self.bg, cursor="hand2", height=50)
                empty_area.bind("<Button-1>", lambda _event: command())
                empty_area.pack(fill="both", expand=True)
            else:
                class_data = self._class_display_data(value)
                box = self._create_class_box(
                    group,
                    lines=[class_data["name"], class_data["teacher"], class_data["room"]],
                    substituted=substitutions[index - 1] if index - 1 < len(substitutions) else False,
                    command=command,
                )
                box.pack(fill="both", expand=True)
        return cell

    def _create_empty_slot_area(self, parent, *, day_index: int, slot: int):
        frame = Frame(parent, bg=self.bg, cursor="hand2")
        frame.bind("<Double-Button-1>", lambda _event: self._open_assignment_prompt(day_index, slot))
        return frame

    def _slot_time_string(self, slot: int) -> str:
        return state.settings.schedule._data["timeSlots"].get(str(slot), "00:00-00:00")

    def _open_assignment_prompt(self, day_index: int, slot: int, *, add_group: bool = False):
        class_options = self._class_option_lookup()
        option_labels = list(class_options.keys())
        if not option_labels:
            return messagebox.showerror(
                self._ui("assignment.no_classes.title", "No classes"),
                self._ui("assignment.no_classes.message", "Add classes to config/classes.json before assigning schedule slots."),
                parent=self,
            )

        dialog = Toplevel(self)
        self._style_dialog(dialog)
        dialog.title(self._ui("assignment.dialog.title", "Add class to {day_name}", day_name=self._day_name(day_index)))
        dialog.transient(self)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._close_child_window(dialog))

        current_value = self._raw_weekly_value(day_index, slot)
        group_values = self._group_values_for_slot(current_value)
        if add_group:
            group_values.append(None)
        class_vars: list[StringVar] = []
        secondary_var = BooleanVar(value=str(slot) in state.settings.schedule._data["secondary"].get(str(day_index), {}))
        one_day_var = BooleanVar(value=False)

        ttk.Label(dialog, text=self._ui("assignment.class_number", "Class number")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        ttk.Label(dialog, text=str(slot), style="mainText.Label").grid(row=0, column=1, sticky="w", padx=10, pady=(10, 4))

        class_rows = ttk.Frame(dialog)
        class_rows.grid(row=1, column=0, columnspan=2, sticky="ew")
        class_rows.grid_columnconfigure(1, weight=1)
        dropdown_width = max(len(label) for label in option_labels) + 2

        def redraw_class_rows():
            for child in class_rows.winfo_children():
                child.destroy()
            for index, var in enumerate(class_vars, start=1):
                ttk.Label(class_rows, text=self._ui("assignment.class_label", "Class ({index})", index=index)).grid(row=index - 1, column=0, sticky="w", padx=10, pady=4)
                ttk.Combobox(
                    class_rows,
                    textvariable=var,
                    values=option_labels,
                    state="readonly",
                    width=dropdown_width,
                ).grid(row=index - 1, column=1, sticky="ew", padx=10, pady=4)

        for value in group_values:
            class_vars.append(StringVar(value=self._class_label_for_value(value, class_options)))
        redraw_class_rows()

        secondary_check = Checkbutton(dialog, text=self._ui("assignment.secondary_only", "Set only for secondary week"), variable=secondary_var)
        self._style_checkbutton(secondary_check)
        secondary_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=4)

        def toggle_one_day():
            if one_day_var.get():
                secondary_var.set(False)
                secondary_check.configure(state="disabled")
            else:
                secondary_check.configure(state="normal")

        one_day_check = Checkbutton(dialog, text=self._ui("assignment.day_only", "Set only for this day"), variable=one_day_var, command=toggle_one_day)
        self._style_checkbutton(one_day_check)
        one_day_check.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=4)
        dialog.grid_columnconfigure(1, weight=1)

        def save_assignment():
            selected_groups = [class_options[var.get()] for var in class_vars]
            class_code = selected_groups[0] if len(selected_groups) == 1 else selected_groups
            if one_day_var.get():
                date_key = (self._current_week_start() + timedelta(days=day_index)).strftime("%Y-%m-%d")
                special_day = state.settings.events._data["specialDays"].setdefault(date_key, {"full": False})
                special_day.setdefault("full", False)
                special_day.setdefault("classes", {})[str(slot)] = class_code
                special_day.setdefault("timeSlots", {})[str(slot)] = self._slot_time_string(slot)
                state.settings.events.save()
            else:
                state.settings.schedule._data["timeSlots"].setdefault(str(slot), self._slot_time_string(slot))
                while len(state.settings.schedule._data["default"]) <= day_index:
                    state.settings.schedule._data["default"].append({})
                if secondary_var.get():
                    state.settings.schedule._data["secondary"].setdefault(str(day_index), {})[str(slot)] = class_code
                else:
                    state.settings.schedule._data["default"][day_index][str(slot)] = class_code
                    state.settings.schedule._data["secondary"].get(str(day_index), {}).pop(str(slot), None)
                state.settings.schedule.save()
            self._openSchedule()
            self._close_child_window(dialog)

        buttons = ttk.Frame(dialog)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        ttk.Button(buttons, text=self._ui("assignment.save", "Save"), command=save_assignment).pack(side="left")
        ttk.Button(buttons, text=self._ui("assignment.cancel", "Cancel"), command=lambda: self._close_child_window(dialog)).pack(side="left", padx=(6, 0))

        def split_class():
            class_vars.append(StringVar(value=self._ui("common.null_option", "Null")))
            redraw_class_rows()
            dialog.update_idletasks()
            dialog.geometry(f"{dialog.winfo_reqwidth()}x{dialog.winfo_reqheight()}")

        def remove_split():
            if len(class_vars) > 1:
                class_vars.pop()
                redraw_class_rows()
                dialog.update_idletasks()
                dialog.geometry(f"{dialog.winfo_reqwidth()}x{dialog.winfo_reqheight()}")

        ttk.Button(buttons, text=self._ui("assignment.split", "Split class"), command=split_class).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text=self._ui("assignment.remove_split", "Remove split"), command=remove_split).pack(side="left", padx=(6, 0))
        dialog.update_idletasks()
        dialog.geometry(f"{dialog.winfo_reqwidth()}x{dialog.winfo_reqheight()}")
        self._refresh_clock_runtime()

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
        hour_var = StringVar(value="00")
        minute_var = StringVar(value="00")
        if start:
            parsed = datetime.strptime(start, "%H:%M")
            hour_var.set(f"{parsed.hour:02}")
            minute_var.set(f"{parsed.minute:02}")
        frame = ttk.Frame(parent)
        ttk.Spinbox(frame, from_=0, to=23, width=3, format="%02.0f", textvariable=hour_var, wrap=True).pack(side="left")
        ttk.Label(frame, text=":").pack(side="left")
        ttk.Spinbox(frame, from_=0, to=59, width=3, format="%02.0f", textvariable=minute_var, wrap=True).pack(side="left")
        return frame, hour_var, minute_var

    def _time_from_vars(self, hour_var: StringVar, minute_var: StringVar) -> str:
        hour = int(hour_var.get())
        minute = int(minute_var.get())
        if hour not in range(24) or minute not in range(60):
            raise ValueError("Invalid time value.")
        return f"{hour:02}:{minute:02}"

    def _create_date_inputs(self, parent, *, value: str | None = None):
        today = state.getTime().date()
        parsed = today
        if value:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        year_var = StringVar(value=str(parsed.year))
        month_var = StringVar(value=f"{parsed.month:02}")
        day_var = StringVar(value=f"{parsed.day:02}")
        frame = ttk.Frame(parent)
        ttk.Spinbox(frame, from_=today.year - 10, to=today.year + 10, width=5, textvariable=year_var, wrap=True).pack(side="left")
        ttk.Label(frame, text="-").pack(side="left")
        ttk.Spinbox(frame, from_=1, to=12, width=3, format="%02.0f", textvariable=month_var, wrap=True).pack(side="left")
        ttk.Label(frame, text="-").pack(side="left")
        ttk.Spinbox(frame, from_=1, to=31, width=3, format="%02.0f", textvariable=day_var, wrap=True).pack(side="left")
        return frame, year_var, month_var, day_var

    def _date_from_vars(self, year_var: StringVar, month_var: StringVar, day_var: StringVar) -> str:
        value = date(int(year_var.get()), int(month_var.get()), int(day_var.get()))
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

        dialog = Toplevel(self)
        self._style_dialog(dialog)
        dialog.title(self._ui("classes.remove.title", "Remove class"))
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        result = {"confirmed": False}
        ttk.Label(
            dialog,
            text=self._ui("classes.remove.message", "Remove {class_label}?", class_label=class_label),
            wraplength=360,
            justify="left",
        ).pack(fill="x", padx=12, pady=(12, 10))

        def finish(confirmed: bool, disable_prompt: bool = False):
            result["confirmed"] = confirmed
            if confirmed and disable_prompt:
                self._confirm_class_delete = False
            self._close_child_window(dialog)

        buttons = ttk.Frame(dialog)
        buttons.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(buttons, text=self._ui("classes.button.remove", "Remove"), command=lambda: finish(True)).pack(side="left")
        ttk.Button(
            buttons,
            text=self._ui("classes.button.remove_no_prompt", "Remove and do not ask again"),
            command=lambda: finish(True, True),
        ).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text=self._ui("assignment.cancel", "Cancel"), command=lambda: finish(False)).pack(side="right")

        dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        dialog.update_idletasks()
        dialog.geometry(f"{dialog.winfo_reqwidth()}x{dialog.winfo_reqheight()}")
        self.wait_window(dialog)
        return result["confirmed"]

    def _openClasses(self, selected_code: str | None = None):
        self._clearContent()
        if selected_code not in state.settings.classes:
            selected_code = None

        root = ttk.Frame(self.content)
        root.pack(fill="both", expand=True)
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=3 if selected_code else 1)
        if selected_code:
            root.grid_columnconfigure(1, weight=1, minsize=260)

        list_panel = ttk.Frame(root)
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12 if selected_code else 0))
        list_panel.grid_rowconfigure(1, weight=1)
        list_panel.grid_columnconfigure(0, weight=1)

        ttk.Label(list_panel, text=self._ui("classes.title", "Classes"), style="mainText.Label").grid(row=0, column=0, sticky="w")
        class_list = Listbox(list_panel, exportselection=False)
        self._style_listbox(class_list)
        class_list.grid(row=1, column=0, sticky="nsew", pady=(8, 8))

        code_order = [
            code
            for code, _data in sorted(
                state.settings.classes.items(),
                key=lambda item: self._class_editor_label(item[0], item[1]).lower(),
            )
        ]
        for code in code_order:
            class_list.insert(END, self._class_editor_label(code, state.settings.classes[code]))

        if selected_code in code_order:
            selected_index = code_order.index(selected_code)
            class_list.selection_set(selected_index)
            class_list.activate(selected_index)
            class_list.see(selected_index)

        def navigate_class(direction: int):
            if not code_order:
                return "break"
            selection = class_list.curselection()
            if selection:
                next_index = selection[0] + direction
            elif selected_code in code_order:
                next_index = code_order.index(selected_code) + direction
            else:
                next_index = 0 if direction > 0 else len(code_order) - 1
            next_index = max(0, min(next_index, len(code_order) - 1))
            self._openClasses(code_order[next_index])
            return "break"

        def select_class(_event=None):
            selection = class_list.curselection()
            if not selection:
                return self._openClasses()
            self._openClasses(code_order[selection[0]])

        class_list.bind("<<ListboxSelect>>", select_class)
        class_list.bind("<Up>", lambda _event: navigate_class(-1))
        class_list.bind("<Down>", lambda _event: navigate_class(1))
        self.bind("<Up>", lambda _event: navigate_class(-1))
        self.bind("<Down>", lambda _event: navigate_class(1))

        def add_class():
            code = self._new_class_code()
            state.settings.classes._data[code] = {
                "name": self._ui("classes.placeholder.name", "New class"),
                "room": self._ui("classes.placeholder.location", "New location"),
                "teacher": self._ui("classes.placeholder.teacher", "New teacher"),
            }
            state.settings.classes.save()
            self._refresh_clock_runtime()
            self._openClasses(code)

        ttk.Button(list_panel, text=self._ui("classes.button.add", "Add"), command=add_class).grid(row=2, column=0, sticky="ew")

        if not selected_code:
            return

        selected_data = state.settings.classes[selected_code]
        editor = ttk.Frame(root)
        editor.grid(row=0, column=1, sticky="nsew")
        editor.grid_columnconfigure(1, weight=1)

        ttk.Label(editor, text=self._ui("classes.editor.title", "Edit class"), style="mainText.Label").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        name_var = StringVar(value=selected_data.get("name", ""))
        location_var = StringVar(value=selected_data.get("room", ""))
        teacher_var = StringVar(value=selected_data.get("teacher", ""))

        fields = [
            (self._ui("classes.field.name", "Class name"), name_var),
            (self._ui("classes.field.location", "Class location"), location_var),
            (self._ui("classes.field.teacher", "Class teacher"), teacher_var),
        ]
        for row, (label, var) in enumerate(fields, start=1):
            ttk.Label(editor, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            entry = ttk.Entry(editor, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            entry.bind("<Up>", lambda _event: navigate_class(-1))
            entry.bind("<Down>", lambda _event: navigate_class(1))

        def remove_class():
            class_label = self._class_editor_label(selected_code, selected_data)
            if not self._confirm_remove_class(class_label):
                return
            state.settings.classes._data.pop(selected_code, None)
            state.settings.classes.save()
            self._refresh_clock_runtime()
            self._openClasses()

        def save_class():
            state.settings.classes._data[selected_code] = {
                "name": name_var.get().strip(),
                "room": location_var.get().strip(),
                "teacher": teacher_var.get().strip(),
            }
            state.settings.classes.save()
            self._refresh_clock_runtime()
            self._openClasses(selected_code)

        buttons = ttk.Frame(editor)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text=self._ui("classes.button.remove", "Remove"), command=remove_class).pack(side="left")
        ttk.Button(buttons, text=self._ui("classes.button.save", "Save"), command=save_class).pack(side="right")

    def _openSchedule(self):
        self._clearContent()
        root = ttk.Frame(self.content)
        root.pack(fill="both", expand=True)

        week_start = self._current_week_start()
        visible_days = self._visible_schedule_days()

        top_bar = ttk.Frame(root)
        top_bar.pack(fill="x", pady=(0, 12))
        top_bar.grid_columnconfigure(0, weight=1, uniform="schedule_top")
        top_bar.grid_columnconfigure(1, weight=1, uniform="schedule_top")
        top_bar.grid_columnconfigure(2, weight=1, uniform="schedule_top")

        nav_section = ttk.Frame(top_bar)
        nav_section.grid(row=0, column=0, sticky="w")
        ttk.Button(nav_section, text=self._ui("schedule.nav.prev", "<"), width=3, command=lambda: self._navigate_schedule(-1)).pack(side="left")
        ttk.Button(nav_section, text=self._ui("schedule.nav.next", ">"), width=3, command=lambda: self._navigate_schedule(1)).pack(side="left", padx=(6, 0))
        ttk.Button(nav_section, text=self._ui("schedule.nav.today", "Today"), command=self._show_schedule_today).pack(side="left", padx=(8, 0))

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
        center_section = ttk.Frame(top_bar)
        center_section.grid(row=0, column=1, sticky="nsew", padx=(12, 12))
        ttk.Label(center_section, text=center_text, style="mainText.Label", anchor="center", justify="center").pack(fill="x")
        instruction_label = ttk.Label(
            center_section,
            text=self._ui(
                "schedule.instruction",
                "Click a class slot to edit the weekly schedule for that day. Use comma-separated class codes for grouped classes.",
            ),
            style="mainText.Label",
            anchor="center",
            justify="center",
        )
        instruction_label.pack(fill="x")
        center_section.bind("<Configure>", lambda event: instruction_label.configure(wraplength=max(event.width - 24, 120)))

        mode_section = ttk.Frame(top_bar)
        mode_section.grid(row=0, column=2, sticky="e")
        mode_var = StringVar(value=self._schedule_view_mode)
        mode_buttons = [
            (self._ui("schedule.mode.day", "day"), "day"),
            (self._ui("schedule.mode.week", "week"), "week"),
            (self._ui("schedule.mode.week_with_saturday", "Week with Saturday"), "week_with_saturday"),
            (self._ui("schedule.mode.full_week", "Entire week"), "full_week"),
        ]
        for text, value in mode_buttons:
            mode_button = Radiobutton(
                mode_section,
                text=text,
                value=value,
                variable=mode_var,
                command=lambda v=value: self._set_schedule_view_mode(v),
            )
            self._style_radiobutton(mode_button)
            mode_button.pack(side="left", padx=(0, 6))

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

        schedule_outer = ttk.Frame(root)
        schedule_outer.pack(fill="both", expand=True, pady=(0, 18))
        schedule_canvas = Canvas(schedule_outer, bg=self.bg, highlightthickness=0, height=300)
        schedule_vscroll = ttk.Scrollbar(schedule_outer, orient="vertical", command=schedule_canvas.yview)
        schedule_hscroll = ttk.Scrollbar(schedule_outer, orient="horizontal", command=schedule_canvas.xview)
        schedule_canvas.configure(yscrollcommand=schedule_vscroll.set, xscrollcommand=schedule_hscroll.set)
        schedule_canvas.grid(row=0, column=0, sticky="nsew")
        schedule_vscroll.grid(row=0, column=1, sticky="ns")
        schedule_hscroll.grid(row=1, column=0, sticky="ew")
        schedule_outer.grid_columnconfigure(0, weight=1)
        schedule_outer.grid_rowconfigure(0, weight=1)

        schedule_grid = ttk.Frame(schedule_canvas)
        schedule_window = schedule_canvas.create_window((0, 0), window=schedule_grid, anchor="nw")

        def update_schedule_scrollregion(_event=None):
            schedule_canvas.configure(scrollregion=schedule_canvas.bbox("all"))
            bbox = schedule_canvas.bbox("all")
            if bbox and bbox[2] > schedule_canvas.winfo_width():
                schedule_hscroll.grid()
            else:
                schedule_hscroll.grid_remove()

        def resize_schedule_grid(event):
            schedule_canvas.itemconfigure(schedule_window, width=max(event.width, schedule_grid.winfo_reqwidth()))

        def bind_schedule_wheel(_event=None):
            schedule_canvas.bind_all("<MouseWheel>", on_schedule_wheel)
            schedule_canvas.bind_all("<Shift-MouseWheel>", on_schedule_shift_wheel)

        def unbind_schedule_wheel(_event=None):
            schedule_canvas.unbind_all("<MouseWheel>")
            schedule_canvas.unbind_all("<Shift-MouseWheel>")

        def on_schedule_wheel(event):
            schedule_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_schedule_shift_wheel(event):
            schedule_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        schedule_grid.bind("<Configure>", update_schedule_scrollregion)
        schedule_canvas.bind("<Configure>", resize_schedule_grid)
        schedule_canvas.bind("<Enter>", bind_schedule_wheel)
        schedule_canvas.bind("<Leave>", unbind_schedule_wheel)
        schedule_grid.bind("<Enter>", bind_schedule_wheel)
        schedule_grid.bind("<Leave>", unbind_schedule_wheel)

        time_column_width = 104
        schedule_grid.grid_columnconfigure(0, weight=0, minsize=time_column_width)
        ttk.Label(schedule_grid, text="", anchor="center").grid(row=0, column=0, sticky="nsew", padx=2, pady=(0, 2))

        for column_index, day_index in enumerate(visible_days, start=1):
            schedule_grid.grid_columnconfigure(column_index, weight=1, minsize=class_box_width * max_groups_by_day[day_index])
            header = (week_start + timedelta(days=day_index)).strftime("%a\n%Y-%m-%d")
            header_label = ttk.Label(
                schedule_grid,
                text=header,
                anchor="center",
                justify="center",
                wraplength=max(class_box_width * max_groups_by_day[day_index], 48),
            )
            header_label.grid(
                row=0,
                column=column_index,
                sticky="nsew",
                padx=2,
                pady=(0, 2),
            )

        for row_index, slot_index in enumerate(slot_indexes, start=1):
            schedule_grid.grid_rowconfigure(row_index, weight=1, uniform="schedule_slots", minsize=72 if max_groups_by_slot[slot_index] > 1 else 56)
            slot_label = ttk.Label(
                schedule_grid,
                text=f"{slot_index}\n{self._slot_time_string(slot_index)}",
                anchor="center",
                justify="center",
                style="mainText.Label",
                wraplength=time_column_width - 8,
            )
            slot_label.grid(row=row_index, column=0, sticky="nsew", padx=2, pady=2)

            for column_index, day_index in enumerate(visible_days, start=1):
                entry = entries_by_day[day_index].get(slot_index)
                if entry is None:
                    self._create_empty_slot_area(schedule_grid, day_index=day_index, slot=slot_index).grid(
                        row=row_index,
                        column=column_index,
                        sticky="nsew",
                        padx=2,
                        pady=2,
                    )
                else:
                    values = entry.data or [None]
                    class_box = self._create_grouped_class_cell(
                        schedule_grid,
                        values=values,
                        substitutions=self._substituted_groups(day_index, entry.classIndex, week_start, len(values)),
                        command=lambda d=day_index, s=entry.classIndex, e=entry: self._open_class_slot(d, s, e),
                    )
                    class_box.grid(row=row_index, column=column_index, sticky="nsew", padx=2, pady=2)

        add_row = len(slot_indexes) + 1
        schedule_grid.grid_rowconfigure(add_row, weight=1, uniform="schedule_slots", minsize=36)
        ttk.Label(schedule_grid, text="", anchor="center").grid(row=add_row, column=0, sticky="nsew", padx=2, pady=2)
        for column_index, day_index in enumerate(visible_days, start=1):
            next_slot = max(entries_by_day[day_index], default=0) + 1
            ttk.Button(
                schedule_grid,
                text=self._ui("schedule.add_slot", "Add slot"),
                command=lambda d=day_index, s=next_slot: self._open_assignment_prompt(d, s),
            ).grid(
                row=add_row,
                column=column_index,
                sticky="nsew",
                padx=2,
                pady=2,
            )

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
        dialog = Toplevel(self)
        self._style_dialog(dialog)
        dialog.title(self._ui("class_slot.dialog.title", "{day_name} class", day_name=self._day_name(day_index)))
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("460x380")
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._close_child_window(dialog))

        week_start = self._current_week_start()
        class_date = week_start + timedelta(days=day_index)
        date_key = class_date.strftime("%Y-%m-%d")
        class_data = self._class_display_data(entry.data)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        class_tab = ttk.Frame(notebook)
        events_tab = ttk.Frame(notebook)
        alerts_tab = ttk.Frame(notebook)
        notebook.add(class_tab, text=self._ui("class_slot.tab.class_data", "Class data"))
        notebook.add(events_tab, text=self._ui("class_slot.tab.events", "Events"))
        notebook.add(alerts_tab, text=self._ui("class_slot.tab.alerts", "Alerts"))

        rows = [
            (self._ui("class_slot.row.date", "Date"), date_key),
            (self._ui("class_slot.row.time", "Time"), f"{entry.start.strftime('%H:%M')}-{entry.end.strftime('%H:%M')}"),
            (self._ui("class_slot.row.class_name", "Class name"), class_data["name"]),
            (self._ui("class_slot.row.teacher_name", "Teacher name"), class_data["teacher"]),
            (self._ui("class_slot.row.room", "Room"), class_data["room"]),
            (self._ui("class_slot.row.class_index", "Class number in the day"), str(slot)),
        ]
        for row, (label, value) in enumerate(rows):
            ttk.Label(class_tab, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=5)
            ttk.Label(class_tab, text=value or "-", style="mainText.Label").grid(row=row, column=1, sticky="w", padx=8, pady=5)
        class_tab.grid_columnconfigure(1, weight=1)

        class_buttons = ttk.Frame(class_tab)
        class_buttons.grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=8, pady=(12, 0))
        ttk.Button(class_buttons, text=self._ui("class_slot.button.change", "Change class"), command=lambda: (dialog.destroy(), self._open_assignment_prompt(day_index, slot))).pack(side="left")
        ttk.Button(class_buttons, text=self._ui("class_slot.button.add_group", "Add group"), command=lambda: (dialog.destroy(), self._open_assignment_prompt(day_index, slot, add_group=True))).pack(side="left", padx=(6, 0))
        ttk.Button(class_buttons, text=self._ui("class_slot.button.delete_slot", "Delete slot"), command=lambda: self._delete_weekly_slot(day_index, slot, dialog)).pack(side="left", padx=(6, 0))

        homework_label = self._ui("events.type.homework", "Homework")
        exam_label = self._ui("events.type.exam", "Exam")
        event_type_var = StringVar(value=homework_label)
        event_topic = Text(events_tab, height=4, width=36)
        self._style_text(event_topic)
        homework_list = Listbox(events_tab, exportselection=False, height=4)
        exam_list = Listbox(events_tab, exportselection=False, height=4)
        self._style_listbox(homework_list)
        self._style_listbox(exam_list)

        def refresh_events():
            homework_list.delete(0, END)
            exam_list.delete(0, END)
            for item in self._event_items("homework", date_key, slot):
                homework_list.insert(END, item.get("topic", ""))
            for item in self._event_items("exams", date_key, slot):
                exam_list.insert(END, item.get("topic", ""))

        ttk.Label(events_tab, text=homework_label).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        homework_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        ttk.Label(events_tab, text=exam_label).grid(row=2, column=0, sticky="w", padx=8, pady=(8, 2))
        exam_list.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))

        event_form = ttk.Frame(events_tab)
        event_form.grid(row=4, column=0, sticky="ew", padx=8, pady=8)
        ttk.Combobox(event_form, textvariable=event_type_var, values=[homework_label, exam_label], state="readonly", width=14).grid(row=0, column=0, sticky="w", pady=(0, 4))
        event_topic.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 8))
        events_tab.grid_columnconfigure(0, weight=1)
        events_tab.grid_rowconfigure(1, weight=1)
        events_tab.grid_rowconfigure(3, weight=1)

        def add_event():
            topic = event_topic.get("1.0", END).strip()
            if not topic:
                return messagebox.showerror(
                    self._ui("events.invalid.title", "Invalid event"),
                    self._ui("events.invalid.message", "Event text is required."),
                    parent=dialog,
                )
            key = "homework" if event_type_var.get() == homework_label else "exams"
            state.settings.events._data[key].setdefault(date_key, []).append({"class": slot, "topic": topic})
            state.settings.events.save()
            event_topic.delete("1.0", END)
            refresh_events()
            self._refresh_clock_runtime()

        def remove_event():
            if homework_list.curselection():
                key = "homework"
                listbox = homework_list
            elif exam_list.curselection():
                key = "exams"
                listbox = exam_list
            else:
                return
            if not listbox.curselection():
                return
            selected_index = listbox.curselection()[0]
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

        event_buttons = ttk.Frame(events_tab)
        event_buttons.grid(row=6, column=0, sticky="w", padx=8, pady=(0, 8))
        ttk.Button(event_buttons, text=self._ui("events.button.add", "Add"), command=add_event).pack(side="left")
        ttk.Button(event_buttons, text=self._ui("events.button.remove", "Remove"), command=remove_event).pack(side="left", padx=(6, 0))
        refresh_events()

        ttk.Label(
            alerts_tab,
            text=self._ui("alerts.info", "Alert time is calculated relative to the beginning or end of this class."),
            style="mainText.Label",
            wraplength=400,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 6))
        alert_list = Listbox(alerts_tab, exportselection=False, height=8)
        self._style_listbox(alert_list)
        alert_list.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(8, 6), pady=(0, 8))
        alerts_tab.grid_columnconfigure(0, weight=1)
        alerts_tab.grid_rowconfigure(1, weight=1)
        current_alert_indexes: list[int] = []

        def refresh_alerts():
            current_alert_indexes.clear()
            alert_list.delete(0, END)
            for alert_index, alert in self._class_alert_items(date_key, slot):
                current_alert_indexes.append(alert_index)
                alert_list.insert(END, self._format_class_alert(alert))

        def remove_alert():
            if not alert_list.curselection():
                return
            alert_index = current_alert_indexes[alert_list.curselection()[0]]
            state.settings.events._data["alerts"].pop(alert_index)
            state.settings.events.save()
            refresh_alerts()
            self._refresh_clock_runtime()

        def open_alert_prompt(alert_index: int | None = None):
            existing_alert = state.settings.events._data["alerts"][alert_index] if alert_index is not None else {}
            alert_dialog = Toplevel(dialog)
            self._style_dialog(alert_dialog)
            alert_dialog.title(
                self._ui("alerts.dialog.edit_title", "Edit alert")
                if alert_index is not None
                else self._ui("alerts.dialog.add_title", "Add alert")
            )
            alert_dialog.transient(dialog)
            alert_dialog.grab_set()

            def close_alert_dialog():
                alert_dialog.destroy()
                dialog.lift()
                dialog.focus_force()

            alert_dialog.protocol("WM_DELETE_WINDOW", close_alert_dialog)

            relative_var = StringVar(value=existing_alert.get("relativeTo", "end"))
            message_box = Text(alert_dialog, height=4, width=36)
            self._style_text(message_box)
            message_box.insert("1.0", existing_alert.get("message", ""))
            keep_var = BooleanVar(value=bool(existing_alert.get("keep", False)))
            minutes_var = StringVar(value=str(existing_alert.get("minutes", 5)))

            relative_group = ttk.LabelFrame(alert_dialog, text=self._ui("alerts.calculate_from", "Calculate from"))
            relative_group.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 6))
            ttk.Radiobutton(relative_group, text=self._ui("alerts.from_end", "End of class"), variable=relative_var, value="end").pack(anchor="w", padx=8, pady=3)
            ttk.Radiobutton(relative_group, text=self._ui("alerts.from_start", "Beginning of class"), variable=relative_var, value="start").pack(anchor="w", padx=8, pady=3)

            ttk.Label(alert_dialog, text=self._ui("alerts.message", "Message")).grid(row=1, column=0, sticky="nw", padx=10, pady=6)
            message_box.grid(row=1, column=1, sticky="ew", padx=10, pady=6)

            keep_check = Checkbutton(alert_dialog, text=self._ui("alerts.keep_after", "Keep alert after firing"), variable=keep_var)
            self._style_checkbutton(keep_check)
            keep_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=6)

            ttk.Label(alert_dialog, text=self._ui("alerts.minutes", "Minutes since start/before end")).grid(row=3, column=0, sticky="w", padx=10, pady=6)
            ttk.Spinbox(alert_dialog, from_=0, to=240, textvariable=minutes_var, width=8).grid(row=3, column=1, sticky="w", padx=10, pady=6)
            alert_dialog.grid_columnconfigure(1, weight=1)

            def save_alert():
                try:
                    minutes = int(minutes_var.get().strip())
                    if minutes < 0:
                        raise ValueError("Minutes must be zero or greater.")
                    base_time = entry.end if relative_var.get() == "end" else entry.start
                    class_dt = datetime.combine(class_date, base_time) + timedelta(seconds=state.settings.schedule.delay)
                    alert_dt = class_dt - timedelta(minutes=minutes) if relative_var.get() == "end" else class_dt + timedelta(minutes=minutes)
                    message = message_box.get("1.0", END).strip()
                    payload = {
                        "date": alert_dt.strftime("%Y-%m-%d"),
                        "classDate": date_key,
                        "class": slot,
                        "time": alert_dt.strftime("%H:%M"),
                        "message": message or state.settings.localization.alert.defaultText,
                        "keep": keep_var.get(),
                        "relativeTo": relative_var.get(),
                        "minutes": minutes,
                    }
                    if alert_index is None:
                        state.settings.events._data["alerts"].append(payload)
                    else:
                        state.settings.events._data["alerts"][alert_index] = payload
                    state.settings.events.save()
                    refresh_alerts()
                    self._refresh_clock_runtime()
                    close_alert_dialog()
                except Exception as exc:
                    messagebox.showerror(self._ui("alerts.invalid.title", "Invalid alert"), str(exc), parent=alert_dialog)

            button_row = ttk.Frame(alert_dialog)
            button_row.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 10))
            ttk.Button(button_row, text=self._ui("assignment.save", "Save"), command=save_alert).pack(side="left")
            ttk.Button(button_row, text=self._ui("assignment.cancel", "Cancel"), command=close_alert_dialog).pack(side="left", padx=(6, 0))
            alert_dialog.update_idletasks()
            alert_dialog.geometry(f"{alert_dialog.winfo_reqwidth()}x{alert_dialog.winfo_reqheight()}")

        def edit_selected_alert(_event=None):
            if not alert_list.curselection():
                return
            open_alert_prompt(current_alert_indexes[alert_list.curselection()[0]])

        alert_list.bind("<Double-Button-1>", edit_selected_alert)

        alert_buttons = ttk.Frame(alerts_tab)
        alert_buttons.grid(row=2, column=1, sticky="sew", padx=(0, 8), pady=(0, 8))
        ttk.Button(alert_buttons, text=self._ui("alerts.button.remove_selected", "Remove selected alert"), command=remove_alert).pack(fill="x", pady=(0, 6))
        ttk.Button(alert_buttons, text=self._ui("alerts.button.add_new", "Add new alert"), command=open_alert_prompt).pack(fill="x")
        refresh_alerts()

    def _delete_weekly_slot(self, day_index: int, slot: int, dialog: Toplevel | None = None):
        if day_index < len(state.settings.schedule._data["default"]):
            state.settings.schedule._data["default"][day_index].pop(str(slot), None)
        state.settings.schedule._data["secondary"].get(str(day_index), {}).pop(str(slot), None)
        state.settings.schedule.save()
        if dialog is not None:
            self._close_child_window(dialog)
        else:
            self.after(0, self._focus_window)
        self._refresh_clock_runtime()
        self._openSchedule()

    def _openSpecialDays(self):
        self._clearContent()
        root = ttk.Frame(self.content)
        root.pack(fill="both", expand=True)

        left = ttk.Frame(root)
        left.pack(side="left", fill="y", padx=(0, 12))
        right = ttk.Frame(root)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text=self._ui("special_days.title", "Special days"), style="mainText.Label").pack(anchor="w")
        day_list = Listbox(left, exportselection=False, width=18, height=18)
        self._style_listbox(day_list)
        day_list.pack(fill="y", expand=True, pady=(8, 8))
        for key in sorted(state.settings.events._data["specialDays"]):
            day_list.insert(END, key)

        selected_date = StringVar(value=state.getTime().strftime("%Y-%m-%d"))
        full_var = BooleanVar(value=False)
        row_container = ttk.Frame(right)
        row_container.pack(fill="both", expand=True, pady=(8, 0))
        rows: list[dict[str, object]] = []

        def add_row(slot="", start="", end="", value=""):
            row_frame = ttk.Frame(row_container)
            row_frame.pack(fill="x", pady=2)
            slot_var = StringVar(value=str(slot))
            value_var = StringVar(value=value)
            ttk.Entry(row_frame, textvariable=slot_var, width=8).pack(side="left", padx=(0, 4))
            start_frame, start_hour_var, start_minute_var = self._create_time_inputs(row_frame, start=start)
            start_frame.pack(side="left", padx=(0, 4))
            end_frame, end_hour_var, end_minute_var = self._create_time_inputs(row_frame, start=end)
            end_frame.pack(side="left", padx=(0, 4))
            ttk.Entry(row_frame, textvariable=value_var).pack(side="left", fill="x", expand=True, padx=(0, 4))
            ttk.Button(row_frame, text=self._ui("special_days.button.remove_row", "X"), width=3, command=lambda: remove_row(row_frame)).pack(side="left")
            rows.append(
                {
                    "frame": row_frame,
                    "slot": slot_var,
                    "start_hour": start_hour_var,
                    "start_minute": start_minute_var,
                    "end_hour": end_hour_var,
                    "end_minute": end_minute_var,
                    "value": value_var,
                }
            )

        def remove_row(row_frame: ttk.Frame):
            for index, row in enumerate(list(rows)):
                if row["frame"] is row_frame:
                    rows.pop(index)
                    break
            row_frame.destroy()

        def load_special_day(_event=None):
            for row in list(rows):
                row["frame"].destroy()
            rows.clear()
            if not day_list.curselection():
                return
            key = day_list.get(day_list.curselection()[0])
            selected_date.set(key)
            parsed_date = datetime.strptime(key, "%Y-%m-%d").date()
            date_year_var.set(str(parsed_date.year))
            date_month_var.set(f"{parsed_date.month:02}")
            date_day_var.set(f"{parsed_date.day:02}")
            data = state.settings.events._data["specialDays"].get(key, {})
            full_var.set(bool(data.get("full", False)))
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

        day_list.bind("<<ListboxSelect>>", load_special_day)

        ttk.Label(right, text=self._ui("special_days.date", "Date")).pack(anchor="w")
        date_frame, date_year_var, date_month_var, date_day_var = self._create_date_inputs(right, value=selected_date.get())
        date_frame.pack(anchor="w", pady=(0, 8))
        full_check = Checkbutton(right, text=self._ui("special_days.replace_day", "Replace entire day"), variable=full_var)
        self._style_checkbutton(full_check)
        full_check.pack(anchor="w", pady=(0, 8))
        ttk.Label(right, text=self._ui("special_days.rows_help", "Rows: slot | start | end | classes")).pack(anchor="w")

        button_bar = ttk.Frame(right)
        button_bar.pack(fill="x", pady=(8, 8))
        ttk.Button(button_bar, text=self._ui("special_days.button.add_row", "Add row"), command=add_row).pack(side="left")

        def new_special_day():
            try:
                key = self._date_from_vars(date_year_var, date_month_var, date_day_var)
            except ValueError:
                return messagebox.showerror(
                    self._ui("special_days.invalid_date.title", "Invalid date"),
                    self._ui("special_days.invalid_date.message", "Use a valid date."),
                    parent=self,
                )
            selected_date.set(key)
            if key not in day_list.get(0, END):
                day_list.insert(END, key)
            day_list.selection_clear(0, END)
            day_list.selection_set(day_list.size() - 1)
            state.settings.events._data["specialDays"].setdefault(key, {"full": False})
            self._refresh_clock_runtime()
            load_special_day()

        ttk.Button(button_bar, text=self._ui("special_days.button.new_date", "New date"), command=new_special_day).pack(side="left", padx=(6, 0))

        def save_special_day():
            try:
                key = self._date_from_vars(date_year_var, date_month_var, date_day_var)
            except ValueError:
                return messagebox.showerror(
                    self._ui("special_days.invalid_date.title", "Invalid date"),
                    self._ui("special_days.invalid_date.message", "Use a valid date."),
                    parent=self,
                )
            selected_date.set(key)

            payload: dict[str, object] = {"full": full_var.get()}
            classes: dict[str, object] = {}
            time_slots: dict[str, str] = {}
            try:
                for row in rows:
                    slot = row["slot"].get().strip()
                    if not slot:
                        continue
                    int(slot)
                    start = self._time_from_vars(row["start_hour"], row["start_minute"])
                    end = self._time_from_vars(row["end_hour"], row["end_minute"])
                    value = row["value"].get().strip()
                    time_slots[slot] = f"{start}-{end}"
                    if value:
                        classes[slot] = self._parse_class_entry(value)
            except Exception as exc:
                return messagebox.showerror(self._ui("special_days.invalid_day.title", "Invalid special day"), str(exc), parent=self)

            if classes:
                payload["classes"] = classes
            if time_slots:
                payload["timeSlots"] = time_slots
            state.settings.events._data["specialDays"][key] = payload
            state.settings.events.save()
            self._refresh_clock_runtime()
            self._openSpecialDays()

        def delete_special_day():
            if not day_list.curselection():
                return
            key = day_list.get(day_list.curselection()[0])
            state.settings.events._data["specialDays"].pop(key, None)
            state.settings.events.save()
            self._refresh_clock_runtime()
            self._openSpecialDays()

        footer = ttk.Frame(right)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text=self._ui("special_days.button.save", "Save special day"), command=save_special_day).pack(side="left")
        ttk.Button(footer, text=self._ui("special_days.button.delete", "Delete"), command=delete_special_day).pack(side="left", padx=(6, 0))

        add_row()

    def _openGeneral(self):
        self._clearContent()
        root = ttk.Frame(self.content)
        root.pack(fill="both", expand=True)

        cfg = state.settings.config
        background_var = StringVar(value=f"#{cfg.background:06X}")
        foreground_var = StringVar(value=f"#{cfg.foreground:06X}")
        lang_options = self._available_languages()
        lang_var = StringVar(value=cfg.lang if cfg.lang in lang_options else (lang_options[0] if lang_options else cfg.lang))
        ignore_updates_var = BooleanVar(value=cfg.ignoreUpdates)
        show_teacher_var = BooleanVar(value=cfg.showTeacher)
        alpha_default_var = StringVar(value=str(cfg.alpha.get("default", 0.75)))
        alpha_hover_var = StringVar(value=str(cfg.alpha.get("onHover", 0.25)))

        fields = ttk.Frame(root)
        fields.pack(fill="x")
        items = [
            (self._ui("general.label.background", "Background"), background_var),
            (self._ui("general.label.foreground", "Foreground"), foreground_var),
            (self._ui("general.label.language", "Language"), lang_var),
            (self._ui("general.label.alpha_default", "Alpha default"), alpha_default_var),
            (self._ui("general.label.alpha_hover", "Alpha on hover"), alpha_hover_var),
        ]
        for row, (label, var) in enumerate(items):
            ttk.Label(fields, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
            if label == self._ui("general.label.language", "Language"):
                ttk.Combobox(fields, textvariable=var, values=lang_options, state="readonly").grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            else:
                ttk.Entry(fields, textvariable=var).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        fields.grid_columnconfigure(1, weight=1)
        ignore_updates_check = Checkbutton(fields, text=self._ui("general.ignore_updates", "Ignore updates"), variable=ignore_updates_var)
        self._style_checkbutton(ignore_updates_check)
        ignore_updates_check.grid(row=5, column=0, columnspan=2, sticky="w", padx=4, pady=4)
        show_teacher_check = Checkbutton(fields, text=self._ui("general.show_teacher", "Show teacher"), variable=show_teacher_var)
        self._style_checkbutton(show_teacher_check)
        show_teacher_check.grid(row=6, column=0, columnspan=2, sticky="w", padx=4, pady=4)

        def choose_color(target: StringVar):
            color = colorchooser.askcolor(target.get(), parent=self)[1]
            if color:
                target.set(color.upper())

        color_buttons = ttk.Frame(root)
        color_buttons.pack(fill="x", pady=(8, 8))
        ttk.Button(color_buttons, text=self._ui("general.pick_background", "Pick background"), command=lambda: choose_color(background_var)).pack(side="left")
        ttk.Button(color_buttons, text=self._ui("general.pick_foreground", "Pick foreground"), command=lambda: choose_color(foreground_var)).pack(side="left", padx=(6, 0))

        def save_general():
            try:
                bg = background_var.get().strip()
                fg = foreground_var.get().strip()
                if not (bg.startswith("#") and len(bg) == 7):
                    raise ValueError(self._ui("general.invalid.background", "Background must be #RRGGBB"))
                if not (fg.startswith("#") and len(fg) == 7):
                    raise ValueError(self._ui("general.invalid.foreground", "Foreground must be #RRGGBB"))
                int(bg.removeprefix("#"), 16)
                int(fg.removeprefix("#"), 16)
                cfg._data["background"] = bg.upper()
                cfg._data["foreground"] = fg.upper()
                cfg._data["lang"] = lang_var.get().strip() or cfg._data["lang"]
                cfg._data["ignoreUpdates"] = ignore_updates_var.get()
                cfg._data["showTeacher"] = show_teacher_var.get()
                cfg.setAlpha("default", float(alpha_default_var.get().strip()))
                cfg.setAlpha("onHover", float(alpha_hover_var.get().strip()))
                cfg.save()
                try:
                    state.clock.wm_attributes("-alpha", cfg.alpha["default"])
                except Exception:
                    self.logger.exception("Could not refresh clock colors from settings UI")
                self._openGeneral()
            except Exception as exc:
                messagebox.showerror(self._ui("general.invalid.title", "Invalid settings"), str(exc), parent=self)
            self._refresh_clock_runtime()

        ttk.Button(root, text=self._ui("general.save", "Save general settings"), command=save_general).pack(anchor="w")
