import re
from pathlib import Path, PureWindowsPath

from PySide6 import QtCore


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
    if solver_name == "PressureOven":
        return {"PressureOven": format_pressure_oven(parameters)}
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


def format_pressure_oven(parameters):
    general = parameters.get("general", {})
    mat_props = parameters.get("material properties", {})
    proc_conditions = parameters.get("process conditions", {})
    ramp_section = parameters.get("pressure ramp profile", {})

    payload = {}

    output_folder = general.get("OutputFolder")
    if output_folder not in ("", None):
        payload["OutputFolder"] = stringify_value(output_folder)

    void_shape = general.get("Void shape (Cylindrical/Spherical)")
    if void_shape not in ("", None):
        payload["Void shape (Cylindrical/Spherical)"] = stringify_value(void_shape)

    material_properties = {
        key: stringify_value(value)
        for key, value in mat_props.items()
        if value not in ("", None)
    }
    if material_properties:
        payload["MaterialProperties"] = material_properties

    process_conditions = {
        key: stringify_value(value)
        for key, value in proc_conditions.items()
        if value not in ("", None)
    }
    if process_conditions:
        payload["ProcessConditions"] = process_conditions

    ramp_rows = ramp_section.get("Pressure Ramp Profile")
    ramp_profile = format_pressure_ramp_profile(ramp_rows)
    if ramp_profile:
        payload["PressureRampProfile"] = ramp_profile

    return payload


def format_pressure_ramp_profile(rows):
    if not rows:
        return {}

    increments = []
    time_marks = []
    has_data = False

    for row in rows:
        if not isinstance(row, dict):
            continue
        increment = row.get("Pressure increment (Pa)")
        time_mark = row.get("Time mark (s)")
        if increment in ("", None) or time_mark in ("", None):
            continue
        increments.append(stringify_value(increment))
        time_marks.append(stringify_value(time_mark))
        has_data = True

    if not has_data:
        return {}

    return {
        "Pressure increment (Pa)": increments,
        "Time mark (s)": time_marks,
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

        if model_choice:
            model_entries.sort(key=lambda item: 0 if item["Model"]["Name"] == model_choice else 1)

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

