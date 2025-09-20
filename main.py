# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "matplotlib",
#     "pandas",
# ]
# ///

from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt

# Load CSV files as DataFrames
S_DF = pd.read_csv("data/students.csv", index_col="student_id")
W_DF = pd.read_csv("data/workshops.csv", index_col="workshop_id")


# split the W_DF into 3 dataframes based on slot
W_DF_2 = W_DF[W_DF["slot"] == 2]
W_DF_3 = W_DF[W_DF["slot"] == 3]


w_id_to_s_id: dict[int, list[int]] = defaultdict(list)
s_id_to_w_id: dict[int, list[int]] = defaultdict(list)


def eligible_workshops(s_id, slot):
    """Find eligible workshops for a given student according to these rules:

    - Students can only attend workshops offered in the languages they speak.
    - Students from Lampedusa can only attend workshops marked as doable from Lampedusa.
    - Students cannot attend workshops organized by their own school.
    """

    workshops = W_DF[W_DF["slot"] == slot]
    student = S_DF.loc[s_id]

    # 1. language
    s_langs = set(student["languages"].split(","))
    cond = workshops["languages"].apply(
        lambda langs: len(s_langs & set(langs.split(","))) > 0
    )
    workshops = workshops[cond]

    # 2. from_lampedusa (or other attribute)
    if student["from_lampedusa"]:
        workshops = workshops[workshops["doable_from_lampedusa"]]

    # 3. organizer != School
    workshops = workshops[workshops["organizer"] != student["school"]]

    # 4. avoid same workshops with different slots
    prev_w_names = W_DF["name"].loc[s_id_to_w_id[s_id]]
    workshops = workshops[~workshops["name"].isin(prev_w_names)]

    assert isinstance(workshops, pd.DataFrame)
    return workshops


def map_students_to_workshops(slot):
    print(f"Number of Workshops (slot {slot}):", len(W_DF[W_DF["slot"] == slot]))
    unassigned_students = []

    for s_id, _ in S_DF.iterrows():
        e_workshops = eligible_workshops(s_id, slot).index.to_list()
        e_workshops = sorted(
            e_workshops,
            key=lambda w_id: len(w_id_to_s_id.get(w_id, [])),
            reverse=False,  # Changed to False for better distribution
        )

        selected_workshop = None
        for workshop in e_workshops:
            participants = W_DF.loc[workshop, "participants"]
            limit = 1_000 if pd.isna(participants) else int(participants)
            if len(w_id_to_s_id[workshop]) < limit:
                selected_workshop = workshop
                break

        if selected_workshop is not None:
            w_id_to_s_id[selected_workshop].append(s_id)
            s_id_to_w_id[s_id].append(selected_workshop)
        else:
            unassigned_students.append(s_id)

    if unassigned_students:
        print(
            f"Warning: {len(unassigned_students)} students could not be assigned to any workshop in slot {slot}"
        )
        print(f"Unassigned student IDs: {unassigned_students}")


def export_mapping_to_csv():
    """Export the student-workshop mappings to data/mapping.csv."""
    print("Exporting mappings to data/mapping.csv...")

    # Create list of rows for the CSV
    mapping_rows = []

    for student_id in S_DF.index:
        workshops = s_id_to_w_id.get(student_id, [])

        # Ensure we have exactly 3 workshops (pad with None if needed)
        while len(workshops) < 3:
            workshops.append(None)

        mapping_rows.append(
            {
                "student_id": student_id,
                "workshop_id_1": workshops[0] if workshops[0] is not None else "",
                "workshop_id_2": workshops[1] if workshops[1] is not None else "",
                "workshop_id_3": workshops[2] if workshops[2] is not None else "",
            }
        )

    # Create DataFrame and save to CSV
    mapping_df = pd.DataFrame(mapping_rows)
    mapping_df.to_csv("data/mapping.csv", index=False)
    print(f"Exported {len(mapping_rows)} student mappings to data/mapping.csv")


def plot_workshop_distribution(slot):
    workshops = W_DF[W_DF["slot"] == slot]
    workshop_names = []
    student_counts = []

    for w_id in workshops.index:
        student_counts.append(len(w_id_to_s_id.get(w_id, [])))

        workshop_name = W_DF.loc[w_id, "name"]
        if len(workshop_name) > 30:
            workshop_name = workshop_name[:30] + "..."
        if not pd.isna(W_DF.loc[w_id, "participants"]):
            workshop_name += f" (max {int(W_DF.loc[w_id, 'participants'])})"

        workshop_names.append(workshop_name + f" ({w_id})")

    plt.figure(figsize=(10, 8))
    plt.barh(workshop_names, student_counts)

    plt.xlabel("Number of Students")
    plt.ylabel("Workshop")
    plt.title(f"Distribution (Slot {slot})")

    plt.tight_layout()
    plt.savefig(f"workshop_distribution_slot_{slot}.png", dpi=300, bbox_inches="tight")


def main():
    map_students_to_workshops(1)
    map_students_to_workshops(2)
    map_students_to_workshops(3)

    # Export all mappings to CSV
    export_mapping_to_csv()

    # Generate distribution plots
    plot_workshop_distribution(1)
    plot_workshop_distribution(2)
    plot_workshop_distribution(3)


if __name__ == "__main__":
    main()
