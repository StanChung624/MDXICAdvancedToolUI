import copy
import json
import re
from pathlib import Path, PureWindowsPath

from run_reader import run_reader

from PySide6 import QtCore, QtGui, QtWidgets


SECTION_EMOJIS = {
    "source": "📁",
    "target": "🎯",
    "configuration": "⚙️",
    "materials": "🧬",
    "model": "🧠",
}

STRUCTURE_DEFINITION = {
    "solver": [
        "MappingTool",
        "ReliabilityTools",
    ],
    "parameters": [
        {
            "MappingTool": [
                {
                    "source": [
                        {
                            "Name": "MeshDirectory",
                            "type": "path finder",
                        },
                        {
                            "Name": "RunFolderPath",
                            "type": "path finder",
                        },
                    ],
                    "target": [
                        {
                            "Name": "MeshDirectory",
                            "type": "path finder",
                        },
                        {
                            "Name": "RunFolderPath",
                            "type": "path finder",
                        },
                        {
                            "Name": "ProjectName",
                            "type": "text edit",
                        },
                        {
                            "Name": "RunName",
                            "type": "text edit",
                        },
                        {
                            "Name": "TFMDirectory",
                            "type": "path finder",
                        },
                    ],
                    "configuration": [
                        {
                            "Name": "MappingMode",
                            "type": "list",
                            "list": [
                                "ByInstance",
                                "ByPartAndPartInsert",
                                "Flatten",
                            ],
                        }
                    ],
                }
            ]
        },
        {
            "ReliabilityTools": [
                {
                    "source": [
                        {
                            "Name": "RunFile",
                            "type": "path finder",
                            "mode": "file",
                            "dialog": "open",
                            "caption": "Select a .run file",
                            "filter": "Run Files (*.run);;All Files (*)",
                            "default_suffix": "run",
                        },
                        {
                            "Name": "Materials",
                            "type": "table",
                            "columns": [
                                {
                                    "Name": "Name",
                                    "type": "text edit",
                                },
                                {
                                    "Name": "Model",
                                    "type": "list",
                                    "list": [
                                        "FatigueModel: Modified Coffin Manson",
                                        "FailureModel: Hill-Tsai Criterion",
                                        "FailureModel: Von Mises Criterion",
                                    ],
                                },
                                {
                                    "Name": "Parameters",
                                    "type": "key-value list",
                                    "fields": [
                                        {
                                            "Name": "FatigueModel: Modified Coffin Manson",
                                            "fields": [
                                                {
                                                    "Name": "YoungModulus",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "YieldStress",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "Alpha",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "m",
                                                    "type": "number",
                                                },
                                            ],
                                        },
                                        {
                                            "Name": "FailureModel: Hill-Tsai Criterion",
                                            "fields": [
                                                {
                                                    "Name": "Xc",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "Xt",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "Yc",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "Yt",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "Sxy",
                                                    "type": "number",
                                                },
                                            ],
                                        },
                                        {
                                            "Name": "FailureModel: Von Mises Criterion",
                                            "fields": [
                                                {
                                                    "Name": "Strength",
                                                    "type": "number",
                                                }
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                }
            ]
        },
    ],
}


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
            dialog_func = QtWidgets.QFileDialog.getSaveFileName
            if self.dialog_mode.lower() == "open":
                dialog_func = QtWidgets.QFileDialog.getOpenFileName
            path, _ = dialog_func(
                self,
                self.caption,
                current_value,
                self.filter,
            )
            if path:
                if self.dialog_mode.lower() != "open" and self.default_suffix and not Path(path).suffix:
                    path = f"{path}.{self.default_suffix.lstrip('.')}"
                self.line_edit.setText(path)
                self._emit_current_path()

    def value(self):
        return self.line_edit.text()

    def set_path(self, path, emit_change=False):
        self.line_edit.setText(path)
        if emit_change:
            self._emit_current_path()

    def _emit_current_path(self):
        self.pathChanged.emit(self.value())


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

    def _remove_model(self, widget):
        try:
            self.model_entries.remove(widget.model_entry)
        except ValueError:
            pass
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

    def _remove_row(self, row_widget):
        self.row_widgets.remove(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()

    def value(self):
        return [row.value() for row in self.row_widgets]


def stringify_value(value):
    if isinstance(value, dict):
        return {key: stringify_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [stringify_value(item) for item in value]
    if isinstance(value, QtCore.QDate):
        return value.toString(QtCore.Qt.ISODate)
    if isinstance(value, QtCore.QDateTime):
        return value.toString(QtCore.Qt.ISODate)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return value
    if isinstance(value, int):
        return value
    if value is None:
        return ""
    return str(value)


def format_solver_payload(solver_name, parameters):
    solver_name = solver_name or ""
    if solver_name == "MappingTool":
        return {"Maptools": format_mapping_tool(parameters)}
    if solver_name == "ReliabilityTools":
        return {"ReliabilityTools": format_reliability_tools(parameters)}
    # Fallback: just stringify collected parameters.
    formatted = {
        section.capitalize(): {field: stringify_value(val) for field, val in fields.items()}
        for section, fields in parameters.items()
    }
    return {solver_name or "Solver": formatted}


def format_mapping_tool(parameters):
    formatted = {}
    for section_name, fields in parameters.items():
        section_key = section_name.capitalize()
        formatted[section_key] = {field: stringify_value(val) for field, val in fields.items()}
    return formatted


def format_reliability_tools(parameters):
    formatted = {}
    for section_name, fields in parameters.items():
        section_key = section_name.capitalize()
        if section_name.lower() == "source":
            formatted[section_key] = format_reliability_source(fields)
        else:
            formatted[section_key] = {field: stringify_value(val) for field, val in fields.items()}
    return formatted


def _coerce_run_path(path_str):
    normalized = str(path_str).strip()
    if not normalized:
        return None, normalized
    if normalized.startswith("\\\\") or re.match(r"^[A-Za-z]:", normalized) or "\\" in normalized:
        return PureWindowsPath(normalized), normalized
    return Path(normalized).expanduser(), normalized


def _extract_project_folder(path_obj, run_folder):
    parts_lower = [part.lower() for part in path_obj.parts]
    for idx, part in enumerate(parts_lower):
        if part == "analysis" and idx > 0:
            project_cls = path_obj.__class__
            return str(project_cls(*path_obj.parts[:idx]))
    parent_candidate = run_folder.parent
    if parent_candidate == run_folder:
        return str(run_folder)
    return str(parent_candidate)


def derive_run_metadata(run_file_value):
    path_obj, normalized = _coerce_run_path(run_file_value)
    if path_obj is None or not normalized:
        raise ValueError("Run file path is required.")
    if not path_obj.is_absolute():
        raise ValueError("Run file path must be absolute.")
    run_folder = path_obj.parent
    if run_folder == path_obj:
        raise ValueError("Run file path must include a parent folder.")

    run_name_token = run_folder.name or ""
    run_name_match = re.search(r"(\d+)$", run_name_token)
    run_name = run_name_match.group(1) if run_name_match else run_name_token

    file_stem = path_obj.stem
    project_name = re.sub(r"\d+$", "", file_stem)
    project_name = re.sub(r"[_\-\s]+$", "", project_name)
    if not project_name:
        project_name = file_stem

    project_folder = _extract_project_folder(path_obj, run_folder)

    return {
        "RunFile": str(path_obj),
        "RunName": run_name,
        "ProjectName": project_name,
        "ProjectFolder": project_folder,
    }


def format_reliability_source(fields):
    formatted = {}
    run_file_raw = fields.get("RunFile", "")
    if isinstance(run_file_raw, str):
        run_file_value = run_file_raw.strip()
    else:
        run_file_value = str(run_file_raw).strip()

    run_metadata = derive_run_metadata(run_file_value)
    formatted.update(run_metadata)

    for field_name, value in fields.items():
        if field_name == "Materials":
            formatted[field_name] = format_materials(value)
        elif field_name == "RunFile":
            formatted.setdefault("RunFile", stringify_value(value))
        else:
            formatted[field_name] = stringify_value(value)
    return formatted


def format_materials(material_rows):
    materials_output = []
    for row in material_rows or []:
        if not isinstance(row, dict):
            continue
        if "Models" in row or "Model" in row:
            materials_output.append(stringify_value(row))
            continue
        entry = {}
        name = row.get("Name")
        if name:
            entry["Name"] = stringify_value(name)

        model_choice = row.get("Model")
        parameter_groups = row.get("Parameters", {})

        model_entries = []
        if isinstance(parameter_groups, dict):
            for group_name, parameters in parameter_groups.items():
                model_entries.append(build_model_entry(group_name, parameters))

        # If a model was explicitly selected, order it first.
        if model_choice:
            model_entries.sort(key=lambda item: 0 if item["Model"]["Name"] == model_choice else 1)

        # Remove empty parameter groups.
        model_entries = [entry for entry in model_entries if entry["Model"]["Parameters"]]

        if not model_entries and model_choice:
            model_entries.append(
                {
                    "Model": {
                        "Name": stringify_value(model_choice),
                        "Parameters": [],
                    }
                }
            )

        if not model_entries:
            materials_output.append(entry)
            continue

        if len(model_entries) == 1:
            entry["Model"] = model_entries[0]["Model"]
        else:
            entry["Models"] = model_entries

        materials_output.append(entry)

    return materials_output


def build_model_entry(model_name, parameters):
    params_list = []
    if isinstance(parameters, dict):
        for param_name, value in parameters.items():
            params_list.append({param_name: stringify_value(value)})
    return {
        "Model": {
            "Name": stringify_value(model_name),
            "Parameters": params_list,
        }
    }


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


def load_structure(structure):
    parameters_section = structure.get("parameters")
    if parameters_section is None:
        parameters_section = structure.get("Parameters", [])
    solver_defs = {}
    for entry in parameters_section:
        for solver_name, groups in entry.items():
            sections = {}
            for group in groups:
                for section_name, fields in group.items():
                    sections[section_name] = copy.deepcopy(fields)
            solver_defs[solver_name] = sections
    solvers = structure.get("solver")
    if solvers is None:
        solvers = structure.get("Solver", [])
    return list(solvers or []), solver_defs


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🛠️ IC Advanced Tool UI")

        self.root_dir = Path(__file__).parent
        self.solvers, self.solver_definitions = load_structure(STRUCTURE_DEFINITION)
        self.parameter_widgets = {}
        self.run_file_widget = None
        self.materials_widget = None
        self._last_run_reader_error = None

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        solver_layout = QtWidgets.QHBoxLayout()
        solver_label = QtWidgets.QLabel("🧠 Solver:", central)
        self.solver_combo = QtWidgets.QComboBox(central)
        self.solver_combo.addItems(self.solvers)
        self.solver_combo.currentTextChanged.connect(self._rebuild_form)
        solver_layout.addWidget(solver_label)
        solver_layout.addWidget(self.solver_combo, 1)
        main_layout.addLayout(solver_layout)

        output_layout = QtWidgets.QHBoxLayout()
        output_label = QtWidgets.QLabel("💾 Output File:", central)
        self.output_path_widget = PathFieldWidget(
            {
                "Name": "OutputFile",
                "type": "path finder",
                "mode": "file",
                "caption": "Choose output JSON file",
                "filter": "JSON Files (*.json);;All Files (*)",
                "default_suffix": "json",
            },
            parent=central,
        )
        default_output_path = self.root_dir / "test.json"
        self.output_path_widget.set_path(str(default_output_path))
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path_widget, 1)
        main_layout.addLayout(output_layout)

        self.scroll_area = QtWidgets.QScrollArea(central)
        self.scroll_area.setWidgetResizable(True)
        self.form_container = QtWidgets.QWidget()
        self.form_layout = QtWidgets.QVBoxLayout(self.form_container)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(10)
        self.scroll_area.setWidget(self.form_container)
        main_layout.addWidget(self.scroll_area, 1)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        save_btn = QtWidgets.QPushButton("💾 Save to JSON", central)
        save_btn.clicked.connect(self._save_to_json)
        buttons_layout.addWidget(save_btn)
        main_layout.addLayout(buttons_layout)

        if self.solvers:
            self._rebuild_form(self.solvers[0])

    def _clear_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _rebuild_form(self, solver_name):
        self._clear_form()
        self.parameter_widgets = {}
        self.run_file_widget = None
        self.materials_widget = None

        sections = self.solver_definitions.get(solver_name, {})
        for section_name, fields in sections.items():
            emoji = SECTION_EMOJIS.get(section_name.lower(), "📦")
            title = f"{emoji} {section_name.capitalize()}"
            group_box = QtWidgets.QGroupBox(title, self.form_container)
            group_layout = QtWidgets.QFormLayout(group_box)
            group_layout.setContentsMargins(10, 10, 10, 10)
            group_layout.setSpacing(8)
            self.parameter_widgets[section_name] = {}

            for field in fields:
                field_name = field["Name"]
                widget = create_field_widget(field, parent=group_box)
                self.parameter_widgets[section_name][field_name] = widget
                group_layout.addRow(field_name, widget)
                if section_name.lower() == "source":
                    if field_name == "RunFile" and isinstance(widget, PathFieldWidget):
                        self.run_file_widget = widget
                        widget.pathChanged.connect(self._handle_run_file_changed)
                    if field_name == "Materials" and isinstance(widget, MaterialsTableWidget):
                        self.materials_widget = widget

            self.form_layout.addWidget(group_box)

        self.form_layout.addStretch(1)
        if self.run_file_widget and self.run_file_widget.value().strip():
            self._handle_run_file_changed(self.run_file_widget.value())

    def _handle_run_file_changed(self, path_str):
        if not self.materials_widget:
            return
        run_path_value = (path_str or "").strip()
        if not run_path_value:
            return
        try:
            candidate_path = Path(run_path_value).expanduser()
        except (OSError, RuntimeError, ValueError):
            return
        if not candidate_path.exists():
            return
        run_input = str(candidate_path)
        try:
            material_names = run_reader(run_input)
        except FileNotFoundError:
            return
        except Exception as exc:
            error_signature = (run_input, str(exc))
            if self._last_run_reader_error != error_signature:
                self._last_run_reader_error = error_signature
                QtWidgets.QMessageBox.warning(
                    self,
                    "Run File Error",
                    f"Unable to read materials from '{run_input}':\n{exc}",
                )
            return

        self._last_run_reader_error = None
        self.materials_widget.populate_from_names(material_names)

    def _save_to_json(self):
        solver_name = self.solver_combo.currentText()
        if not solver_name:
            QtWidgets.QMessageBox.warning(self, "Missing Solver", "Please select a solver before saving.")
            return

        collected_parameters = {}
        for section_name, fields in self.parameter_widgets.items():
            section_data = {}
            for field_name, widget in fields.items():
                try:
                    section_data[field_name] = widget.value()
                except Exception as exc:  # report faulty widget instead of crashing
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Error Collecting Data",
                        f"Failed to read value for '{field_name}' in '{section_name}': {exc}",
                    )
                    return
            collected_parameters[section_name] = section_data

        try:
            formatted_payload = format_solver_payload(solver_name, collected_parameters)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Formatting Error",
                f"Failed to format data for '{solver_name}': {exc}",
            )
            return

        output_path_text = self.output_path_widget.value().strip() if hasattr(self, "output_path_widget") else ""
        if not output_path_text:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Output Path",
                "Please choose an output file path before saving.",
            )
            return

        output_path = Path(output_path_text).expanduser()
        if not output_path.is_absolute():
            output_path = self.root_dir / output_path

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "File Error",
                f"Could not create directory for {output_path}:\n{exc}",
            )
            return

        existing_payload = {}
        if output_path.exists():
            try:
                with open(output_path, "r", encoding="utf-8") as fh:
                    existing_payload = json.load(fh) or {}
                if not isinstance(existing_payload, dict):
                    existing_payload = {}
            except (OSError, json.JSONDecodeError):
                existing_payload = {}

        final_payload = existing_payload
        final_payload.update(formatted_payload)

        try:
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(final_payload, fh, indent=4)
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "File Error", f"Could not write to {output_path}:\n{exc}")
            return

        QtWidgets.QMessageBox.information(self, "Success", f"Configuration saved to {output_path}")


def main():
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
