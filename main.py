# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "matplotlib",
#     "pandas",
#     "seaborn",
#     "tqdm",
# ]
# ///

import argparse
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from tqdm import trange


def eligible_workshops(s_id, student, w_df, s_id_to_w_id):
    """Find eligible workshops for a given student according to these rules:

    - Students can only attend workshops offered in the languages they speak.
    - Students from Lampedusa can only attend workshops marked as doable from Lampedusa.
    - Students cannot attend workshops organized by their own school.
    - Students cannot attend multiple workshops with the same name but different slots.
    - Students cannot attend workshops that are scheduled in the same slot.
    """

    ew_df = w_df  # ew_df = eligible workshops DataFrame

    # 1. language
    cond = ew_df["languages"].apply(lambda langs: len(student["languages"] & langs) > 0)
    ew_df = ew_df[cond]

    # 1. from_lampedusa (or other attribute)
    if student["from_lampedusa"]:
        ew_df = ew_df[ew_df["doable_from_lampedusa"]]

    # 2. organizer != School
    ew_df = ew_df[ew_df["organizer"] != student["school"]]

    # 4. avoid same workshops with different slots
    prev_w_ids = list(s_id_to_w_id[s_id])
    prev_w_names = ew_df["name"].loc[prev_w_ids]
    ew_df = ew_df[~ew_df["name"].isin(prev_w_names)]

    # 5. avoid simultaneous workshops
    prev_w_ids = list(set(ew_df.index) & s_id_to_w_id[s_id])
    not_allow_slots = ew_df["slot"].loc[prev_w_ids]
    ew_df = ew_df[~ew_df["slot"].isin(not_allow_slots)]

    # 6. Sort ew_df by priority:
    #   - first the workshops with fix number of participants in "count" ascending order
    #   - then workshops with variable number of participants in "count" ascending order
    _df_fix = ew_df[ew_df["participants"] > 0]
    _df_fix = _df_fix[_df_fix["participants"] - _df_fix["count"] > 0]  # not full
    _df_fix = _df_fix.sort_values(by="count", ascending=True)
    _df_var = ew_df[ew_df["participants"] == 0]
    _df_var = _df_var.sort_values(by="count", ascending=True)
    ew_df = pd.concat([_df_fix, _df_var])

    return ew_df


def map_workshops(s_df, w_df, s_id_to_w_id):
    # Get the eligible workshops for each student
    s_id_to_ew_df = {
        s_id: eligible_workshops(s_id, student, w_df, s_id_to_w_id)
        for s_id, student in s_df.iterrows()
    }

    # Sort dict by len of eligible_workshops. We want to assign the workshops
    # to the people with the least amount of eligible workshops.
    # s_id_to_ew_df = dict(sorted(s_id_to_ew_df.items(), key=lambda item: len(item[1])))
    # NOTE: This is not required but it seems reasonable.
    # It does not make sense to sort again after df shuffing (sample(frac=1))

    for s_id in s_id_to_ew_df:
        student = s_df.loc[s_id]
        ew_df = eligible_workshops(s_id, student, w_df, s_id_to_w_id)

        if ew_df.empty:
            continue  # no eligible workshops found for student

        w_id = int(ew_df.index[0])
        s_id_to_w_id[s_id].add(w_id)  # assign first eligible workshop to student
        w_df.loc[w_id, "count"] += 1  # increment count for workshop (for balancing)

    return s_id_to_w_id


def save_mapping(s_id_to_w_id, path):
    num_w_max = max([len(w_ids) for w_ids in s_id_to_w_id.values()])
    data = []
    for s_id, w_ids in s_id_to_w_id.items():
        w_ids = list(w_ids)
        w_ids.extend([None] * (num_w_max - len(w_ids)))
        data.append(
            {
                "student_id": s_id,
                **{f"workshop_id_{i}": w_id for i, w_id in enumerate(w_ids, 1)},
            }
        )
    pd.DataFrame(data, dtype="Int64").to_csv(path, index=False)


def mapping_score(s_id_to_w_id):
    # NOTE: adjust this metric to your needs
    num_w_to_num_s = Counter([len(w_ids) for w_ids in s_id_to_w_id.values()])
    return sum(num_w * num_s for num_w, num_s in num_w_to_num_s.items())


