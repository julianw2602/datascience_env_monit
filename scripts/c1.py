import json
import re
from pathlib import Path

import pandas as pd
from IPython.display import SVG, display

project_root = next(
    (
        path
        for path in (Path.cwd(), *Path.cwd().parents)
        if (path / "data/snapshots").is_dir()
        and (path / "flux4student/world.json").is_file()
    ),
    None,
)
if project_root is None:
    raise FileNotFoundError("Could not locate the project data and world map.")

zip_files = sorted((project_root / "data/raw").glob("*.zip"))
if len(zip_files) != 5:
    raise FileNotFoundError(
        f"Expected five tower ZIP files in data/raw, found {len(zip_files)}."
    )
site_ids = []
for zip_file in zip_files:
    match = re.match(r"^[^_]+_([^_]+)_FLUXNET_", zip_file.name)
    if match is None:
        raise ValueError(f"Could not extract a site ID from {zip_file.name!r}.")
    site_ids.append(match.group(1))
if len(set(site_ids)) != 5:
    raise ValueError("The five tower ZIP files do not contain five unique site IDs.")

snapshot_files = sorted((project_root / "data/snapshots").glob("*.csv"))
if not snapshot_files:
    raise FileNotFoundError("No FLUXNET Shuttle snapshot CSV found in data/snapshots.")
snapshot_file = snapshot_files[-1]
snapshot = pd.read_csv(snapshot_file)
site_table = snapshot.loc[snapshot["site_id"].isin(site_ids)].copy()
if set(site_table["site_id"]) != set(site_ids) or site_table["site_id"].duplicated().any():
    raise ValueError("The latest snapshot does not contain exactly one row per tower.")

countries = {
    "DE": "Germany",
    "ES": "Spain",
    "FI": "Finland",
    "MN": "Mongolia",
    "US": "United States",
}
site_table["country"] = site_table["site_id"].str[:2].map(countries)
if site_table["country"].isna().any():
    raise ValueError("Could not determine a country for every tower.")
site_table["location_lat"] = pd.to_numeric(site_table["location_lat"])
site_table["location_long"] = pd.to_numeric(site_table["location_long"])

overview = site_table[
    [
        "site_id",
        "site_name",
        "country",
        "igbp",
        "location_lat",
        "location_long",
        "first_year",
        "last_year",
        "data_hub",
        "product_citation",
    ]
].rename(
    columns={
        "site_id": "Site ID",
        "site_name": "Name",
        "country": "Country",
        "igbp": "IGBP",
        "location_lat": "Latitude",
        "location_long": "Longitude",
        "first_year": "First year",
        "last_year": "Last year",
        "data_hub": "Hub",
        "product_citation": "Data citation",
    }
).sort_values("Site ID")
overview["Latitude"] = overview["Latitude"].map(lambda value: f"{value:.5f}")
overview["Longitude"] = overview["Longitude"].map(lambda value: f"{value:.5f}")
overview["First year"] = overview["First year"].astype(int)
overview["Last year"] = overview["Last year"].astype(int)

print(f"Snapshot used: {snapshot_file.name}")
display(overview)


with open("c1.csv", "w", encoding="utf-8") as f:
    overview.to_csv(f, index=False)


#####C2 #####


world = json.loads((project_root / "flux4student/world.json").read_text())
width, height = 1000, 500
left, top = 35, 20
map_width, map_height = 930, 440
min_lon, max_lon = -180, 180
min_lat, max_lat = -60, 85


def project(lon, lat):
    x = left + (lon - min_lon) / (max_lon - min_lon) * map_width
    y = top + (max_lat - lat) / (max_lat - min_lat) * map_height
    return x, y


land_paths = []
for feature in world["features"]:
    geometry = feature["geometry"]
    if geometry is None:
        continue
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"Unsupported map geometry: {geometry['type']}")
    for polygon in polygons:
        for ring in polygon:
            if len(ring) < 3:
                continue
            points = " L ".join(
                f"{project(lon, lat)[0]:.1f} {project(lon, lat)[1]:.1f}"
                for lon, lat, *_ in ring
            )
            land_paths.append(f"M {points} Z")

grid = []
for lon in range(-120, 181, 60):
    x, _ = project(lon, 0)
    grid.append(
        f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" '
        f'y2="{top + map_height}" />'
    )
for lat in range(-30, 61, 30):
    _, y = project(0, lat)
    grid.append(
        f'<line x1="{left}" y1="{y:.1f}" x2="{left + map_width}" '
        f'y2="{y:.1f}" />'
    )

label_offsets = {
    "DE-Geb": (9, -8),
    "ES-LM1": (9, 15),
    "FI-Hyy": (9, -8),
    "MN-Nkh": (9, -8),
    "US-WCr": (9, -8),
}
markers = []
for _, site in site_table.iterrows():
    x, y = project(site["location_long"], site["location_lat"])
    dx, dy = label_offsets[site["site_id"]]
    markers.append(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="site" />'
        f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" class="label">'
        f'{site["site_id"]}</text>'
    )

