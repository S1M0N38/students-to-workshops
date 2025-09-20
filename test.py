# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pandas",
# ]
# ///

"""
Test suite for validating workshop mapping constraints.
Validates that data/mapping.csv respects all assignment rules.
"""

import argparse
from collections import defaultdict

import pandas as pd


def load_data(students_path, workshops_path, mapping_path):
    """Load all required CSV files."""
    print("Loading data files...")

    students_df = pd.read_csv(students_path, index_col="student_id")
    workshops_df = pd.read_csv(workshops_path, index_col="workshop_id")
    mapping_df = pd.read_csv(mapping_path)

    print(
        f"Loaded {len(students_df)} students, {len(workshops_df)} workshops, {len(mapping_df)} mappings"
    )
    return students_df, workshops_df, mapping_df


def parse_assignments(mapping_df):
    """Parse mapping.csv into student-workshop assignments."""
    assignments = []

    for _, row in mapping_df.iterrows():
        student_id = row["student_id"]
        for slot in [1, 2, 3]:
            workshop_id = row[f"workshop_id_{slot}"]
            assignments.append(
                {"student_id": student_id, "workshop_id": workshop_id, "slot": slot}
            )

    return assignments


def get_workshop_student_counts(assignments):
    """Count how many students are assigned to each workshop."""
    workshop_counts = defaultdict(int)

    for assignment in assignments:
        workshop_counts[assignment["workshop_id"]] += 1

    return workshop_counts


def test_language_constraint(assignments, students_df, workshops_df):
    """Test that students only attend workshops in languages they speak."""
    print("Testing language constraint...")
    violations = []

    for assignment in assignments:
        student_id = assignment["student_id"]
        workshop_id = assignment["workshop_id"]

        student = students_df.loc[student_id]
        workshop = workshops_df.loc[workshop_id]

        student_languages = set(student["languages"].split(","))
        workshop_languages = set(workshop["languages"].split(","))

        # Check if student and workshop share at least one language
        if len(student_languages & workshop_languages) == 0:
            violations.append(
                {
                    "student_id": student_id,
                    "workshop_id": workshop_id,
                    "student_languages": student_languages,
                    "workshop_languages": workshop_languages,
                }
            )

    if violations:
        print(f"FAILED: {len(violations)} language constraint violations found:")
        for v in violations[:5]:  # Show first 5 violations
            print(
                f"  Student {v['student_id']} speaks {v['student_languages']} but assigned to workshop {v['workshop_id']} requiring {v['workshop_languages']}"
            )
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more violations")
        assert False, f"Language constraint violated for {len(violations)} assignments"
    else:
        print("PASSED: All students assigned to workshops in compatible languages")


def test_lampedusa_constraint(assignments, students_df, workshops_df):
    """Test that students from Lampedusa only attend workshops doable from Lampedusa."""
    print("Testing Lampedusa constraint...")
    violations = []

    for assignment in assignments:
        student_id = assignment["student_id"]
        workshop_id = assignment["workshop_id"]

        student = students_df.loc[student_id]
        workshop = workshops_df.loc[workshop_id]

        # Check if student is from Lampedusa but workshop is not doable from Lampedusa
        if student["from_lampedusa"] and not workshop["doable_from_lampedusa"]:
            violations.append(
                {
                    "student_id": student_id,
                    "workshop_id": workshop_id,
                    "workshop_name": workshop["name"],
                }
            )

    if violations:
        print(f"FAILED: {len(violations)} Lampedusa constraint violations found:")
        for v in violations[:5]:  # Show first 5 violations
            print(
                f"  Student {v['student_id']} from Lampedusa assigned to workshop {v['workshop_id']} ({v['workshop_name']}) not doable from Lampedusa"
            )
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more violations")
        assert False, f"Lampedusa constraint violated for {len(violations)} assignments"
    else:
        print(
            "PASSED: All Lampedusa students assigned to workshops doable from Lampedusa"
        )


