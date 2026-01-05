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
                                        "FailureModel: Tsai-Wu Criterion",
                                        "FailureModel: Maximum Stress Criterion",
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
                                                    "Name": "YoungModulus (MPa)",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "YieldStress (MPa)",
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
                                                {
                                                    "Name": "Epislon_f",
                                                    "type": "number",
                                                },
                                            ],
                                        },
                                        {
                                            "Name": "FailureModel: Tsai-Wu Criterion",
                                            "fields": [
                                                {
                                                    "Name": "Xt (MPa)",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "Xc (MPa)",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "Yt (MPa)",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "Yc (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "Zt (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "Zc (MPa)",
                                                    "type": "number",
                                                },
                                                {
                                                    "Name": "S12 (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "S23 (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "S13 (MPa)",
                                                    "type": "number",
                                                },
                                            ],
                                        },
                                        {
                                            "Name": "FailureModel: Maximum Stress Criterion",
                                            "fields": [
                                                {
                                                    "Name": "X (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "Y (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "Z (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "S12 (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "S23 (MPa)",
                                                    "type": "number",
                                                },                                                
                                                {
                                                    "Name": "S13 (MPa)",
                                                    "type": "number",
                                                },                                                
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