map_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
 role="img" aria-labelledby="map-title map-desc">
 <title id="map-title">Locations of the five flux towers</title>
 <desc id="map-desc">World map with labeled markers for US-WCr, ES-LM1,
 DE-Geb, FI-Hyy, and MN-Nkh.</desc>
 <style>
  .grid {{ stroke: #ccd3d8; stroke-width: 0.8; }}
  .land {{ fill: #e6eadf; stroke: #86918a; stroke-width: 0.7; }}
  .site {{ fill: #c33b2f; stroke: white; stroke-width: 1.5; }}
  .label {{ font: 13px sans-serif; fill: #202820; paint-order: stroke;
            stroke: white; stroke-width: 3px; stroke-linejoin: round; }}
 </style>
 <rect width="{width}" height="{height}" fill="#f7fafc" />
 <g class="grid">{''.join(grid)}</g>
 <path class="land" fill-rule="evenodd" d="{' '.join(land_paths)}" />
 <g>{''.join(markers)}</g>
</svg>"""

display(SVG(map_svg))
with open("world_map.svg", "w", encoding="utf-8") as svg_file:
    svg_file.write(map_svg)

import zipfile

from IPython.display import Markdown, SVG, display

markdown_c3_parts = []
markdown_c4_parts = []
markdown_c6_parts = []


def display_markdown(text, parts):
    markdown = Markdown(text)
    parts.append(markdown.data)
    display(markdown)


coverage_records = []
for zip_file, site_id in zip(zip_files, site_ids):
    with zipfile.ZipFile(zip_file) as archive:
        hh_files = [
            name for name in archive.namelist()
            if "FLUXMET_HH" in Path(name).name
        ]
        if len(hh_files) != 1:
            raise ValueError(
                f"Expected one FLUXMET_HH CSV in {zip_file.name}, found {len(hh_files)}."
            )
        with archive.open(hh_files[0]) as csv_file:
            half_hours = pd.read_csv(
                csv_file,
                na_values=[-9999],
                usecols=lambda column: column in {
                    "TIMESTAMP_START",
                    "NEE_VUT_REF_QC",
                },
                dtype={"TIMESTAMP_START": str},
            )

    if "TIMESTAMP_START" not in half_hours:
        raise ValueError(f"{hh_files[0]} is missing TIMESTAMP_START.")
    years_for_rows = pd.to_datetime(
        half_hours["TIMESTAMP_START"], format="%Y%m%d%H%M", errors="raise"
    ).dt.year
    if "NEE_VUT_REF_QC" in half_hours:
        yearly_share = half_hours["NEE_VUT_REF_QC"].eq(0).groupby(years_for_rows).mean()
    else:
        yearly_share = pd.Series(
            float("nan"), index=sorted(years_for_rows.unique()), dtype=float
        )

    coverage_records.extend(
        {"site": site_id, "year": int(year), "share": float(share)}
        for year, share in yearly_share.items()
    )

coverage = pd.DataFrame(coverage_records).pivot(
    index="site", columns="year", values="share"
)
coverage = coverage.reindex(
    index=sorted(site_ids),
    columns=range(int(coverage.columns.min()), int(coverage.columns.max()) + 1),
)

best_site_years = coverage.stack()
if best_site_years.empty:
    raise ValueError("No site-year values are available for NEE coverage.")
best_share = best_site_years.max()
best_locations = best_site_years[best_site_years.eq(best_share)]
best_description = ", ".join(
    f"{site} in {year}" for site, year in best_locations.index
)
display_markdown(
    f"Best measured-data coverage was **{best_share:.1%}** at "
    f"{best_description}.",
    markdown_c3_parts,
)

width, height = 1020, 360
left, top = 105, 45
cell_width, cell_height, gap = 26, 38, 4
years = list(coverage.columns)
sites = list(coverage.index)
first_year, last_year = years[0], years[-1]


def coverage_color(value):
    if pd.isna(value):
        return "#d9d9d9"
    low = (247, 251, 255)
    high = (8, 81, 156)
    rgb = tuple(round(start + value * (end - start)) for start, end in zip(low, high))
    return "#" + "".join(f"{channel:02x}" for channel in rgb)


cells = []
for row, site_id in enumerate(sites):
    y = top + row * (cell_height + gap)
    cells.append(
        f'<text x="{left - 12}" y="{y + cell_height / 2:.1f}" '
        f'class="site" text-anchor="end" dominant-baseline="middle">{site_id}</text>'
    )
    for column, year in enumerate(years):
        x = left + column * (cell_width + gap)
        share = coverage.loc[site_id, year]
        fill = coverage_color(share)
        detail = "No QC data" if pd.isna(share) else f"{share:.1%} measured"
        cells.append(
            f'<rect x="{x}" y="{y}" width="{cell_width}" height="{cell_height}" '
            f'rx="2" fill="{fill}"><title>{site_id}, {year}: {detail}</title></rect>'
        )

year_labels = []
label_years = list(range(first_year, last_year + 1, 3))
if last_year not in label_years:
    label_years.append(last_year)
for year in label_years:
    x = left + (year - first_year) * (cell_width + gap) + cell_width / 2
    year_labels.append(
        f'<text x="{x:.1f}" y="{top + len(sites) * (cell_height + gap) + 10}" '
        f'class="year" text-anchor="middle">{year}</text>'
    )

legend_x, legend_y, legend_width, legend_height = left, 315, 220, 16
legend_stops = []
for step in range(21):
    offset = step / 20
    legend_stops.append(
        f'<stop offset="{offset:.0%}" stop-color="{coverage_color(offset)}" />'
    )
legend = (
    f'<defs><linearGradient id="coverage-scale">{ "".join(legend_stops) }</linearGradient></defs>'
    f'<rect x="{legend_x}" y="{legend_y}" width="{legend_width}" '
    f'height="{legend_height}" fill="url(#coverage-scale)" />'
    f'<text x="{legend_x}" y="{legend_y + legend_height + 18}" class="year">0%</text>'
    f'<text x="{legend_x + legend_width / 2}" y="{legend_y + legend_height + 18}" '
    f'class="year" text-anchor="middle">50%</text>'
    f'<text x="{legend_x + legend_width}" y="{legend_y + legend_height + 18}" '
    f'class="year" text-anchor="end">100%</text>'
    f'<rect x="{legend_x + 280}" y="{legend_y}" width="20" height="16" '
    f'fill="{coverage_color(float("nan"))}" />'
    f'<text x="{legend_x + 307}" y="{legend_y + 13}" class="year">No data</text>'
)

heatmap_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
 role="img" aria-labelledby="coverage-title coverage-desc">
 <title id="coverage-title">Measured NEE coverage by site and year</title>
 <desc id="coverage-desc">Heat map of the yearly share of half hours with a
 measured NEE quality flag for each tower.</desc>
 <style>
  .site {{ font: 14px sans-serif; fill: #202820; }}
  .year {{ font: 12px sans-serif; fill: #202820; }}
 </style>
 <text x="{left + ((last_year - first_year + 1) * (cell_width + gap)) / 2}"
  y="20" class="site" text-anchor="middle">Year</text>
 {''.join(cells)}
 {''.join(year_labels)}
 {legend}
</svg>"""
display(SVG(heatmap_svg))

with open("heatmap.svg", "w", encoding="utf-8") as svg_file:
    svg_file.write(heatmap_svg)

variable_headers = {
    "TA_F": "TA_F (°C)",
    "SW_IN_F": "SW_IN_F (W m⁻²)",
    "VPD_F": "VPD_F (hPa)",
    "P_F": "P_F (mm per 30 min; annual sum in mm yr⁻¹)",
    "NEE_VUT_REF": "NEE_VUT_REF (µmol CO₂ m⁻² s⁻¹)",
    "GPP_NT_VUT_REF": "GPP_NT_VUT_REF (µmol CO₂ m⁻² s⁻¹)",
    "RECO_NT_VUT_REF": "RECO_NT_VUT_REF (µmol CO₂ m⁻² s⁻¹)",
    "H_F_MDS": "H_F_MDS (W m⁻²)",
    "LE_F_MDS": "LE_F_MDS (W m⁻²)",
}
variables = list(variable_headers)
table_columns = list(variable_headers.values())
statistic_rows = [
    "Mean (P_F: mean annual sum)",
    "Minimum",
    "Maximum",
    "Missing (%)",
]
site_statistics = []

for zip_file, site_id in zip(zip_files, site_ids):
    with zipfile.ZipFile(zip_file) as archive:
        hh_files = [
            name for name in archive.namelist()
            if "FLUXMET_HH" in Path(name).name
        ]
        if len(hh_files) != 1:
            raise ValueError(
                f"Expected one FLUXMET_HH CSV in {zip_file.name}, found {len(hh_files)}."
            )
        with archive.open(hh_files[0]) as csv_file:
            half_hours = pd.read_csv(
                csv_file,
                na_values=[-9999],
                usecols=lambda column: column in {"TIMESTAMP_START", *variables},
                dtype={"TIMESTAMP_START": str},
            )

    if "TIMESTAMP_START" not in half_hours:
        raise ValueError(f"{hh_files[0]} is missing TIMESTAMP_START.")
    missing_columns = [variable for variable in variables if variable not in half_hours]
    for variable in missing_columns:
        half_hours[variable] = float("nan")

    years_for_rows = pd.to_datetime(
        half_hours["TIMESTAMP_START"], format="%Y%m%d%H%M", errors="raise"
    ).dt.year
    statistics = pd.DataFrame(
        index=statistic_rows, columns=table_columns, dtype=object
    )
    statistics.index.name = "Statistic"

    for variable, header in variable_headers.items():
        values = pd.to_numeric(half_hours[variable], errors="raise")
        if variable == "P_F":
            annual_totals = values.groupby(years_for_rows).sum(min_count=1)
            mean_value = annual_totals.mean()
        else:
            mean_value = values.mean()
        minimum = values.min()
        maximum = values.max()
        missing_percent = values.isna().mean() * 100

        def format_value(value):
            return "—" if pd.isna(value) else f"{value:.2f}"

        statistics.loc["Mean (P_F: mean annual sum)", header] = format_value(mean_value)
        statistics.loc["Minimum", header] = format_value(minimum)
        statistics.loc["Maximum", header] = format_value(maximum)
        statistics.loc["Missing (%)", header] = f"{missing_percent:.1f}%"

    display_markdown(f"### {site_id}", markdown_c3_parts)
    if missing_columns:
        display_markdown(
            "Variables absent from this HH file: "
            + ", ".join(f"`{variable}`" for variable in missing_columns)
            + ". Their summaries are unavailable.",
            markdown_c3_parts,
        )
    display(statistics)
    site_statistics.append(
        statistics.rename_axis("Statistic")
        .reset_index()
        .assign(Site=site_id)
        [["Site", "Statistic", *table_columns]]
    )

    flux_variables = ["NEE_VUT_REF", "GPP_NT_VUT_REF", "RECO_NT_VUT_REF"]
conversion_factor = 1.0378

pd.concat(site_statistics, ignore_index=True).to_csv(
    Path(__file__).resolve().with_name("site_statistics.csv"),
    index=False,
)

script_dir = Path(__file__).resolve().parent
(script_dir / "c3.md").write_text(
    "\n\n".join(markdown_c3_parts),
    encoding="utf-8",
)
daily_records = []

for zip_file, site_id in zip(zip_files, site_ids):
    with zipfile.ZipFile(zip_file) as archive:
        hh_files = [
            name for name in archive.namelist()
            if "FLUXMET_HH" in Path(name).name
        ]
        if len(hh_files) != 1:
            raise ValueError(
                f"Expected one FLUXMET_HH CSV in {zip_file.name}, found {len(hh_files)}."
            )
        with archive.open(hh_files[0]) as csv_file:
            half_hours = pd.read_csv(
                csv_file,
                na_values=[-9999],
                usecols=lambda column: column in {"TIMESTAMP_START", *flux_variables},
                dtype={"TIMESTAMP_START": str},
            )

    if "TIMESTAMP_START" not in half_hours:
        raise ValueError(f"{hh_files[0]} is missing TIMESTAMP_START.")
    for variable in flux_variables:
        if variable not in half_hours:
            half_hours[variable] = float("nan")

    half_hours["day"] = pd.to_datetime(
        half_hours["TIMESTAMP_START"], format="%Y%m%d%H%M", errors="raise"
    ).dt.normalize()
    site_daily = half_hours.groupby("day")[flux_variables].mean()
    complete_days = pd.date_range(site_daily.index.min(), site_daily.index.max(), freq="D")
    site_daily = site_daily.reindex(complete_days).mul(conversion_factor)
    site_daily.index.name = "day"
    site_daily.insert(0, "site", site_id)
    daily_records.append(site_daily.reset_index())

daily_flux = pd.concat(daily_records, ignore_index=True).sort_values(["site", "day"])

check_site = "FI-Hyy"
if check_site not in site_ids:
    raise ValueError(f"Cannot check daily aggregation: {check_site} is not in the tower files.")
check_zip = zip_files[site_ids.index(check_site)]
with zipfile.ZipFile(check_zip) as archive:
    dd_files = [
        name for name in archive.namelist()
        if "FLUXMET_DD" in Path(name).name
    ]
    if len(dd_files) != 1:
        raise ValueError(
            f"Expected one FLUXMET_DD CSV in {check_zip.name}, found {len(dd_files)}."
        )
    with archive.open(dd_files[0]) as csv_file:
        daily_reference = pd.read_csv(
            csv_file,
            na_values=[-9999],
            usecols=lambda column: column in {"TIMESTAMP", *flux_variables},
            dtype={"TIMESTAMP": str},
        )

required_daily_columns = {"TIMESTAMP", *flux_variables}
if not required_daily_columns.issubset(daily_reference.columns):
    missing = sorted(required_daily_columns - set(daily_reference.columns))
    raise ValueError(f"{dd_files[0]} is missing required columns: {', '.join(missing)}.")
daily_reference["day"] = pd.to_datetime(
    daily_reference["TIMESTAMP"], format="%Y%m%d", errors="raise"
)
comparison = daily_flux.loc[daily_flux["site"] == check_site].merge(
    daily_reference[["day", *flux_variables]],
    on="day",
    how="inner",
    suffixes=("_hh", "_dd"),
)
max_difference = 0.0
for variable in flux_variables:
    differences = (
        comparison[f"{variable}_hh"] - comparison[f"{variable}_dd"]
    ).abs().dropna()
    if differences.empty:
        raise ValueError(f"No valid daily comparison values for {check_site} {variable}.")
    max_difference = max(max_difference, differences.max())
if max_difference > 0.01:
    raise AssertionError(
        f"Daily aggregation check for {check_site} differs from FLUXMET_DD "
        f"by as much as {max_difference:.4f} g C m⁻² d⁻¹."
    )
display_markdown(
    f"**Daily aggregation check:** for {check_site}, the converted HH daily "
    f"means agree with `FLUXMET_DD`; the largest absolute difference across "
    f"the three fluxes is {max_difference:.4f} g C m⁻² d⁻¹.",
    markdown_c4_parts,
)

series_colors = {
    "NEE_VUT_REF": "#2166ac",
    "GPP_NT_VUT_REF": "#1a9850",
    "RECO_NT_VUT_REF": "#d95f02",
}
valid_fluxes = daily_flux[flux_variables].stack()
if valid_fluxes.empty:
    raise ValueError("No daily NEE, GPP, or RECO values are available to plot.")
y_min, y_max = min(valid_fluxes.min(), 0), max(valid_fluxes.max(), 0)
y_padding = max((y_max - y_min) * 0.05, 0.5)
y_min, y_max = y_min - y_padding, y_max + y_padding

first_day, last_day = daily_flux["day"].min(), daily_flux["day"].max()
first_ordinal, last_ordinal = first_day.toordinal(), last_day.toordinal()
if first_ordinal == last_ordinal:
    last_ordinal += 1

svg_width, svg_height = 1300, 930
plot_left, plot_width = 125, 1140
panel_top, panel_height, panel_gap = 70, 145, 22
plot_top_offset, plot_bottom_offset = 25, 10
panel_sites = list(site_ids)
panel_area_height = len(panel_sites) * panel_height + (len(panel_sites) - 1) * panel_gap
series_paths = []
axes = []
y_ticks = [y_min + (y_max - y_min) * step / 4 for step in range(5)]
tick_years = [first_day.year]
next_tick_year = (first_day.year // 5 + 1) * 5
tick_years.extend(range(next_tick_year, last_day.year + 1, 5))


def map_x(day):
    return plot_left + (day.toordinal() - first_ordinal) / (
        last_ordinal - first_ordinal
    ) * plot_width


def map_y(value, plot_top, plot_bottom):
    return plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top)


def flux_path(days, values, plot_top, plot_bottom):
    segments = []
    current = []
    for day, value in zip(days, values):
        if pd.isna(value):
            if current:
                segments.append(current)
                current = []
            continue
        command = "M" if not current else "L"
        current.append(f"{command} {map_x(day):.1f} {map_y(value, plot_top, plot_bottom):.1f}")
    if current:
        segments.append(current)
    return " ".join(" ".join(segment) for segment in segments)


for row, site_id in enumerate(panel_sites):
    y = panel_top + row * (panel_height + panel_gap)
    plot_top = y + plot_top_offset
    plot_bottom = y + panel_height - plot_bottom_offset
    axes.append(
        f'<text x="{plot_left}" y="{y + 15}" class="site">{site_id}</text>'
        f'<rect x="{plot_left}" y="{plot_top}" width="{plot_width}" '
        f'height="{plot_bottom - plot_top}" class="panel" />'
    )
    for value in y_ticks:
        grid_y = map_y(value, plot_top, plot_bottom)
        axes.append(
            f'<line x1="{plot_left}" y1="{grid_y:.1f}" '
            f'x2="{plot_left + plot_width}" y2="{grid_y:.1f}" class="grid" />'
            f'<text x="{plot_left - 9}" y="{grid_y + 4:.1f}" class="tick" '
            f'text-anchor="end">{value:.1f}</text>'
        )
    zero_y = map_y(0, plot_top, plot_bottom)
    axes.append(
        f'<line x1="{plot_left}" y1="{zero_y:.1f}" '
        f'x2="{plot_left + plot_width}" y2="{zero_y:.1f}" class="zero" />'
    )
    for year in tick_years:
        tick_day = pd.Timestamp(year=year, month=1, day=1)
        if first_day <= tick_day <= last_day:
            tick_x = map_x(tick_day)
            axes.append(
                f'<line x1="{tick_x:.1f}" y1="{plot_top}" '
                f'x2="{tick_x:.1f}" y2="{plot_bottom}" class="grid" />'
            )
            if row == len(panel_sites) - 1:
                axes.append(
                    f'<text x="{tick_x:.1f}" y="{plot_bottom + 20}" '
                    f'class="tick" text-anchor="middle">{year}</text>'
                )

    site_data = daily_flux.loc[daily_flux["site"] == site_id].sort_values("day")
    if not site_data[flux_variables].notna().any().any():
        axes.append(
            f'<text x="{plot_left + plot_width / 2}" '
            f'y="{(plot_top + plot_bottom) / 2}" class="tick" '
            f'text-anchor="middle">No flux data available</text>'
        )
    for variable, color in series_colors.items():
        path_data = flux_path(
            site_data["day"].tolist(),
            site_data[variable].tolist(),
            plot_top,
            plot_bottom,
        )
        if path_data:
            series_paths.append(
                f'<path d="{path_data}" fill="none" stroke="{color}" '
                'stroke-width="1.1" stroke-opacity="0.9" />'
            )

legend_items = []
for index, (variable, color) in enumerate(series_colors.items()):
    legend_x = plot_left + index * 250
    legend_items.append(
        f'<line x1="{legend_x}" y1="38" x2="{legend_x + 28}" y2="38" '
        f'stroke="{color}" stroke-width="3" />'
        f'<text x="{legend_x + 36}" y="42" class="tick">{variable}</text>'
    )
plot_svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
 viewBox="0 0 {svg_width} {svg_height}" role="img"
 aria-labelledby="flux-title flux-desc">
 <title id="flux-title">Daily NEE, GPP, and RECO for five flux towers</title>
 <desc id="flux-desc">Five vertically stacked site panels showing daily carbon
 fluxes in grams of carbon per square metre per day.</desc>
 <style>
  .site {{ font: bold 14px sans-serif; fill: #202820; }}
  .tick {{ font: 11px sans-serif; fill: #303840; }}
  .grid {{ stroke: #dce1e5; stroke-width: 0.7; }}
  .panel {{ fill: #ffffff; stroke: #aab3ba; stroke-width: 0.8; }}
  .zero {{ stroke: #737d84; stroke-width: 1.1; }}
 </style>
 <rect width="{svg_width}" height="{svg_height}" fill="#ffffff" />
 <g>{''.join(legend_items)}</g>
 <g>{''.join(axes)}</g>
 <g>{''.join(series_paths)}</g>
 <text transform="translate(22 {panel_top + panel_area_height / 2}) rotate(-90)"
  class="tick" text-anchor="middle">Daily carbon exchange (g C m⁻² d⁻¹)</text>
 <text x="{plot_left + plot_width / 2}" y="{svg_height - 10}"
  class="tick" text-anchor="middle">Date</text>
</svg>"""
display(SVG(plot_svg))
with open("daily_flux.svg", "w", encoding="utf-8") as svg_file:
    svg_file.write(plot_svg)


diurnal_variables = ["NEE_VUT_REF", "LE_F_MDS"]
season_order = ["Winter", "Spring", "Summer", "Autumn"]
north_month_season = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}
south_month_season = {
    12: "Summer", 1: "Summer", 2: "Summer",
    3: "Autumn", 4: "Autumn", 5: "Autumn",
    6: "Winter", 7: "Winter", 8: "Winter",
    9: "Spring", 10: "Spring", 11: "Spring",
}
latitude_by_site = site_table.set_index("site_id")["location_lat"].astype(float)
diurnal_records = []

for zip_file, site_id in zip(zip_files, site_ids):
    with zipfile.ZipFile(zip_file) as archive:
        hh_files = [
            name for name in archive.namelist()
            if "FLUXMET_HH" in Path(name).name
        ]
        if len(hh_files) != 1:
            raise ValueError(
                f"Expected one FLUXMET_HH CSV in {zip_file.name}, found {len(hh_files)}."
            )
        with archive.open(hh_files[0]) as csv_file:
            half_hours = pd.read_csv(
                csv_file,
                na_values=[-9999],
                usecols=lambda column: column in {
                    "TIMESTAMP_START",
                    *diurnal_variables,
                },
                dtype={"TIMESTAMP_START": str},
            )

    if "TIMESTAMP_START" not in half_hours:
        raise ValueError(f"{hh_files[0]} is missing TIMESTAMP_START.")
    for variable in diurnal_variables:
        if variable not in half_hours:
            half_hours[variable] = float("nan")

    time = pd.to_datetime(
        half_hours["TIMESTAMP_START"], format="%Y%m%d%H%M", errors="raise"
    )
    month_season = (
        north_month_season if latitude_by_site[site_id] >= 0 else south_month_season
    )
    half_hours["season"] = time.dt.month.map(month_season)
    half_hours["hour"] = time.dt.hour
    hourly = half_hours.groupby(["season", "hour"])[diurnal_variables].mean()
    full_course = pd.MultiIndex.from_product(
        [season_order, range(24)], names=["season", "hour"]
    )
    hourly = hourly.reindex(full_course).reset_index()
    hourly["site"] = site_id
    diurnal_records.append(hourly)

diurnal = pd.concat(diurnal_records, ignore_index=True)
diurnal_colors = {
    "Winter": "#2166ac",
    "Spring": "#1a9850",
    "Summer": "#fdae61",
    "Autumn": "#d73027",
}
diurnal_labels = {
    "NEE_VUT_REF": "NEE_VUT_REF (µmol CO₂ m⁻² s⁻¹)",
    "LE_F_MDS": "LE_F_MDS (W m⁻²)",
}
diurnal_ranges = {}
for variable in diurnal_variables:
    values = diurnal[variable].dropna()
    if values.empty:
        diurnal_ranges[variable] = (-1.0, 1.0)
    else:
        low, high = min(values.min(), 0), max(values.max(), 0)
        padding = max((high - low) * 0.08, 0.5)
        diurnal_ranges[variable] = (low - padding, high + padding)

svg_width, svg_height = 1400, 1195
column_starts = [110, 780]
panel_width, panel_height, row_gap = 580, 195, 20
panel_top = 85
plot_offset_x, plot_width = 50, 500
plot_top_offset, plot_bottom_offset = 25, 28
diurnal_axes = []
diurnal_lines = []


def diurnal_x(hour, plot_left):
    return plot_left + hour / 24 * plot_width


def diurnal_y(value, variable, plot_top, plot_bottom):
    low, high = diurnal_ranges[variable]
    return plot_bottom - (value - low) / (high - low) * (plot_bottom - plot_top)


for column, variable in enumerate(diurnal_variables):
    column_x = column_starts[column]
    diurnal_axes.append(
        f'<text x="{column_x + panel_width / 2}" y="66" class="column-title" '
        f'text-anchor="middle">{diurnal_labels[variable]}</text>'
    )
    low, high = diurnal_ranges[variable]
    y_ticks = [low, 0, high]
    for row, site_id in enumerate(site_ids):
        y = panel_top + row * (panel_height + row_gap)
        plot_left = column_x + plot_offset_x
        plot_right = plot_left + plot_width
        plot_top = y + plot_top_offset
        plot_bottom = y + panel_height - plot_bottom_offset
        diurnal_axes.extend(
            [
                f'<text x="{plot_left}" y="{y + 15}" class="site">{site_id}</text>',
                f'<rect x="{plot_left}" y="{plot_top}" width="{plot_width}" '
                f'height="{plot_bottom - plot_top}" class="panel" />',
            ]
        )
        for value in y_ticks:
            grid_y = diurnal_y(value, variable, plot_top, plot_bottom)
            diurnal_axes.append(
                f'<line x1="{plot_left}" y1="{grid_y:.1f}" '
                f'x2="{plot_right}" y2="{grid_y:.1f}" class="grid" />'
                f'<text x="{plot_left - 7}" y="{grid_y + 4:.1f}" class="tick" '
                f'text-anchor="end">{value:.1f}</text>'
            )
        for hour in (0, 6, 12, 18, 24):
            tick_x = diurnal_x(hour, plot_left)
            diurnal_axes.append(
                f'<line x1="{tick_x:.1f}" y1="{plot_top}" '
                f'x2="{tick_x:.1f}" y2="{plot_bottom}" class="grid" />'
            )
            if row == len(site_ids) - 1:
                diurnal_axes.append(
                    f'<text x="{tick_x:.1f}" y="{plot_bottom + 16}" '
                    f'class="tick" text-anchor="middle">{hour}</text>'
                )

        site_course = diurnal.loc[diurnal["site"] == site_id]
        for season in season_order:
            course = (
                site_course.loc[site_course["season"] == season]
                .set_index("hour")[variable]
                .reindex(range(24))
            )
            commands = []
            started = False
            for hour, value in course.items():
                if pd.isna(value):
                    started = False
                    continue
                command = "L" if started else "M"
                commands.append(
                    f"{command} {diurnal_x(hour, plot_left):.1f} "
                    f"{diurnal_y(value, variable, plot_top, plot_bottom):.1f}"
                )
                started = True
            if commands:
                diurnal_lines.append(
                    f'<path d="{" ".join(commands)}" fill="none" '
                    f'stroke="{diurnal_colors[season]}" stroke-width="2" />'
                )
        if not site_course[variable].notna().any():
            diurnal_axes.append(
                f'<text x="{plot_left + plot_width / 2}" '
                f'y="{(plot_top + plot_bottom) / 2}" class="tick" '
                f'text-anchor="middle">No data</text>'
            )

legend_items = []
for index, season in enumerate(season_order):
    x = 260 + index * 230
    legend_items.append(
        f'<line x1="{x}" y1="35" x2="{x + 28}" y2="35" '
        f'stroke="{diurnal_colors[season]}" stroke-width="3" />'
        f'<text x="{x + 36}" y="39" class="tick">{season}</text>'
    )
diurnal_svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
 viewBox="0 0 {svg_width} {svg_height}" role="img"
 aria-labelledby="diurnal-title diurnal-desc">
 <title id="diurnal-title">Seasonal mean diurnal cycles of NEE and latent heat</title>
 <desc id="diurnal-desc">Five site rows by two variable columns; each line shows
 the seasonal hourly mean.</desc>
 <style>
  .column-title {{ font: bold 15px sans-serif; fill: #202820; }}
  .site {{ font: bold 13px sans-serif; fill: #202820; }}
  .tick {{ font: 10px sans-serif; fill: #303840; }}
  .grid {{ stroke: #dce1e5; stroke-width: 0.7; }}
  .panel {{ fill: #ffffff; stroke: #aab3ba; stroke-width: 0.8; }}
 </style>
 <rect width="{svg_width}" height="{svg_height}" fill="#ffffff" />
 <g>{''.join(legend_items)}</g>
 <g>{''.join(diurnal_axes)}</g>
 <g>{''.join(diurnal_lines)}</g>
 <text x="{column_starts[0] + panel_width / 2}" y="{svg_height - 13}"
  class="tick" text-anchor="middle">Hour of day</text>
 <text x="{column_starts[1] + panel_width / 2}" y="{svg_height - 13}"
  class="tick" text-anchor="middle">Hour of day</text>
</svg>"""
display(SVG(diurnal_svg))
with open("diurnal_cycles.svg", "w", encoding="utf-8") as svg_file:
    svg_file.write(diurnal_svg) 

(script_dir / "c4.md").write_text(
    "\n\n".join(markdown_c4_parts),
    encoding="utf-8",
)

import math

energy_columns = {
    "TIMESTAMP_START",
    "NETRAD",
    "G_F_MDS",
    "H_F_MDS",
    "H_F_MDS_QC",
    "LE_F_MDS",
    "LE_F_MDS_QC",
}
energy_site = None
energy_data = None
for zip_file, site_id in zip(zip_files, site_ids):
    with zipfile.ZipFile(zip_file) as archive:
        hh_files = [
            name for name in archive.namelist()
            if "FLUXMET_HH" in Path(name).name
        ]
        if len(hh_files) != 1:
            raise ValueError(
                f"Expected one FLUXMET_HH CSV in {zip_file.name}, found {len(hh_files)}."
            )
        with archive.open(hh_files[0]) as csv_file:
            candidate = pd.read_csv(
                csv_file,
                na_values=[-9999],
                usecols=lambda column: column in energy_columns,
            )
    if not energy_columns.issubset(candidate.columns):
        continue

    measured = (
        candidate["H_F_MDS_QC"].eq(0)
        & candidate["LE_F_MDS_QC"].eq(0)
        & candidate[["NETRAD", "G_F_MDS", "H_F_MDS", "LE_F_MDS"]]
        .notna()
        .all(axis=1)
    )
    candidate = candidate.loc[measured]
    if not candidate.empty:
        energy_site = site_id
        energy_data = candidate
        break

if energy_data is None:
    raise ValueError("No tower has measured H and LE with NETRAD and G available.")

energy_x = energy_data["NETRAD"] - energy_data["G_F_MDS"]
energy_y = energy_data["H_F_MDS"] + energy_data["LE_F_MDS"]
x_center, y_center = energy_x.mean(), energy_y.mean()
x_deviations = energy_x - x_center
if x_deviations.pow(2).sum() == 0:
    raise ValueError(f"{energy_site} has no x-axis variation for the energy fit.")
energy_slope = (x_deviations * (energy_y - y_center)).sum() / x_deviations.pow(2).sum()
energy_intercept = y_center - energy_slope * x_center

domain_min = min(energy_x.min(), energy_y.min(), 0)
domain_max = max(energy_x.max(), energy_y.max(), 0)
domain_padding = max((domain_max - domain_min) * 0.05, 10)
domain_min, domain_max = domain_min - domain_padding, domain_max + domain_padding
chart_size = 510
chart_left, chart_top = 125, 75
chart_bottom = chart_top + chart_size


def energy_map_x(value):
    return chart_left + (value - domain_min) / (domain_max - domain_min) * chart_size


def energy_map_y(value):
    return chart_bottom - (value - domain_min) / (domain_max - domain_min) * chart_size


sample_stride = max(1, math.ceil(len(energy_data) / 20000))
scatter_sample = energy_data.iloc[::sample_stride]
scatter_points = []
for _, point in scatter_sample.iterrows():
    x_value = point["NETRAD"] - point["G_F_MDS"]
    y_value = point["H_F_MDS"] + point["LE_F_MDS"]
    scatter_points.append(
        f'<circle cx="{energy_map_x(x_value):.1f}" '
        f'cy="{energy_map_y(y_value):.1f}" r="1.7" />'
    )

energy_ticks = [domain_min, 0, domain_max]
energy_axes = []
for value in energy_ticks:
    x_position, y_position = energy_map_x(value), energy_map_y(value)
    energy_axes.append(
        f'<line x1="{chart_left}" y1="{y_position:.1f}" '
        f'x2="{chart_left + chart_size}" y2="{y_position:.1f}" class="grid" />'
        f'<line x1="{x_position:.1f}" y1="{chart_top}" '
        f'x2="{x_position:.1f}" y2="{chart_bottom}" class="grid" />'
        f'<text x="{chart_left - 9}" y="{y_position + 4:.1f}" class="tick" '
        f'text-anchor="end">{value:.0f}</text>'
        f'<text x="{x_position:.1f}" y="{chart_bottom + 20}" class="tick" '
        f'text-anchor="middle">{value:.0f}</text>'
    )
fit_path = (
    f"M {energy_map_x(domain_min):.1f} "
    f"{energy_map_y(energy_slope * domain_min + energy_intercept):.1f} "
    f"L {energy_map_x(domain_max):.1f} "
    f"{energy_map_y(energy_slope * domain_max + energy_intercept):.1f}"
)
energy_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 700"
 role="img" aria-labelledby="energy-title energy-desc">
 <title id="energy-title">Energy balance at {energy_site}</title>
 <desc id="energy-desc">Measured half hours of H plus LE against net radiation
 minus ground heat, with the one-to-one line and a linear fit.</desc>
 <style>
  .tick {{ font: 12px sans-serif; fill: #303840; }}
  .grid {{ stroke: #dce1e5; stroke-width: 0.8; }}
 </style>
 <text x="410" y="28" class="tick" text-anchor="middle">
  Energy balance — {energy_site}; fit slope = {energy_slope:.3f}</text>
 <defs><clipPath id="energy-clip"><rect x="{chart_left}" y="{chart_top}"
  width="{chart_size}" height="{chart_size}" /></clipPath></defs>
 <rect x="{chart_left}" y="{chart_top}" width="{chart_size}" height="{chart_size}"
  fill="#ffffff" stroke="#66727a" />
 <g>{''.join(energy_axes)}</g>
 <g clip-path="url(#energy-clip)">
  <line x1="{energy_map_x(domain_min):.1f}" y1="{energy_map_y(domain_min):.1f}"
   x2="{energy_map_x(domain_max):.1f}" y2="{energy_map_y(domain_max):.1f}"
   stroke="#252525" stroke-width="2" stroke-dasharray="7 5" />
  <path d="{fit_path}" fill="none" stroke="#c33b2f" stroke-width="2.5" />
  <g fill="#2166ac" fill-opacity="0.22">{''.join(scatter_points)}</g>
 </g>
 <line x1="505" y1="52" x2="535" y2="52" stroke="#252525"
  stroke-width="2" stroke-dasharray="7 5" />
 <text x="542" y="56" class="tick">1:1</text>
 <line x1="600" y1="52" x2="630" y2="52" stroke="#c33b2f" stroke-width="2.5" />
 <text x="637" y="56" class="tick">Linear fit</text>
 <text x="{chart_left + chart_size / 2}" y="{chart_bottom + 55}" class="tick"
  text-anchor="middle">NETRAD − G_F_MDS (W m⁻²)</text>
 <text transform="translate(30 {chart_top + chart_size / 2}) rotate(-90)"
  class="tick" text-anchor="middle">H_F_MDS + LE_F_MDS (W m⁻²)</text>
</svg>"""
display(SVG(energy_svg))
display_markdown(
    f"At {energy_site}, the fitted slope was **{energy_slope:.3f}** "
    f"from {len(energy_data):,} measured half hours.",
    markdown_c6_parts,
)

# Cross-site comparison
daily_with_year = daily_flux.assign(year=daily_flux["day"].dt.year)
annual_group = daily_with_year.groupby(["site", "year"])["NEE_VUT_REF"]
annual_nee = annual_group.sum(min_count=1)
valid_days = annual_group.count()
expected_days = daily_with_year.groupby(["site", "year"]).size()
annual_summary = pd.DataFrame(
    {
        "annual_nee": annual_nee,
        "valid_fraction": valid_days / expected_days,
    }
)
eligible_annual = annual_summary.loc[annual_summary["valid_fraction"] >= 0.90]
mean_annual_nee = eligible_annual.groupby(level="site")["annual_nee"].mean().dropna()
if mean_annual_nee.empty:
    raise ValueError("No site has an annual NEE total with at least 90% daily coverage.")
uptake_site = mean_annual_nee.idxmin()
uptake_value = mean_annual_nee.loc[uptake_site]
uptake_year_count = eligible_annual.xs(uptake_site, level="site").shape[0]

monthly_nee = (
    daily_flux.dropna(subset=["NEE_VUT_REF"])
    .assign(month=lambda data: data["day"].dt.month)
    .groupby(["site", "month"])["NEE_VUT_REF"]
    .mean()
    .unstack()
    .reindex(columns=range(1, 13))
)
monthly_nee = monthly_nee.dropna(thresh=12)
seasonal_range = (monthly_nee.max(axis=1) - monthly_nee.min(axis=1)).dropna()
if seasonal_range.empty:
    raise ValueError("No site has enough monthly NEE data to compare seasonality.")
seasonal_site = seasonal_range.idxmax()
seasonal_value = seasonal_range.loc[seasonal_site]

qc_statistics = {}
for zip_file, site_id in zip(zip_files, site_ids):
    with zipfile.ZipFile(zip_file) as archive:
        hh_files = [
            name for name in archive.namelist()
            if "FLUXMET_HH" in Path(name).name
        ]
        if len(hh_files) != 1:
            raise ValueError(
                f"Expected one FLUXMET_HH CSV in {zip_file.name}, found {len(hh_files)}."
            )
        with archive.open(hh_files[0]) as csv_file:
            quality = pd.read_csv(
                csv_file,
                na_values=[-9999],
                usecols=lambda column: column in {
                    "TIMESTAMP_START",
                    "NEE_VUT_REF_QC",
                },
            )
    if "NEE_VUT_REF_QC" in quality:
        codes = quality["NEE_VUT_REF_QC"].dropna()
        if not codes.empty:
            qc_statistics[site_id] = {
                "measured": codes.eq(0).mean(),
                "gapfilled": codes.gt(0).mean(),
            }
if not qc_statistics:
    raise ValueError("No NEE quality flags are available for the gap-fill comparison.")

gapfilled_shares = pd.Series(
    {site: values["gapfilled"] for site, values in qc_statistics.items()}
)
measured_shares = pd.Series(
    {site: values["measured"] for site, values in qc_statistics.items()}
)
least_gapfilled_site, most_gapfilled_site = (
    gapfilled_shares.idxmin(),
    gapfilled_shares.idxmax(),
)
highest_measured_site, lowest_measured_site = (
    measured_shares.idxmax(),
    measured_shares.idxmin(),
)

no_flux_sites = [
    site_id
    for site_id in site_ids
    if not (
        daily_flux.loc[daily_flux["site"] == site_id, flux_variables]
        .notna()
        .any()
        .any()
    )
]
if no_flux_sites:
    limited_site = no_flux_sites[0]
    limited_metadata = site_table.loc[site_table["site_id"] == limited_site].iloc[0]
    surprising_sentence = (
        f"A surprising data limitation is that {limited_site} "
        f"({int(limited_metadata['first_year'])}–{int(limited_metadata['last_year'])}) "
        "has no usable values for the plotted NEE, GPP, or RECO series."
    )
else:
    surprising_sentence = (
        f"A notable contrast is that the strongest annual sink, {uptake_site}, "
        f"differs from the site with the largest seasonal NEE range, {seasonal_site}."
    )

comparison_sentences = [
    f"Using negative annual NEE as net uptake and years with at least 90% valid daily values, "
    f"{uptake_site} had the largest mean annual sink at {uptake_value:.1f} g C m⁻² yr⁻¹ "
    f"across {uptake_year_count} years.",
    f"I defined seasonal-cycle size as the range of the 12 calendar-month mean daily NEE values; "
    f"{seasonal_site} had the largest range at {seasonal_value:.1f} g C m⁻² d⁻¹.",
    surprising_sentence,
    f"Among non-missing NEE QC flags, the gap-filled fraction (QC > 0) ranged from "
    f"{gapfilled_shares[least_gapfilled_site]:.1%} at {least_gapfilled_site} to "
    f"{gapfilled_shares[most_gapfilled_site]:.1%} at {most_gapfilled_site}.",
    f"Among non-missing QC flags, the measured fraction (QC = 0) was highest at {highest_measured_site} "
    f"({measured_shares[highest_measured_site]:.1%}) and lowest at {lowest_measured_site} "
    f"({measured_shares[lowest_measured_site]:.1%}) among sites with QC data.",
    "The annual sink comparison uses NEE_VUT_REF, while gap-filled percentages exclude intervals with missing QC flags.",
]
display_markdown(" ".join(comparison_sentences), markdown_c6_parts)

(script_dir / "c6.md").write_text(
    "\n\n".join(markdown_c6_parts),
    encoding="utf-8",
)

citation_lines = [
    f"- **{row['site_id']}**: {row['product_citation']}"
    for _, row in site_table.sort_values("site_id").iterrows()
]
display(Markdown(f"Snapshot: `{snapshot_file.name}`.\n\n" + "\n".join(citation_lines)))
(script_dir / "c6_citations.md").write_text(
    "\n\n".join(citation_lines),
    encoding="utf-8",
)