def test_school_constraint(assignments, students_df, workshops_df):
    """Test that students cannot attend workshops organized by their own school."""
    print("Testing school constraint...")
    violations = []

    for assignment in assignments:
        student_id = assignment["student_id"]
        workshop_id = assignment["workshop_id"]

        student = students_df.loc[student_id]
        workshop = workshops_df.loc[workshop_id]

        # Check if student's school is the same as workshop organizer
        if student["school"] == workshop["organizer"]:
            violations.append(
                {
                    "student_id": student_id,
                    "workshop_id": workshop_id,
                    "school": student["school"],
                    "workshop_name": workshop["name"],
                }
            )

    if violations:
        print(f"FAILED: {len(violations)} school constraint violations found:")
        for v in violations[:5]:  # Show first 5 violations
            print(
                f"  Student {v['student_id']} from {v['school']} assigned to workshop {v['workshop_id']} ({v['workshop_name']}) organized by their own school"
            )
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more violations")
        assert False, f"School constraint violated for {len(violations)} assignments"
    else:
        print("PASSED: No students assigned to workshops organized by their own school")


def test_duplicate_workshop_constraint(assignments, workshops_df):
    """Test that students don't attend the same workshop (by name) in different slots."""
    print("Testing duplicate workshop constraint...")
    violations = []

    # Group assignments by student
    student_assignments = defaultdict(list)
    for assignment in assignments:
        student_assignments[assignment["student_id"]].append(assignment)

    for student_id, student_workshops in student_assignments.items():
        workshop_names = []

        for assignment in student_workshops:
            workshop_id = assignment["workshop_id"]
            workshop_name = workshops_df.loc[workshop_id, "name"]
            workshop_names.append((workshop_name, assignment["slot"], workshop_id))

        # Check for duplicate workshop names
        name_counts = defaultdict(list)
        for name, slot, w_id in workshop_names:
            name_counts[name].append((slot, w_id))

        for workshop_name, slots_and_ids in name_counts.items():
            if len(slots_and_ids) > 1:
                violations.append(
                    {
                        "student_id": student_id,
                        "workshop_name": workshop_name,
                        "slots_and_ids": slots_and_ids,
                    }
                )

    if violations:
        print(
            f"FAILED: {len(violations)} duplicate workshop constraint violations found:"
        )
        for v in violations[:5]:  # Show first 5 violations
            slots_info = ", ".join(
                [f"slot {slot} (workshop {w_id})" for slot, w_id in v["slots_and_ids"]]
            )
            print(
                f"  Student {v['student_id']} assigned to '{v['workshop_name']}' multiple times: {slots_info}"
            )
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more violations")
        assert False, (
            f"Duplicate workshop constraint violated for {len(violations)} students"
        )
    else:
        print("PASSED: No students assigned to the same workshop multiple times")


def test_participant_limits(workshop_counts, workshops_df):
    """Test that workshops with defined participant limits are not exceeded."""
    print("Testing participant limits...")
    violations = []

    for workshop_id, actual_count in workshop_counts.items():
        workshop = workshops_df.loc[workshop_id]
        limit = workshop["participants"]

        # Check if workshop has a defined limit and it's exceeded
        if not pd.isna(limit):
            limit = int(limit)
            if actual_count > limit:
                violations.append(
                    {
                        "workshop_id": workshop_id,
                        "workshop_name": workshop["name"],
                        "limit": limit,
                        "actual_count": actual_count,
                    }
                )

    if violations:
        print(f"FAILED: {len(violations)} participant limit violations found:")
        for v in violations[:5]:  # Show first 5 violations
            print(
                f"  Workshop {v['workshop_id']} ({v['workshop_name']}) has {v['actual_count']} students but limit is {v['limit']}"
            )
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more violations")
        assert False, f"Participant limits violated for {len(violations)} workshops"
    else:
        print("PASSED: All workshops respect their participant limits")


