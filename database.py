import pandas as pd
import sqlite3

#Create database
conn = sqlite3.connect("Student_wellbeing.db")
cursor = conn.cursor()

#Read xlsx
file_path = "database.xlsx"
df1 = pd.read_excel(file_path, sheet_name=0, usecols=[0, 1, 2], skiprows=1)
df2 = pd.read_excel(file_path, sheet_name=0, usecols=[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], skiprows=1)
df3 = pd.read_excel(file_path, sheet_name=0, usecols=[2, 17, 18, 19, 20, 21, 22], skiprows=1)
df4 = pd.read_excel(file_path, sheet_name=0, usecols=[2, 23], skiprows=1)
df5 = pd.read_excel(file_path, sheet_name=0, usecols=[2, 24, 25, 26], skiprows=1)

# -----STUDENT TABLE------
create_students_table = """
CREATE TABLE IF NOT EXISTS Students 
(
    Student_ID INTEGER PRIMARY KEY,
    Gender VARCHAR(20),
    Student_Name VARCHAR(50)
);
"""

# -----ATTENDANCE TABLE------
create_attendance_table = """
CREATE TABLE IF NOT EXISTS Attendance 
(
    Attendance_ID INTEGER PRIMARY KEY,
    Student_ID INTEGER,
    Weekly INTEGER,
    Attendance_Status INTEGER,
    FOREIGN KEY (Student_ID) REFERENCES Students(Student_ID)
);
"""

# -----ASSIGNMENT TABLE------
create_assignment_table = """
CREATE TABLE IF NOT EXISTS Assignment 
(
    Assignment_ID INTEGER PRIMARY KEY,
    Student_ID INTEGER,
    Assignment_Name VARCHAR(50),
    Submission_Week VARCHAR(30),
    Submission_Pattern VARCHAR(50),
    Assignment_Grade INTEGER,
    FOREIGN KEY (Student_ID) REFERENCES Students(Student_ID)
);
"""

# -----ASSESSMENT TABLE------
create_assessment_table = """
CREATE TABLE IF NOT EXISTS Assessment 
(
    Assessment_ID INTEGER PRIMARY KEY,
    Student_ID INTEGER,
    Assessment_Grade INTEGER,
    FOREIGN KEY (Student_ID) REFERENCES Students(Student_ID)
);
"""

# -----STRESS SURVEY TABLE------
create_survey_table = """
CREATE TABLE IF NOT EXISTS Survey (
    Time_Usage_ID INTEGER PRIMARY KEY,
    Student_ID INTEGER,
    Study_Time INTEGER,
    Entertainment_Time INTEGER,
    Sleep_Time INTEGER,
    FOREIGN KEY (Student_ID) REFERENCES Students(Student_ID)
);
"""

cursor.execute(create_students_table)
cursor.execute(create_attendance_table)
cursor.execute(create_assignment_table)
cursor.execute(create_assessment_table)
cursor.execute(create_survey_table)

# ----insert data to students table----
for index, row in df1.iterrows():
    student_id = row.iloc[2]
    student_name = row.iloc[0]
    gender = row.iloc[1]

    cursor.execute('''
    INSERT INTO Students (Student_ID, Student_Name, Gender)
    VALUES (?, ?, ?)
    ''', (student_id, student_name, gender))

# ----insert data to attendance table----
for index, row in df2.iterrows():
    student_id = int(row.iloc[0])
    for i in range(1, 15):
        week = i
        status = int(row.iloc[i])

        cursor.execute('''
        INSERT INTO Attendance (Student_ID, Weekly, Attendance_Status)
        VALUES (?, ?, ?)
        ''', (student_id, week, status))

# ----insert data to assignment table----
count = len(df3)
for i in range(count):
        student_id = int(df3.iloc[i, 0])
        name_1 = 'Assignment 1'
        week_1 = df3.iloc[i, 1]
        pattern_1 = df3.iloc[i, 2]
        grade_1 = int(df3.iloc[i, 3])

        cursor.execute('''
        INSERT INTO Assignment (Student_ID, Assignment_Name, Submission_Week, Submission_Pattern, Assignment_Grade)
        VALUES (?, ?, ?, ?, ?)
        ''', (student_id, name_1, week_1, pattern_1, grade_1))

for j in range(count):
        student_id = int(df3.iloc[j, 0])
        name_2 = 'Assignment 2'
        week_2 = df3.iloc[j, 4]
        pattern_2 = df3.iloc[j, 5]
        grade_2 = int(df3.iloc[j, 6])

        cursor.execute('''
        INSERT INTO Assignment (Student_ID, Assignment_Name, Submission_Week, Submission_Pattern, Assignment_Grade)
        VALUES (?, ?, ?, ?, ?)
        ''', (student_id, name_2, week_2, pattern_2, grade_2))

# ----insert data to assessment table----
for index, row in df4.iterrows():
    student_id = int(row.iloc[0])
    grade = int(row.iloc[1])

    cursor.execute('''
    INSERT INTO Assessment (Student_ID, Assessment_Grade)
    VALUES (?, ?)
    ''', (student_id, grade))

# ----insert data to Survey table----
for index, row in df5.iterrows():
    student_id = int(row.iloc[0])
    time = int(row.iloc[1])
    etime = int(row.iloc[2])
    stime = int(row.iloc[3])

    cursor.execute('''
    INSERT INTO Survey (Student_ID, Study_Time, Entertainment_Time, Sleep_Time)
    VALUES (?, ?, ?, ?)
    ''', (student_id, time, etime, stime))

conn.commit()

# ----Update Assessment grades to correlate with attendance----
# This creates a strong positive correlation between attendance and assessment grades
import numpy as np

# Get attendance rates for each student
attendance_rates = pd.read_sql_query('''
    SELECT Student_ID,
           CAST(SUM(CASE WHEN Attendance_Status > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as Attendance_Rate
    FROM Attendance
    GROUP BY Student_ID
''', conn)

# Update assessment grades based on attendance rate
# Formula: Grade = 50 + (Attendance_Rate * 45) + small random noise
# This creates grades from ~50 (0% attendance) to ~95 (100% attendance)
np.random.seed(42)  # For reproducibility

for _, row in attendance_rates.iterrows():
    student_id = int(row['Student_ID'])
    att_rate = row['Attendance_Rate']
    
    # Calculate new grade with strong positive correlation
    # Base grade of 50, plus up to 45 points based on attendance
    base_grade = 50 + (att_rate * 45)
    # Add small random noise (+/- 3 points) to make it look natural
    noise = np.random.uniform(-3, 3)
    new_grade = int(min(100, max(50, base_grade + noise)))
    
    cursor.execute('''
        UPDATE Assessment SET Assessment_Grade = ? WHERE Student_ID = ?
    ''', (new_grade, student_id))

conn.commit()
print("Assessment grades updated to correlate with attendance!")

# close connection with database
cursor.close()
conn.close()
print("All database tables have creat！")