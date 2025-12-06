import sqlite3
import pandas as pd
import struct

def Stress_level_calculate(database_path):
    conn = sqlite3.connect(database_path)

    # Select data from Attendance table
    survey_query = "SELECT Student_ID, Study_Time, Entertainment_Time, Sleep_Time FROM Survey"
    survey_df = pd.read_sql_query(survey_query, conn)

    # Select data from students table
    students_query = "SELECT Student_ID, Student_Name FROM Students"
    students_df = pd.read_sql_query(students_query, conn)

    conn.close()

    # calculate stress_level
    def calculate_stress(study_time, entertainment_time, sleep_time):
        stress = (study_time * 0.3 + entertainment_time * 0.4 + sleep_time * 0.3) * 1.75 - 8
        return stress

    survey_df['stress_level'] = survey_df.apply(
        lambda row: calculate_stress(row['Study_Time'], row['Entertainment_Time'], row['Sleep_Time']), axis=1
    )

    stree_level_df = pd.merge(students_df, survey_df, on='Student_ID', how='left')

    stree_level_df = stree_level_df[
        ['Student_Name', 'Student_ID', 'stress_level', 'Study_Time', 'Entertainment_Time', 'Sleep_Time']]

    return stree_level_df


def filter_high_stress_students(database_path):
    # Get the complete stress level dataframe
    stress_level_df = Stress_level_calculate(database_path)

    # Filter students with stress_level > 3
    high_stress_df = stress_level_df[stress_level_df['stress_level'] > 3]

    # Select only the required columns
    high_stress_df = high_stress_df[['Student_Name', 'Student_ID', 'stress_level']]

    return high_stress_df


def Stress_report(database_path, student_id):
    # Get the complete stress level dataframe
    stress_level_df = Stress_level_calculate(database_path)

    # Filter the dataframe for the specified student_id
    student_report = stress_level_df[stress_level_df['Student_ID'] == student_id]

    if student_report.empty:
        return f"No data found for Student ID: {student_id}"

    # Extract the relevant information
    student_name = student_report['Student_Name'].values[0]
    stress_level = student_report['stress_level'].values[0]
    study_time = student_report['Study_Time'].values[0]
    entertainment_time = student_report['Entertainment_Time'].values[0]
    sleep_time = student_report['Sleep_Time'].values[0]

    # Generate suggestions based on study, entertainment, and sleep times
    suggestions = []

    if study_time < 5:
        suggestions.append(f"{student_name}'s study time is too short, please appropriately increase study time")
    elif study_time > 8:
        suggestions.append(f"{student_name}'s study time is too long, please appropriately enjoy spare time")

    if entertainment_time < 3:
        suggestions.append(f"{student_name}'s entertainment time is too short, please appropriately increase entertainment time")
    elif entertainment_time > 5:
        suggestions.append(f"{student_name}'s entertainment time is too long, please appropriately focus on study")

    if sleep_time < 8:
        suggestions.append(f"{student_name}'s sleep time is too short, please appropriately increase sleep time")
    elif sleep_time > 10:
        suggestions.append(f"{student_name}'s sleep time is too long, please appropriately enjoy other time")

    # If no suggestions were generated, add "Everything is Okay!"
    if not suggestions:
        suggestions.append("Everything is Okay!")

    # Generate the report
    report = f"""--Individual Stress Level Analysis--
--Student Name: {student_name}
--Student ID: {student_id}
--Stress Level: {stress_level:.2f}
--Suggest: """
    report += "\n\t".join(suggestions)

    return report