def test_all_workshops_have_students(workshop_counts, workshops_df):
    """Test that all workshops have at least one student assigned."""
    print("Testing workshop coverage...")
    workshops_without_students = []

    for workshop_id in workshops_df.index:
        if workshop_counts.get(workshop_id, 0) == 0:
            workshop = workshops_df.loc[workshop_id]
            workshops_without_students.append(
                {
                    "workshop_id": workshop_id,
                    "workshop_name": workshop["name"],
                    "slot": workshop["slot"],
                }
            )

    if workshops_without_students:
        print(
            f"FAILED: {len(workshops_without_students)} workshops have no students assigned:"
        )
        for w in workshops_without_students[:10]:  # Show first 10
            print(
                f"  Workshop {w['workshop_id']} ({w['workshop_name']}) in slot {w['slot']}"
            )
        if len(workshops_without_students) > 10:
            print(f"  ... and {len(workshops_without_students) - 10} more workshops")
        assert False, (
            f"{len(workshops_without_students)} workshops have no students assigned"
        )
    else:
        print("PASSED: All workshops have at least one student assigned")


def test_all_students_have_three_workshops(assignments, students_df):
    """Test that all students have exactly 3 workshop assignments."""
    print("Testing student coverage...")
    student_assignments = defaultdict(int)

    for assignment in assignments:
        student_assignments[assignment["student_id"]] += 1

    violations = []
    for student_id in students_df.index:
        count = student_assignments.get(student_id, 0)
        if count != 3:
            violations.append({"student_id": student_id, "assignment_count": count})

    if violations:
        print(f"FAILED: {len(violations)} students don't have exactly 3 workshops:")
        for v in violations[:10]:  # Show first 10
            print(
                f"  Student {v['student_id']} has {v['assignment_count']} workshops assigned"
            )
        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more students")
        assert False, (
            f"{len(violations)} students don't have exactly 3 workshops assigned"
        )
    else:
        print("PASSED: All students have exactly 3 workshops assigned")


def run_all_tests(students_path, workshops_path, mapping_path):
    """Run the complete test suite for workshop mapping validation."""
    print("=" * 60)
    print("WORKSHOP MAPPING VALIDATION TEST SUITE")
    print("=" * 60)

    try:
        # Load data
        students_df, workshops_df, mapping_df = load_data(
            students_path, workshops_path, mapping_path
        )
        assignments = parse_assignments(mapping_df)
        workshop_counts = get_workshop_student_counts(assignments)

        print("\nData summary:")
        print(f"  Students: {len(students_df)}")
        print(f"  Workshops: {len(workshops_df)}")
        print(f"  Total assignments: {len(assignments)}")
        print(f"  Workshops with students: {len(workshop_counts)}")
        print()

        # Run all constraint tests
        test_language_constraint(assignments, students_df, workshops_df)
        test_lampedusa_constraint(assignments, students_df, workshops_df)
        test_school_constraint(assignments, students_df, workshops_df)
        test_duplicate_workshop_constraint(assignments, workshops_df)
        test_participant_limits(workshop_counts, workshops_df)

        # Run coverage tests
        test_all_workshops_have_students(workshop_counts, workshops_df)
        test_all_students_have_three_workshops(assignments, students_df)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! 🎉")
        print("The workshop mapping respects all constraints.")
        print("=" * 60)

        return True

    except AssertionError as e:
        print("\n" + "=" * 60)
        print("TEST SUITE FAILED! ❌")
        print(f"Error: {e}")
        print("=" * 60)
        return False

    except Exception as e:
        print("\n" + "=" * 60)
        print("UNEXPECTED ERROR! 💥")
        print(f"Error: {e}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Test workshop mapping constraints")
    parser.add_argument(
        "--students-path",
        default="data/students.csv",
        help="Path to the students CSV file (default: data/students.csv)",
    )
    parser.add_argument(
        "--workshops-path",
        default="data/workshops.csv",
        help="Path to the workshops CSV file (default: data/workshops.csv)",
    )
    parser.add_argument(
        "--mapping-path",
        default="data/mapping.csv",
        help="Path to the mapping CSV file to test (default: data/mapping.csv)",
    )

    args = parser.parse_args()

    print(f"Testing students from: {args.students_path}")
    print(f"Testing workshops from: {args.workshops_path}")
    print(f"Testing mapping from: {args.mapping_path}")
    print()

    success = run_all_tests(args.students_path, args.workshops_path, args.mapping_path)
    exit(0 if success else 1)
