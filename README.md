# Students to Workshops

A friend of mine has to organize an event for students with multiple workshops. There are a lot of students, a lot of workshops, and some restrictions: here is a dead simple script for an automated mapping solution.

In the best case scenario, the restrictions are so loose that we can successfully map all students to a fixed amount of workshops per student.
However, if the restrictions are too strict, we cannot guarantee the same amount of workshops for each student. In this scenario, a metric for the quality of a mapping is introduced; the higher the score, the more students are mapped to various workshops.

The problem gets harder because one step of the mapping process depends on the previous ones (e.g., a workshop has a max number of participants). Moreover, the order of mapping steps can influence mapping quality. The script implemented a pragmatic approach: search for the best mapping over different shuffling of the input data, reporting the one with a higher mapping score.

### Install & Usage

1. Install [uv](https://docs.astral.sh/uv/) for running the script

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Run the script

```bash
uv run https://raw.githubusercontent.com/S1M0N38/students-to-workshops/main/main.py \
  --students-path path/to/students.csv \
  --workshops-path path/to/workshops.csv \
  --mapping-path path/to/mapping.csv
```

Add  `--help` to the last command to see the available options.

______________________________________________________________________

## Tables

The following are dummy data, but the table structure is the same as the real one.

### Students Table

| **student_id** | name    | surname | school      | languages | from_lampedusa |
| :------------: | ------- | ------- | ----------- | --------- | -------------- |
|       1        | John    | Doe     | Science     | it,en,fr  | False          |
|       2        | Alice   | Smith   | Arts        | es        | False          |
|       3        | Roberto | Rossi   | Engineering | it        | True           |
|       4        | Marie   | Dubois  | Science     | fr,en     | False          |
|       5        | Li      | Zhang   | Mathematics | zh,en     | False          |
|       6        | Ahmed   | Khan    | Science     | ar,en     | True           |
|      ...       | ...     | ...     | ...         | ...       | ...            |

### Workshops Table

| **workshop_id** | name              | slot | participants | organizer   | languages | doable_from_lampedusa |
| --------------- | ----------------- | ---: | -----------: | ----------- | --------- | --------------------: |
| 1               | Hackathon         |    1 |           10 | Science     | it,en     |                 False |
| 2               | Hackathon         |    2 |           10 | Science     | it,zh     |                 False |
| 3               | Hackathon         |    3 |           10 | Science     | it,en     |                  True |
| 4               | Art Therapy       |    1 |            - | Arts        | en,es     |                  True |
| 5               | Art Therapy       |    2 |            - | Arts        | en        |                  True |
| 6               | Robotics Workshop |    1 |            - | Engineering | en,it     |                  True |
| 7               | Robotics Workshop |    2 |            - | Engineering | en,it     |                  True |
| 8               | Robotics Workshop |    3 |            - | Engineering | en,zh     |                  True |

### Example Output Table

| **student_id** | workshop_id_1 | workshop_id_2 | workshop_id_3 |
| :------------: | :-----------: | :-----------: | :-----------: |
|       1        |       1       |       5       |       8       |
|       2        |       -       |       -       |       -       |
|       3        |       3       |       6       |       -       |
|      ...       |      ...      |      ...      |      ...      |

## Rules

We need to assign each student to a **maximum of 3** different workshops.

### Workshop Eligibility

- Students can only attend workshops offered in the languages they speak.
- Students from Lampedusa can only attend workshops marked as doable from Lampedusa.
- Students cannot attend workshops organized by their own school.
- Students cannot attend multiple workshops with the same name but different slots.
- Students cannot attend workshops that are scheduled in the same slot.

### Workshop Mapping

- Try to fill the workshop with the exact and required amount of participants (values in `participants` column > 0).
- Try to assign workshops to students that have the lower amount of eligible workshops.
- Try to balance the number of participants across workshops.
