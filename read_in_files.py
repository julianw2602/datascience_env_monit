import re
import warnings
import zipfile
from pathlib import Path

import pandas as pd


KEEP_COLUMNS = [
    "TIMESTAMP_START", "TIMESTAMP_END", "TA_F", "SW_IN_F", "VPD_F", "P_F",
    "NETRAD", "G_F_MDS", "H_F_MDS", "H_F_MDS_QC", "LE_F_MDS", "LE_F_MDS_QC",
    "NEE_VUT_REF", "NEE_VUT_REF_QC", "GPP_NT_VUT_REF", "RECO_NT_VUT_REF",
]
HH_FILENAME_PATTERN = re.compile(
    r"^[^_]+_([^_]+)_FLUXNET_FLUXMET_HH_"
)


def read_hh(zip_file):
    """Read the selected half-hourly FLUXMET variables from one tower archive."""
    zip_file = Path(zip_file)
    with zipfile.ZipFile(zip_file) as archive:
        hh_names = [
            name for name in archive.namelist()
            if "FLUXMET_HH" in Path(name).name
        ]
        if len(hh_names) != 1:
            raise ValueError(
                f"Expected exactly one FLUXMET_HH CSV in {zip_file}, "
                f"found {len(hh_names)}."
            )

        hh_name = hh_names[0]
        match = HH_FILENAME_PATTERN.match(Path(hh_name).name)
        if match is None:
            raise ValueError(f"Could not extract a site ID from {hh_name!r}.")
        site = match.group(1)

        with archive.open(hh_name) as csv_file:
            hh = pd.read_csv(
                csv_file,
                na_values=[-9999],
                usecols=lambda column: column in KEEP_COLUMNS,
                dtype={"TIMESTAMP_START": str, "TIMESTAMP_END": str},
            )

    missing_columns = [column for column in KEEP_COLUMNS if column not in hh]
    required_timestamps = {"TIMESTAMP_START", "TIMESTAMP_END"}
    missing_timestamps = required_timestamps.intersection(missing_columns)
    if missing_timestamps:
        raise ValueError(
            f"{hh_name} is missing required timestamp columns: "
            f"{', '.join(sorted(missing_timestamps))}."
        )
    if missing_columns:
        warnings.warn(
            f"{hh_name} is missing requested columns; returning them as "
            f"missing values: {', '.join(missing_columns)}.",
            UserWarning,
            stacklevel=2,
        )

    hh = hh.reindex(columns=KEEP_COLUMNS)
    hh["time"] = pd.to_datetime(
        hh["TIMESTAMP_START"], format="%Y%m%d%H%M", errors="raise"
    )
    end_time = pd.to_datetime(
        hh["TIMESTAMP_END"], format="%Y%m%d%H%M", errors="raise"
    )

    if hh["time"].isna().any() or end_time.isna().any():
        raise ValueError(f"{hh_name} contains missing timestamps.")
    if hh["time"].duplicated().any():
        raise ValueError(f"{hh_name} contains duplicated start timestamps.")
    if not (end_time - hh["time"]).eq(pd.Timedelta(minutes=30)).all():
        raise ValueError(f"{hh_name} contains records that are not 30 minutes.")

    hh.insert(0, "site", site)
    return hh


def measured_nee_share(qc):
    return float(qc.eq(0).mean()) if qc.notna().any() else float("nan")


def read_all_hh(zip_files=None):
    if zip_files is None:
        zip_files = sorted(Path("data/raw").glob("*.zip"))
    if len(zip_files) != 5:
        raise FileNotFoundError(
            f"Expected five tower ZIP files, found {len(zip_files)}."
        )
    return pd.concat(
        (read_hh(zip_file) for zip_file in zip_files), ignore_index=True
    )


def main():
    hh_all = read_all_hh()
    print(f"Read {len(hh_all):,} half-hourly rows from {hh_all['site'].nunique()} sites.")
    print("\nRows per site and year:")
    yearly_rows = (
        hh_all.assign(year=hh_all["time"].dt.year)
        .groupby(["site", "year"])
        .size()
        .rename("rows")
    )
    print(yearly_rows.to_string())

    print("\nTime range and share of measured NEE by site:")
    site_summary = hh_all.groupby("site").agg(
        first_time=("time", "min"),
        last_time=("time", "max"),
        measured_nee_share=("NEE_VUT_REF_QC", measured_nee_share),
    )
    print(site_summary.to_string())
    print("\nAir temperature summary by site (°C):")
    print(hh_all.groupby("site")["TA_F"].describe().to_string())


if __name__ == "__main__":
    main()
