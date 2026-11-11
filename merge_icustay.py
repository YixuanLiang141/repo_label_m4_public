import pandas as pd

def merge_time_intervals(input_csv, output_csv):
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

if __name__ == "__main__":
    merge_time_intervals('../../icu/icustays.csv', 'icustays_merged.csv')