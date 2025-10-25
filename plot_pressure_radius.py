from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Tuple

try:
    import matplotlib.pyplot as plt  # type: ignore[import]
except ImportError:  # pragma: no cover - fallback path
    plt = None


def load_columns(path: Path) -> Tuple[List[float], List[float], List[float]]:
    time: List[float] = []
    radius: List[float] = []
    pressure: List[float] = []

    with path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            time.append(float(row["time_seconds"]))
            radius.append(float(row["R_microns"]))
            pressure.append(float(row["P_Pa"]))

    if not time:
        raise ValueError("No data rows found in CSV file.")

    return time, radius, pressure


def plot_with_matplotlib(time: Iterable[float],
                         radius: Iterable[float],
                         pressure: Iterable[float],
                         save_png_path: Path) -> None:
    
    pressure = [p/1000 for p in pressure] # to KPa

    fig, (ax_radius, ax_pressure) = plt.subplots(  # type: ignore[union-attr]
        2,
        1,
        figsize=(8, 6),
        sharex=True,
    )

    ax_radius.plot(time, radius, "--b")
    ax_radius.set_ylabel("Radius (µm)")
    ax_radius.grid(linestyle="dotted", linewidth=1)

    ax_pressure.plot(time, pressure, "--b")
    ax_pressure.set_xlabel("Time (s)")
    ax_pressure.set_ylabel("Pressure (KPa)")
    ax_pressure.grid(linestyle="dotted", linewidth=1)

    fig.tight_layout()
    fig.savefig(save_png_path, dpi=300)


def plot_to_svg(time: List[float],
                radius: List[float],
                pressure: List[float],
                output_path) -> None:
    width, height = 960, 600
    margin = 60
    separation = 40
    panel_height = (height - 3 * margin - separation) // 2

    def scale(value: float, domain_min: float, domain_max: float, length: float) -> float:
        if domain_max == domain_min:
            return 0.0
        return (value - domain_min) / (domain_max - domain_min) * length

    t_min, t_max = min(time), max(time)
    r_min, r_max = min(radius), max(radius)
    p_min, p_max = min(pressure), max(pressure)

    time_coords = [
        margin + scale(t, t_min, t_max, width - 2 * margin)
        for t in time
    ]

    def polyline(y_values: List[float],
                 y_min: float,
                 y_max: float,
                 top: float) -> str:
        coords = []
        for x, y in zip(time_coords, y_values):
            offset = scale(y, y_min, y_max, panel_height)
            coords.append(f"{x:.2f},{top + panel_height - offset:.2f}")
        return " ".join(coords)

    radius_path = polyline(radius, r_min, r_max, margin)
    pressure_path = polyline(pressure, p_min, p_max, margin + panel_height + separation)

    svg_path = Path(output_path+'.svg')
    with svg_path.open("w") as handle:
        handle.write(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">\n'
        )
        handle.write('<style>text{font-family:Arial,sans-serif;font-size:16px;}</style>\n')

        # Radius panel frame and labels
        handle.write(
            f'<rect x="{margin}" y="{margin}" '
            f'width="{width - 2 * margin}" height="{panel_height}" '
            'fill="none" stroke="#444" stroke-width="1"/>\n'
        )
        handle.write(
            f'<text x="{margin}" y="{margin - 20}" fill="#111">'
            'Radius (micron)</text>\n'
        )

        # Pressure panel frame and labels
        pressure_top = margin + panel_height + separation
        handle.write(
            f'<rect x="{margin}" y="{pressure_top}" '
            f'width="{width - 2 * margin}" height="{panel_height}" '
            'fill="none" stroke="#444" stroke-width="1"/>\n'
        )
        handle.write(
            f'<text x="{margin}" y="{pressure_top - 20}" fill="#111">'
            'Pressure (Pa)</text>\n'
        )
        handle.write(
            f'<text x="{margin}" y="{height - margin / 2}" fill="#111">'
            'Time (s)</text>\n'
        )

        handle.write(
            f'<polyline points="{radius_path}" fill="none" stroke="#1f77b4" '
            'stroke-width="2" stroke-dasharray="8 4"/>\n'
        )
        handle.write(
            f'<polyline points="{pressure_path}" fill="none" stroke="#1f77b4" '
            'stroke-width="2" stroke-dasharray="8 4"/>\n'
        )

        handle.write("</svg>\n")


def main() -> None:
    csv_path = Path("pressure_radius_history.csv")
    time, radius, pressure = load_columns(csv_path)
    plot_with_matplotlib(time, radius, pressure, csv_path.with_suffix('.png'))


if __name__ == "__main__":
    main()