def plot(s_id_to_w_id, w_df):
    w_df.set_index("workshop_id", inplace=True)
    plt.style.use("seaborn-v0_8")
    plt.figure(figsize=(6, 4))
    all_workshops = [w_id for workshops in s_id_to_w_id.values() for w_id in workshops]
    workshop_counts = pd.Series(all_workshops).value_counts().sort_index()

    x_labels = [
        (
            f"{w_df.loc[w_id]['name']}\n"
            f"Slot {w_df.loc[w_id]['slot']}\n"
            f"Target: {w_df.loc[w_id]['participants']}"
        )
        for w_id in workshop_counts.index
    ]

    bars = plt.bar(
        range(len(workshop_counts)),
        workshop_counts.values,
        color="skyblue",
        edgecolor="navy",
        alpha=0.7,
    )

    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{int(height)}",
            ha="center",
            va="bottom",
        )

    plt.xticks(range(len(x_labels)), labels=x_labels, rotation=45, ha="right")
    plt.xlabel("Workshops", fontsize=12, labelpad=10)
    plt.ylabel("Number of Participants", fontsize=12, labelpad=10)
    plt.title("Workshop Participation Distribution", fontsize=14, pad=20)

    plt.grid(True, axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.show()


def print_stats(s_id_to_w_id):
    num_w_to_num_s = Counter([len(w_ids) for w_ids in s_id_to_w_id.values()])
    num_w_to_num_s = dict(sorted(num_w_to_num_s.items()))
    print("There are:")
    for num_w, num_s in num_w_to_num_s.items():
        print(f" - {num_s} students map to {num_w} workshops")


def main(s_df, w_df):
    # Preprocess DataFrames
    s_df.set_index("student_id", inplace=True)
    w_df.set_index("workshop_id", inplace=True)
    s_df["languages"] = s_df["languages"].apply(lambda langs: set(langs.split(",")))
    w_df["languages"] = w_df["languages"].apply(lambda langs: set(langs.split(",")))
    w_df["participants"] = w_df["participants"].fillna(0).astype(int)
    w_df["count"] = 0

    # Handle carriage returns and convert boolean columns
    s_df["from_lampedusa"] = s_df["from_lampedusa"].astype(str).str.strip().str.upper() == "TRUE"
    w_df["doable_from_lampedusa"] = w_df["doable_from_lampedusa"].astype(str).str.strip().str.upper() == "TRUE"

    # Initialize data structure for storing results
    s_id_to_w_id: [int, set[int]] = {s_id: set() for s_id in s_df.index}

    # Map 3 workshops for each student
    s_id_to_w_id = map_workshops(s_df, w_df, s_id_to_w_id)
    s_id_to_w_id = map_workshops(s_df, w_df, s_id_to_w_id)
    s_id_to_w_id = map_workshops(s_df, w_df, s_id_to_w_id)

    return s_id_to_w_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Assign workshops to students based on eligibility rules."
    )
    parser.add_argument(
        "--students-path",
        type=Path,
        default="data/students.csv",
        help="path to students.csv",
    )
    parser.add_argument(
        "--workshops-path",
        type=Path,
        default="data/workshops.csv",
        help="path to workshops.csv",
    )
    parser.add_argument(
        "--mapping-path",
        type=Path,
        default="data/mapping.csv",
        help="path where save mapping.csv",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="plot the number of participants per workshop",
    )
    parser.add_argument(
        "--runs",
        default=10,
        type=int,
        help="number of runs for best mapping",
    )
    args = parser.parse_args()

    # Load CSV files as DataFrames
    S_DF = pd.read_csv(args.students_path)
    W_DF = pd.read_csv(args.workshops_path)

    # Assert uniqueness of IDs
    assert S_DF["student_id"].is_unique, f"Duplicate student_id found in {args.students_path}"
    assert W_DF["workshop_id"].is_unique, f"Duplicate workshop_id found in {args.workshops_path}"

    mapping = {}
    best_mapping_score = 0

    for i in trange(args.runs):
        s_df = S_DF.sample(frac=1, random_state=i)
        w_df = W_DF.sample(frac=1, random_state=i)
        s_id_to_w_id = main(s_df, w_df)

        score = mapping_score(s_id_to_w_id)
        if score > best_mapping_score:
            mapping = s_id_to_w_id
            best_mapping_score = score

    save_mapping(mapping, args.mapping_path)

    print_stats(s_id_to_w_id)

    if args.plot:
        plot(mapping, W_DF)
