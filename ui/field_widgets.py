from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from ui.formatters import stringify_value


class BaseFieldWidget(QtWidgets.QWidget):
    """Base widget with a value accessor."""

    def __init__(self, field_def, parent=None):
        super().__init__(parent)
        self.field_def = field_def

    def value(self):
        raise NotImplementedError


class TextFieldWidget(BaseFieldWidget):
    def __init__(self, field_def, parent=None):
        super().__init__(field_def, parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.line_edit = QtWidgets.QLineEdit(self)
        layout.addWidget(self.line_edit)

    def value(self):
        return self.line_edit.text()

    def set_value(self, value):
        self.line_edit.setText("" if value is None else str(value))


class PathFieldWidget(BaseFieldWidget):
    pathChanged = QtCore.Signal(str)

    def __init__(self, field_def, parent=None):
        super().__init__(field_def, parent)
        self.mode = field_def.get("mode", "directory")
        self.caption = field_def.get("caption", "Select path")
        self.filter = field_def.get("filter", "All Files (*)")
        self.default_suffix = field_def.get("default_suffix")
        self.dialog_mode = field_def.get("dialog", "save")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.line_edit = QtWidgets.QLineEdit(self)
        browse_btn = QtWidgets.QPushButton("📂 Browse…", self)
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(self.line_edit)
        layout.addWidget(browse_btn)
        self.line_edit.editingFinished.connect(self._emit_current_path)

    def _browse(self):
        current_value = self.value() or str(Path.home())
        if self.mode == "directory":
            dialog = QtWidgets.QFileDialog(self, self.caption, current_value)
            dialog.setFileMode(QtWidgets.QFileDialog.Directory)
            dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
            if dialog.exec():
                selected = dialog.selectedFiles()
                if selected:
                    self.line_edit.setText(selected[0])
        else:
            dialog_mode = (self.dialog_mode or "save").lower()
            suffix = (self.default_suffix or "").lower()
            use_save_dialog = dialog_mode != "open" or suffix == "json"
            dialog_func = QtWidgets.QFileDialog.getSaveFileName if use_save_dialog else QtWidgets.QFileDialog.getOpenFileName
            path, _ = dialog_func(
                self,
                self.caption,
                current_value,
                self.filter,
            )
            if path:
                normalized = self._normalize_and_materialize_path(path)
                self.line_edit.setText(normalized)
                self._emit_current_path()

    def value(self):
        return self.line_edit.text()

    def set_path(self, path, emit_change=False):
        self.line_edit.setText(path)
        if emit_change:
            self._emit_current_path()

    def _emit_current_path(self):
        current_value = self.value()
        normalized = self._normalize_and_materialize_path(current_value)
        if normalized != current_value:
            self.line_edit.setText(normalized)
        self.pathChanged.emit(self.value())

    def set_value(self, path):
        if path is None:
            path = ""
        self.set_path(str(path), emit_change=False)

    def _normalize_and_materialize_path(self, raw_path):
        if raw_path is None:
            return ""
        text = str(raw_path).strip()
        if not text:
            return ""
        suffix = (self.default_suffix or "").lstrip(".")
        if not suffix:
            return text
        if suffix.lower() != "json":
            if not Path(text).suffix:
                return f"{text}.{suffix}"
            return text
        try:
            candidate = Path(text).expanduser()
        except (OSError, RuntimeError, ValueError):
            return text
        if not candidate.suffix:
            candidate = candidate.with_suffix(f".{suffix}")
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.touch(exist_ok=True)
        except OSError:
            pass
        return str(candidate)


class ListFieldWidget(BaseFieldWidget):
    def __init__(self, field_def, parent=None):
        super().__init__(field_def, parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.combo = QtWidgets.QComboBox(self)
        for option in field_def.get("list", []):
            self.combo.addItem(option)
        layout.addWidget(self.combo)

    def value(self):
        return self.combo.currentText()

    def set_value(self, value):
        text = "" if value is None else str(value)
        index = self.combo.findText(text)
        if index < 0 and text:
            self.combo.addItem(text)
            index = self.combo.findText(text)
        if index >= 0:
            self.combo.setCurrentIndex(index)


class NumberFieldWidget(BaseFieldWidget):
    def __init__(self, field_def, parent=None):
        super().__init__(field_def, parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.line_edit = QtWidgets.QLineEdit(self)
        self.line_edit.setPlaceholderText("e.g., 10e9")
        validator = QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"^$|^-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"),
            self.line_edit,
        )
        self.line_edit.setValidator(validator)
        layout.addWidget(self.line_edit)

    def value(self):
        text = self.line_edit.text().strip()
        if not text:
            return ""
        try:
            number = float(text)
        except ValueError:
            return text
        if number.is_integer():
            return int(number)
        return number

    def set_value(self, value):
        if value in ("", None):
            self.line_edit.setText("")
            return
        self.line_edit.setText(str(value))


class KeyValueGroupWidget(BaseFieldWidget):
    def __init__(self, field_def, parent=None):
        super().__init__(field_def, parent)
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        group_box = QtWidgets.QGroupBox(field_def.get("Name", ""), self)
        form_layout = QtWidgets.QFormLayout(group_box)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(6)
        outer_layout.addWidget(group_box)

        self.widgets = {}
        for sub_field in field_def.get("fields", []):
            widget = create_field_widget(sub_field, parent=group_box)
            form_layout.addRow(sub_field["Name"], widget)
            self.widgets[sub_field["Name"]] = widget

    def value(self):
        return {name: widget.value() for name, widget in self.widgets.items()}

    def set_value(self, values):
        if not isinstance(values, dict):
            return
        for name, widget in self.widgets.items():
            raw_value = values.get(name)
            if raw_value is None:
                continue
            setter = getattr(widget, "set_value", None)
            if callable(setter):
                setter(raw_value)


class KeyValueListWidget(BaseFieldWidget):
    def __init__(self, field_def, parent=None):
        super().__init__(field_def, parent)
        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.widgets = {}
        for fld in field_def.get("fields", []):
            widget = self._create_field_widget(fld)
            if isinstance(widget, QtWidgets.QWidget):
                if isinstance(widget, KeyValueGroupWidget):
                    layout.addRow(widget)
                else:
                    layout.addRow(fld["Name"], widget)
            else:
                raise TypeError(f"Unsupported widget generated for: {fld.get('name')}")
            self.widgets[fld["Name"]] = widget

    def value(self):
        return {name: widget.value() for name, widget in self.widgets.items()}

    def _create_field_widget(self, field_def):
        if "type" in field_def:
            return create_field_widget(field_def, parent=self)
        if "fields" in field_def:
            return KeyValueGroupWidget(field_def, parent=self)
        raise ValueError(f"Unrecognized key-value list field definition: {field_def}")

    def set_value(self, values):
        if not isinstance(values, dict):
            return
        for name, widget in self.widgets.items():
            raw_value = values.get(name)
            if raw_value is None:
                continue
            setter = getattr(widget, "set_value", None)
            if callable(setter):
                setter(raw_value)


class TableRowWidget(QtWidgets.QWidget):
    removed = QtCore.Signal(object)

    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.widgets = {}

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for column in columns:
            col_container = QtWidgets.QWidget(self)
            col_layout = QtWidgets.QVBoxLayout(col_container)
            col_layout.setContentsMargins(0, 0, 0, 0)
            col_layout.setSpacing(2)

            label = QtWidgets.QLabel(column["Name"], col_container)
            label.setStyleSheet("font-weight: 600;")
            widget = create_field_widget(column, parent=col_container)

            col_layout.addWidget(label)
            col_layout.addWidget(widget)
            layout.addWidget(col_container)

            self.widgets[column["Name"]] = widget

        remove_btn = QtWidgets.QPushButton("Remove", self)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(remove_btn)

    def value(self):
        return {name: widget.value() for name, widget in self.widgets.items()}

    def set_row_data(self, data):
        if not isinstance(data, dict):
            return
        for name, widget in self.widgets.items():
            raw_value = data.get(name)
            setter = getattr(widget, "set_value", None)
            if callable(setter):
                setter(raw_value)


class TableFieldWidget(BaseFieldWidget):
    def __init__(self, field_def, parent=None):
        super().__init__(field_def, parent)
        self.columns = field_def.get("columns", [])
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(8)

        self.rows_container = QtWidgets.QWidget(self)
        self.rows_layout = QtWidgets.QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)
        outer_layout.addWidget(self.rows_container)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        add_btn = QtWidgets.QPushButton("Add Row", self)
        add_btn.clicked.connect(self.add_row)
        buttons_layout.addWidget(add_btn)
        outer_layout.addLayout(buttons_layout)

        self.row_widgets = []

    def add_row(self):
        row = TableRowWidget(self.columns, parent=self.rows_container)
        row.removed.connect(self._remove_row)
        self.rows_layout.addWidget(row)
        self.row_widgets.append(row)
        return row

    def _remove_row(self, row_widget):
        self.row_widgets.remove(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()

    def value(self):
        return [row.value() for row in self.row_widgets]

    def clear_rows(self):
        for row in list(self.row_widgets):
            self._remove_row(row)

    def set_value(self, rows):
        if not isinstance(rows, list):
            rows = []
        self.clear_rows()
        for row_data in rows:
            row = self.add_row()
            row.set_row_data(row_data or {})


class ModelDialog(QtWidgets.QDialog):
    def __init__(self, model_column, parameters_column, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧩 Configure Model")
        self.setModal(True)

        self.model_column = model_column or {}
        self.parameters_column = parameters_column or {}

        self.parameter_definitions = {
            group.get("Name"): group.get("fields", [])
            for group in self.parameters_column.get("fields", [])
        }
        self.parameter_widgets = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QtWidgets.QLabel("Select a model and specify its parameters.", self)
        header.setWordWrap(True)
        layout.addWidget(header)

        model_layout = QtWidgets.QHBoxLayout()
        model_label = QtWidgets.QLabel("Model:", self)
        self.model_combo = QtWidgets.QComboBox(self)
        for option in self.model_column.get("list", []):
            self.model_combo.addItem(option)
        self.model_combo.currentTextChanged.connect(self._rebuild_parameters)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo, 1)
        layout.addLayout(model_layout)

        self.parameters_container = QtWidgets.QWidget(self)
        self.parameters_layout = QtWidgets.QFormLayout(self.parameters_container)
        self.parameters_layout.setContentsMargins(0, 0, 0, 0)
        self.parameters_layout.setSpacing(8)
        parameters_group = QtWidgets.QGroupBox("⚙️ Parameters", self)
        parameters_group.setLayout(self.parameters_layout)
        layout.addWidget(parameters_group)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self.model_combo.count():
            self._rebuild_parameters(self.model_combo.currentText())

    def _rebuild_parameters(self, model_name):
        while self.parameters_layout.count():
            item = self.parameters_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.parameter_widgets = {}

        fields = self.parameter_definitions.get(model_name, [])
        for field in fields:
            widget = create_field_widget(field, parent=self)
            self.parameters_layout.addRow(field["Name"], widget)
            self.parameter_widgets[field["Name"]] = widget

    def model_entry(self):
        model_name = self.model_combo.currentText()
        if not model_name:
            return None
        parameters_list = []
        for field_name, widget in self.parameter_widgets.items():
            value = widget.value()
            if value not in ("", None):
                parameters_list.append({field_name: stringify_value(value)})
        return {
            "Model": {
                "Name": model_name,
                "Parameters": parameters_list,
            }
        }


class ModelDisplayWidget(QtWidgets.QFrame):
    removed = QtCore.Signal(object)

    def __init__(self, model_entry, parent=None):
        super().__init__(parent)
        self.model_entry = model_entry
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet("QFrame { border: 1px solid #cccccc; border-radius: 6px; }")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        name = model_entry["Model"]["Name"]
        parameters = model_entry["Model"].get("Parameters", [])
        params_summary = ", ".join(
            f"{list(p.keys())[0]}={list(p.values())[0]}" for p in parameters
        ) or "No parameters specified"

        label = QtWidgets.QLabel(f"🧠 {name}\n🔢 {params_summary}", self)
        label.setWordWrap(True)
        layout.addWidget(label, 1)

        remove_btn = QtWidgets.QPushButton("✖ Remove", self)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(remove_btn)


class MaterialRowWidget(QtWidgets.QFrame):
    removed = QtCore.Signal(object)

    def __init__(self, model_column, parameters_column, parent=None):
        super().__init__(parent)
        self.model_column = model_column
        self.parameters_column = parameters_column
        self.model_entries = []
        self.model_widgets = []

        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet("QFrame { border: 2px solid #e0e0e0; border-radius: 8px; }")

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 10, 12, 12)
        outer_layout.setSpacing(8)

        header_layout = QtWidgets.QHBoxLayout()
        name_label = QtWidgets.QLabel("🧪 Material Name:", self)
        self.name_edit = QtWidgets.QLineEdit(self)
        self.name_edit.setPlaceholderText("Enter material name")
        self.name_edit.setMinimumWidth(260)
        header_layout.addWidget(name_label)
        header_layout.addWidget(self.name_edit, 1)

        remove_btn = QtWidgets.QPushButton("🗑️ Remove Material", self)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        header_layout.addWidget(remove_btn)
        outer_layout.addLayout(header_layout)

        models_header_layout = QtWidgets.QHBoxLayout()
        models_label = QtWidgets.QLabel("🔧 Models:", self)
        self.add_model_btn = QtWidgets.QPushButton("➕ Add Model", self)
        self.add_model_btn.clicked.connect(self._add_model)
        models_header_layout.addWidget(models_label)
        models_header_layout.addStretch()
        models_header_layout.addWidget(self.add_model_btn)
        outer_layout.addLayout(models_header_layout)

        self.models_container = QtWidgets.QWidget(self)
        self.models_layout = QtWidgets.QVBoxLayout(self.models_container)
        self.models_layout.setContentsMargins(0, 0, 0, 0)
        self.models_layout.setSpacing(6)
        outer_layout.addWidget(self.models_container)

    def _add_model(self):
        dialog = ModelDialog(self.model_column, self.parameters_column, parent=self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            entry = dialog.model_entry()
            if entry:
                self.model_entries.append(entry)
                widget = ModelDisplayWidget(entry, parent=self.models_container)
                widget.removed.connect(self._remove_model)
                self.models_layout.addWidget(widget)
                self.model_widgets.append(widget)

    def _remove_model(self, widget):
        try:
            self.model_entries.remove(widget.model_entry)
        except ValueError:
            pass
        if widget in self.model_widgets:
            self.model_widgets.remove(widget)
        widget.setParent(None)
        widget.deleteLater()

    def value(self):
        material_name = self.name_edit.text()
        material_data = {}
        if material_name:
            material_data["Name"] = stringify_value(material_name)

        entries = [entry for entry in self.model_entries if entry.get("Model")]
        if not entries:
            return material_data

        if len(entries) == 1:
            material_data["Model"] = entries[0]["Model"]
        else:
            material_data["Models"] = entries
        return material_data

    def set_material_name(self, name):
        self.name_edit.setText(stringify_value(name))

    def _clear_model_entries(self):
        for widget in list(self.model_widgets):
            if widget in self.model_widgets:
                self.model_widgets.remove(widget)
            widget.setParent(None)
            widget.deleteLater()
        self.model_entries = []

    def _append_model_entry(self, model_info):
        if not isinstance(model_info, dict):
            return
        name = stringify_value(model_info.get("Name", ""))
        parameters = model_info.get("Parameters", [])
        normalized_parameters = []
        if isinstance(parameters, dict):
            source_items = parameters.items()
        else:
            source_items = []
            for item in parameters or []:
                if isinstance(item, dict) and item:
                    source_items.extend(item.items())

        for key, value in source_items:
            normalized_parameters.append({str(key): stringify_value(value)})

        entry = {
            "Model": {
                "Name": name,
                "Parameters": normalized_parameters,
            }
        }
        self.model_entries.append(entry)
        widget = ModelDisplayWidget(entry, parent=self.models_container)
        widget.removed.connect(self._remove_model)
        self.models_layout.addWidget(widget)
        self.model_widgets.append(widget)

    def set_data(self, material_data):
        if not isinstance(material_data, dict):
            return
        self.name_edit.setText(stringify_value(material_data.get("Name", "")))
        self._clear_model_entries()

        def extract_model_payload(raw_entry):
            if not isinstance(raw_entry, dict):
                return None
            if isinstance(raw_entry.get("Model"), dict):
                return raw_entry.get("Model")
            return raw_entry

        models_field = material_data.get("Models")
        if isinstance(models_field, list):
            for raw_model in models_field:
                payload = extract_model_payload(raw_model)
                if payload:
                    self._append_model_entry(payload)
        single_model = material_data.get("Model")
        payload = extract_model_payload(single_model)
        if payload:
            self._append_model_entry(payload)


class MaterialsTableWidget(BaseFieldWidget):
    def __init__(self, field_def, parent=None):
        super().__init__(field_def, parent)
        self.columns = field_def.get("columns", [])
        self.model_column = next((col for col in self.columns if col.get("Name") == "Model"), {})
        self.parameters_column = next(
            (col for col in self.columns if col.get("Name") == "Parameters"), {}
        )

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(8)

        title = QtWidgets.QLabel("🧬 Materials", self)
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        outer_layout.addWidget(title)

        self.rows_container = QtWidgets.QWidget(self)
        self.rows_layout = QtWidgets.QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(10)
        outer_layout.addWidget(self.rows_container)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        add_btn = QtWidgets.QPushButton("➕ Add Material", self)
        add_btn.clicked.connect(self.add_row)
        buttons_layout.addWidget(add_btn)
        outer_layout.addLayout(buttons_layout)

        self.row_widgets = []

    def add_row(self, material_name=None):
        row = MaterialRowWidget(self.model_column, self.parameters_column, parent=self.rows_container)
        row.removed.connect(self._remove_row)
        self.rows_layout.addWidget(row)
        self.row_widgets.append(row)
        if material_name:
            row.set_material_name(material_name)
        return row

    def _remove_row(self, row_widget):
        if row_widget in self.row_widgets:
            self.row_widgets.remove(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()

    def clear_rows(self):
        for row in list(self.row_widgets):
            self._remove_row(row)

    def populate_from_names(self, material_names):
        self.clear_rows()
        for material_name in material_names or []:
            self.add_row(material_name=material_name)

    def value(self):
        values = []
        for row in self.row_widgets:
            data = row.value()
            if data:
                values.append(data)
        return values

    def set_value(self, materials):
        self.clear_rows()
        for entry in materials or []:
            if not isinstance(entry, dict):
                continue
            row = self.add_row()
            row.set_data(entry)


def create_field_widget(field_def, parent=None):
    ftype = field_def.get("type", "").lower()
    if ftype == "text edit":
        return TextFieldWidget(field_def, parent=parent)
    if ftype == "path finder":
        return PathFieldWidget(field_def, parent=parent)
    if ftype == "list":
        return ListFieldWidget(field_def, parent=parent)
    if ftype == "number":
        return NumberFieldWidget(field_def, parent=parent)
    if ftype == "key-value list":
        return KeyValueListWidget(field_def, parent=parent)
    if ftype == "table":
        if field_def.get("Name") == "Materials":
            return MaterialsTableWidget(field_def, parent=parent)
        return TableFieldWidget(field_def, parent=parent)
    raise ValueError(f"Unsupported field type: {field_def.get('type')}")
