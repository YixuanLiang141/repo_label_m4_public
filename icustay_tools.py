import pandas as pd

def merge_time_intervals(input_csv, output_csv):
    # Merge overlapped or continuous ICU stays (though not many)
    
    df = pd.read_csv(
        input_csv,
        usecols=['subject_id', 'intime', 'outtime'],
        parse_dates=['intime', 'outtime']
    )

    df = df.dropna(subset=['subject_id', 'intime', 'outtime'])

    df = df.sort_values(
        ['subject_id', 'intime', 'outtime']
    ).reset_index(drop=True)

    max_outtime = df.groupby('subject_id')['outtime'].cummax()

    prev_max_outtime = max_outtime.groupby(
        df['subject_id']
    ).shift()

    new_group = (
        df['subject_id'].ne(df['subject_id'].shift())
        | (df['intime'] > prev_max_outtime)
    )

    df['_group'] = new_group.cumsum()

    df = df.groupby('_group', sort=False).agg(
        subject_id=('subject_id', 'first'),
        intime=('intime', 'min'),
        outtime=('outtime', 'max')
    ).reset_index(drop=True)

    df.to_csv(output_csv, index=False)

    return df

def expand_icu_hours(input_path, output_path, ignore_short_stays):
    """Expand ICU stays into hourly start timestamps and hour numbers."""

    df = pd.read_csv(
        input_path,
        usecols=["subject_id", "intime", "outtime"],
        dtype={"subject_id": "string"},
    )

    df["intime"] = pd.to_datetime(df["intime"], errors="raise")
    df["outtime"] = pd.to_datetime(df["outtime"], errors="raise")

    if df.isna().any().any():
        raise ValueError("Required fields must not contain missing values.")
    if df["outtime"].lt(df["intime"]).any():
        raise ValueError("outtime must not precede intime.")

    # Filter by actual duration before rounding to full hours.
    if ignore_short_stays:
        duration = df["outtime"] - df["intime"]
        df = df.loc[duration.ge(pd.Timedelta(hours=6))].copy()

    df = df.sort_values(
        ["subject_id", "intime", "outtime"], kind="stable"
    ).reset_index(drop=True)

    # Assign a separate identifier to each input stay.
    df["_stay_id"] = range(len(df))

    # Generate the start timestamp of each full-hour interval.
    df["charttime"] = [
        pd.date_range(
            start=start.floor("h"),
            end=end.ceil("h"),
            freq="h",
            inclusive="left",
        )
        for start, end in zip(df["intime"], df["outtime"])
    ]

    result = (
        df[["subject_id", "_stay_id", "charttime"]]
        .explode("charttime")
        .dropna(subset=["charttime"])
        .reset_index(drop=True)
    )

    # Restart numbering from 1 for each ICU stay.
    result["hour"] = result.groupby("_stay_id", sort=False).cumcount() + 1
    result = result[["subject_id", "charttime", "hour"]]

    result.to_csv(output_path, index=False)

    return result

if __name__ == "__main__":
    merge_time_intervals('../../icu/icustays.csv', 'icustays_merged.csv')
    # Only for urine output
    expand_icu_hours("icustays_merged.csv", "hourly_urine.csv", ignore_short_stays = 1)