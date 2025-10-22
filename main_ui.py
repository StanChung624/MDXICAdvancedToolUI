import copy
import json
import os
import shlex
import subprocess
from pathlib import Path

from PySide6 import QtWidgets

from config_manager import load_tool_path, save_tool_path
from run_reader import run_reader
from ui.constants import SECTION_EMOJIS, STRUCTURE_DEFINITION
from ui.field_widgets import MaterialsTableWidget, PathFieldWidget, create_field_widget
from ui.formatters import format_solver_payload


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

        tool_layout = QtWidgets.QHBoxLayout()
        tool_label = QtWidgets.QLabel("🧮 Tool Executable:", central)
        self.tool_path_widget = PathFieldWidget(
            {
                "Name": "MDXICAdvancedTool",
                "type": "path finder",
                "mode": "file",
                "dialog": "open",
                "caption": "Select MDXICAdvancedTool executable",
                "filter": "Executable Files (*.exe);;All Files (*)",
                "default_suffix": "exe",
            },
            parent=central,
        )
        self.tool_path_widget.line_edit.setPlaceholderText("Select MDXICAdvancedTool executable")
        stored_tool_path = load_tool_path()
        if stored_tool_path:
            self.tool_path_widget.set_path(stored_tool_path)
        self.tool_path_widget.pathChanged.connect(self._persist_tool_path)
        self.run_solver_combo = QtWidgets.QComboBox(central)
        self.run_solver_combo.addItems(
            [
                "MappingTool",
                "ThermalCycleCalc",
                "DelamAlert",
                "PressureOven",
            ]
        )
        self.run_button = QtWidgets.QPushButton("▶ Run", central)
        self.run_button.clicked.connect(self._run_tool)
        tool_layout.addWidget(tool_label)
        tool_layout.addWidget(self.tool_path_widget, 1)
        tool_layout.addWidget(self.run_solver_combo)
        tool_layout.addWidget(self.run_button)
        main_layout.addLayout(tool_layout)

        solver_layout = QtWidgets.QHBoxLayout()
        solver_label = QtWidgets.QLabel("🧠 Solver:", central)
        self.solver_combo = QtWidgets.QComboBox(central)
        self.solver_combo.addItems(self.solvers)
        self.solver_combo.currentTextChanged.connect(self._rebuild_form)
        solver_layout.addWidget(solver_label)
        solver_layout.addWidget(self.solver_combo, 1)
        main_layout.addLayout(solver_layout)

        self.scroll_area = QtWidgets.QScrollArea(central)
        self.scroll_area.setWidgetResizable(True)
        self.form_container = QtWidgets.QWidget()
        self.form_layout = QtWidgets.QVBoxLayout(self.form_container)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(10)
        self.scroll_area.setWidget(self.form_container)
        main_layout.addWidget(self.scroll_area, 1)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.addWidget(QtWidgets.QLabel("💾 Output File:", central))
        self.output_path_widget = PathFieldWidget(
            {
                "Name": "OutputFile",
                "type": "path finder",
                "mode": "file",
                "dialog": "open",
                "caption": "Select output JSON file",
                "filter": "JSON Files (*.json);;All Files (*)",
                "default_suffix": "json",
            },
            parent=central,
        )
        default_output_path = self.root_dir / "ic_advanced_source.json"
        self.output_path_widget.set_path(str(default_output_path))
        footer_layout.addWidget(self.output_path_widget, 1)
        save_btn = QtWidgets.QPushButton("💾 Save to JSON", central)
        save_btn.clicked.connect(self._save_to_json)
        footer_layout.addWidget(save_btn)
        load_btn = QtWidgets.QPushButton("📂 Load from JSON", central)
        load_btn.clicked.connect(self._load_from_json)
        footer_layout.addWidget(load_btn)
        main_layout.addLayout(footer_layout)

        if self.solvers:
            self._rebuild_form(self.solvers[0])

    def _clear_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _persist_tool_path(self, path_str):
        cleaned = (path_str or "").strip()
        if cleaned:
            try:
                cleaned = os.fspath(Path(cleaned).expanduser())
            except (OSError, RuntimeError, ValueError):
                pass
        save_tool_path(cleaned)

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

    def _collect_current_parameters(self):
        solver_name = self.solver_combo.currentText()
        if not solver_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Solver",
                "Please select a solver before continuing.",
            )
            return None

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
                    return None
            collected_parameters[section_name] = section_data
        return solver_name, collected_parameters

    def _resolve_output_path(self):
        output_path_text = self.output_path_widget.value().strip() if hasattr(self, "output_path_widget") else ""
        if not output_path_text:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Output Path",
                "Please choose an output file path before proceeding.",
            )
            return None

        output_path = Path(output_path_text).expanduser()
        if not output_path.is_absolute():
            output_path = self.root_dir / output_path
        return output_path

    def _save_to_json(self, show_message=True, solver_data=None, selected_solver=None):
        if solver_data is None:
            solver_data = self._collect_current_parameters()
        if solver_data is None:
            return None
        solver_name, collected_parameters = solver_data

        try:
            target_solver = selected_solver or solver_name
            formatted_payload = format_solver_payload(target_solver, collected_parameters)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Formatting Error",
                f"Failed to format data for '{target_solver}': {exc}",
            )
            return None

        output_path = self._resolve_output_path()
        if output_path is None:
            return None

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "File Error",
                f"Could not create directory for {output_path}:\n{exc}",
            )
            return None

        existing_payload = {}
        if output_path.exists():
            try:
                with open(output_path, "r", encoding="utf-8") as fh:
                    existing_payload = json.load(fh) or {}
                if not isinstance(existing_payload, dict):
                    existing_payload = {}
            except (OSError, json.JSONDecodeError):
                existing_payload = {}

        final_payload = {}
        final_payload.update(existing_payload)
        final_payload.update(formatted_payload)

        try:
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(final_payload, fh, indent=4)
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "File Error", f"Could not write to {output_path}:\n{exc}")
            return None

        if show_message:
            QtWidgets.QMessageBox.information(self, "Success", f"Configuration saved to {output_path}")
        return output_path

    def _run_tool(self):
        solver_data = self._collect_current_parameters()
        if solver_data is None:
            return

        selected_solver = self.run_solver_combo.currentText() if hasattr(self, "run_solver_combo") else ""
        solver_mapping = {
            "MappingTool": "mt",
            "ThermalCycleCalc": "tc",
            "DelamAlert": "da",
            "PressureOven": "po",
        }
        solver_code = solver_mapping.get(selected_solver)
        if not solver_code:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Solver Selection",
                "Please choose which solver to run.",
            )
            return

        tool_path_text = self.tool_path_widget.value().strip() if hasattr(self, "tool_path_widget") else ""
        if not tool_path_text:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Executable",
                "Please choose the MDXICAdvancedTool executable before running.",
            )
            return

        tool_path = Path(tool_path_text).expanduser()
        if not tool_path.is_absolute():
            tool_path = self.root_dir / tool_path
        if not tool_path.exists():
            QtWidgets.QMessageBox.critical(
                self,
                "Executable Not Found",
                f"No executable found at '{tool_path}'.",
            )
            return
        if tool_path.is_dir():
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Executable",
                f"'{tool_path}' is a directory. Please select the MDXICAdvancedTool executable file.",
            )
            return

        output_path = self._save_to_json(
            show_message=False,
            solver_data=solver_data,
            selected_solver=selected_solver,
        )
        if output_path is None:
            return

        command = [
            os.fspath(tool_path),
            "--solver",
            solver_code,
            "-i",
            os.fspath(output_path),
        ]

        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Execution Error",
                f"Failed to start MDXICAdvancedTool:\n{exc}",
            )
            return

        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip()
            if not details:
                details = f"Process exited with code {completed.returncode}."
            QtWidgets.QMessageBox.critical(
                self,
                "Tool Execution Failed",
                f"{self._format_command(command)}\n\n{details}",
            )
            return

        success_message = completed.stdout.strip() or "MDXICAdvancedTool finished successfully."
        if completed.stderr.strip():
            success_message += f"\n\nWarnings:\n{completed.stderr.strip()}"
        QtWidgets.QMessageBox.information(
            self,
            "Tool Execution Finished",
            success_message,
        )

    @staticmethod
    def _format_command(command_parts):
        if os.name == "nt":
            return subprocess.list2cmdline(command_parts)
        if hasattr(shlex, "join"):
            return shlex.join(command_parts)
        return " ".join(shlex.quote(part) for part in command_parts)

    def _load_from_json(self):
        output_path_text = self.output_path_widget.value().strip() if hasattr(self, "output_path_widget") else ""
        if not output_path_text:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing JSON Path",
                "Please choose a JSON file to load.",
            )
            return

        candidate_path = Path(output_path_text).expanduser()
        if not candidate_path.is_absolute():
            candidate_path = self.root_dir / candidate_path
        if not candidate_path.exists():
            QtWidgets.QMessageBox.warning(
                self,
                "File Not Found",
                f"No JSON file found at '{candidate_path}'.",
            )
            return

        try:
            with open(candidate_path, "r", encoding="utf-8") as handle:
                raw_payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to read configuration:\n{exc}",
            )
            return

        solver_name, solver_payload = self._select_solver_from_payload(raw_payload)
        if not solver_name or not isinstance(solver_payload, dict):
            QtWidgets.QMessageBox.warning(
                self,
                "Unsupported Configuration",
                "The selected JSON does not contain data for the available solvers.",
            )
            return

        sections = self._prepare_section_values(solver_name, solver_payload)

        self.solver_combo.blockSignals(True)
        solver_index = self.solver_combo.findText(solver_name)
        if solver_index >= 0:
            self.solver_combo.setCurrentIndex(solver_index)
        self.solver_combo.blockSignals(False)
        self._rebuild_form(solver_name)
        self._apply_section_values(sections)

        QtWidgets.QMessageBox.information(
            self,
            "Configuration Loaded",
            f"Parameters updated from '{candidate_path}'.",
        )

    SOLVER_KEY_ALIASES = {
        "MappingTool": ["MappingTool", "Maptools"],
        "ReliabilityTools": ["ReliabilityTools"],
        "PressureOven": ["PressureOven"],
    }

    def _select_solver_from_payload(self, payload):
        if not isinstance(payload, dict):
            return None, None

        current_solver = self.solver_combo.currentText()
        solver_candidates = [solver for solver in [current_solver] + list(self.solvers) if solver]
        seen = set()
        ordered_candidates = []
        for solver in solver_candidates:
            if solver not in seen:
                ordered_candidates.append(solver)
                seen.add(solver)

        for solver in ordered_candidates:
            for alias in self.SOLVER_KEY_ALIASES.get(solver, []):
                solver_payload = self._case_insensitive_get(payload, alias)
                if isinstance(solver_payload, dict):
                    return solver, solver_payload

        dict_entries = [(str(key), value) for key, value in payload.items() if isinstance(value, dict)]
        if len(dict_entries) == 1:
            key, value = dict_entries[0]
            inferred_solver = self._infer_solver_from_key(key) or current_solver
            return inferred_solver, value

        return None, None

    def _infer_solver_from_key(self, key):
        lowered = str(key).lower()
        for solver, aliases in self.SOLVER_KEY_ALIASES.items():
            for alias in aliases:
                if lowered == alias.lower():
                    return solver
        return None

    def _prepare_section_values(self, solver_name, solver_payload):
        if solver_name == "PressureOven":
            return self._prepare_pressure_oven_sections(solver_payload)

        sections = {}
        solver_sections = self.solver_definitions.get(solver_name, {})
        for section_name in solver_sections:
            section_payload = self._case_insensitive_get(solver_payload, section_name)
            if isinstance(section_payload, dict):
                sections[section_name] = section_payload
        return sections

    def _prepare_pressure_oven_sections(self, solver_payload):
        if not isinstance(solver_payload, dict):
            return {}

        ramp_rows = []
        ramp_payload = solver_payload.get("PressureRampProfile") or {}
        if isinstance(ramp_payload, dict):
            increments = ramp_payload.get("Pressure increment (Pa)") or []
            time_marks = ramp_payload.get("Time mark (s)") or []
            for increment, time_mark in zip(increments, time_marks):
                ramp_rows.append(
                    {
                        "Pressure increment (Pa)": increment,
                        "Time mark (s)": time_mark,
                    }
                )

        return {
            "general": {
                "OutputFolder": solver_payload.get("OutputFolder", ""),
                "Void shape (Cylindrical/Spherical)": solver_payload.get("Void shape (Cylindrical/Spherical)", ""),
            },
            "material properties": solver_payload.get("MaterialProperties", {}),
            "process conditions": solver_payload.get("ProcessConditions", {}),
            "pressure ramp profile": {
                "Pressure Ramp Profile": ramp_rows,
            },
        }

    def _apply_section_values(self, sections):
        for section_name, fields in self.parameter_widgets.items():
            section_payload = sections.get(section_name) if sections else None
            if not isinstance(section_payload, dict):
                continue
            for field_name, widget in fields.items():
                value = self._case_insensitive_get(section_payload, field_name)
                if value is None:
                    continue
                self._set_widget_value(widget, value)

    @staticmethod
    def _case_insensitive_get(container, key):
        if not isinstance(container, dict):
            return None
        target = str(key).lower()
        for candidate, value in container.items():
            if str(candidate).lower() == target:
                return value
        return None

    def _set_widget_value(self, widget, value):
        setter = getattr(widget, "set_value", None)
        if callable(setter):
            setter(value)
            return
        if isinstance(widget, PathFieldWidget):
            widget.set_path(str(value), emit_change=False)
            return
        if hasattr(widget, "line_edit"):
            widget.line_edit.setText("" if value is None else str(value))


def main():
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
