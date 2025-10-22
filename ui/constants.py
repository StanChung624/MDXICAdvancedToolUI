SECTION_EMOJIS = {
    "source": "📁",
    "target": "🎯",
    "configuration": "⚙️",
    "materials": "🧬",
    "model": "🧠",
    "general": "📋",
    "material properties": "🧪",
    "process conditions": "⏱️",
    "pressure ramp profile": "📈",
}


STRUCTURE_DEFINITION = {
    "solver": [
        "ReliabilityTools",
        "MappingTool",
        "PressureOven",
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
        {
            "PressureOven": [
                {
                    "general": [
                        {
                            "Name": "OutputFolder",
                            "type": "path finder",
                            "mode": "directory",
                            "caption": "Select an output directory",
                        },
                        {
                            "Name": "Void shape (Cylindrical/Spherical)",
                            "type": "list",
                            "list": [
                                "Cylindrical",
                                "Spherical",
                            ],
                        },
                    ],
                },
                {
                    "material properties": [
                        {
                            "Name": "Henry's coef. (mol N^-1 m^-1)",
                            "type": "number",
                        },
                        {
                            "Name": "Diffusivity of air concentration (m^2 s^-1)",
                            "type": "number",
                        },
                        {
                            "Name": "Surface tension coef. (N m^-1)",
                            "type": "number",
                        },
                        {
                            "Name": "Avogadro const. (m^3 Pa K^-1 mol^-1)",
                            "type": "number",
                        },
                    ],
                },
                {
                    "process conditions": [
                        {
                            "Name": "Working temperature (K)",
                            "type": "number",
                        },
                        {
                            "Name": "Initial void radius (m)",
                            "type": "number",
                        },
                        {
                            "Name": "Initial pressure (Pa)",
                            "type": "number",
                        },
                        {
                            "Name": "Process time (s)",
                            "type": "number",
                        },
                    ],
                },
                {
                    "pressure ramp profile": [
                        {
                            "Name": "Pressure Ramp Profile",
                            "type": "table",
                            "columns": [
                                {
                                    "Name": "Pressure increment (Pa)",
                                    "type": "number",
                                },
                                {
                                    "Name": "Time mark (s)",
                                    "type": "number",
                                },
                            ],
                        }
                    ],
                },
            ]
        },
    ],
}

