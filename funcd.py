import sqlite3
import pandas as pd
import struct
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for server-side rendering
import matplotlib.pyplot as plt
import numpy as np
import io

# ----Calculate attendance rate----
def Attendance_rate_calculate(database_path):
    conn = sqlite3.connect(database_path)

    # Select data from Attendance table
    attendance_query = "SELECT Student_ID, Attendance_Status FROM Attendance"
    attendance_df = pd.read_sql_query(attendance_query, conn)

    # Select data from students table
    students_query = "SELECT Student_ID, Student_Name FROM Students"
    students_df = pd.read_sql_query(students_query, conn)

    conn.close()

    # calculate attendance rate
    # Attendance_Status: 0 = Absent, 1 = Partial, 2 = Full
    # Count as attended if status > 0
    def calculate_attendance_rate(df):
        # Count classes where student attended (status > 0)
        attended = df.groupby('Student_ID')['Attendance_Status'].apply(lambda x: (x > 0).sum())
        total = df.groupby('Student_ID')['Attendance_Status'].count()
        attendance_rate = attended / total
        result = attendance_rate.reset_index()
        result.columns = ['Student_ID', 'Attendance_Rate']
        return result

    attendance_rate_df = calculate_attendance_rate(attendance_df)

    att_rate_df = pd.merge(students_df, attendance_rate_df, on='Student_ID', how='left')

    att_rate_df = att_rate_df[['Student_Name', 'Student_ID', 'Attendance_Rate']]
    att_rate_df['Attendance_Rate'] = att_rate_df['Attendance_Rate'].apply(lambda x: f"{x:.0%}")

    return att_rate_df

# ====啦啦啦啦啦啦啦啦啦啦啦====
#    Draw charts (略略略)
# ====啦啦啦啦啦啦啦啦啦啦啦====

# ----Show three grades----
def Students_grades(database_path):
    conn = sqlite3.connect(database_path)

    # Select data from Students table
    students_query = "SELECT Student_ID, Student_Name FROM Students"
    students_df = pd.read_sql_query(students_query, conn)

    # Select data from Assignment table
    assignment_query = """
    SELECT Student_ID, Assignment_Name, Assignment_Grade
    FROM Assignment
    WHERE Assignment_Name IN ('Assignment 1', 'Assignment 2')
    """
    assignment_df = pd.read_sql_query(assignment_query, conn)

    # Select data from Assessment table
    assessment_query = "SELECT Student_ID, Assessment_Grade FROM Assessment"
    assessment_df = pd.read_sql_query(assessment_query, conn)

    conn.close()

    assignment_pivot = assignment_df.pivot(index='Student_ID', columns='Assignment_Name', values='Assignment_Grade')
    assignment_pivot.columns = ['Assignment_1_Grade', 'Assignment_2_Grade']

    # fix data from three tables
    merged_df = pd.merge(students_df, assignment_pivot, on='Student_ID', how='left')
    grades_df = pd.merge(merged_df, assessment_df, on='Student_ID', how='left')

    grades_df.rename(columns={'Assessment_Grade': 'Assessment_Grade'}, inplace=True)
    # reshape table
    grades_df = grades_df[['Student_Name', 'Student_ID', 'Assignment_1_Grade', 'Assignment_2_Grade', 'Assessment_Grade']]

    return grades_df

# ----Assignment Grades----
def barchart_assi_grade(database_path):
    # Select data from Assignment table
    conn = sqlite3.connect(database_path)
    query = "SELECT * FROM Assignment"
    assignment_df = pd.read_sql_query(query, conn)
    conn.close()

    # define stats
    bins = list(range(50, 110, 10))
    labels = [f"{i}-{i+9}" for i in range(50, 100, 10)]

    # statistic data
    assignment_df['Grade_Range'] = pd.cut(assignment_df['Assignment_Grade'], bins=bins, labels=labels, right=False)
    grade_counts = assignment_df.groupby(['Assignment_Name', 'Grade_Range']).size().unstack(fill_value=0)
    all_labels = pd.Index(labels)
    grade_counts = grade_counts.reindex(columns=all_labels, fill_value=0)

    # draw bar chart
    fig, ax = plt.subplots()
    width = 0.35
    x = np.arange(len(labels))

    # bars for assignment 1
    rects1 = ax.bar(x - width/2, grade_counts.loc['Assignment 1'], width, label='Assignment 1', color='#AC6625')
    # bars for assignment 2
    rects2 = ax.bar(x + width/2, grade_counts.loc['Assignment 2'], width, label='Assignment 2', color='#2566AC')

    # label and title
    ax.set_xlabel('Grade Range')
    ax.set_ylabel('Number of Students')
    ax.set_title('Grade Distribution by Assignment')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    # match counts
    def add_labels(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    add_labels(rects1)
    add_labels(rects2)

    # save image
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close(fig)

    return img

# ----Assignment Submission time----
def barchart_assi_subt(database_path):
    # Select data from Assignment table
    conn = sqlite3.connect(database_path)
    query = "SELECT * FROM Assignment"
    assignment_df = pd.read_sql_query(query, conn)
    conn.close()

    # extract weeks
    assignment_df['Week_Number'] = assignment_df['Submission_Week'].str.extract(r'(\d+)').astype(int)
    weeks = sorted(assignment_df['Week_Number'].unique())

    # statistic data
    submission_counts = assignment_df.groupby(['Assignment_Name', 'Week_Number']).size().unstack(fill_value=0)
    all_weeks = pd.Index(weeks)
    submission_counts = submission_counts.reindex(columns=all_weeks, fill_value=0)

    # draw bar chart
    fig, ax = plt.subplots()
    width = 0.35
    x = np.arange(len(weeks))

    # bars for assignment 1
    rects1 = ax.bar(x - width/2, submission_counts.loc['Assignment 1'], width, label='Assignment 1', color='#AC6625')
    # bars for assignment 2
    rects2 = ax.bar(x + width/2, submission_counts.loc['Assignment 2'], width, label='Assignment 2', color='#2566AC')

    # label and title
    ax.set_xlabel('Week')
    ax.set_ylabel('Number of Submissions')
    ax.set_title('Submission Distribution by Week')
    ax.set_xticks(x)
    ax.set_xticklabels(weeks)
    ax.legend()

    # match counts
    def add_labels(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    add_labels(rects1)
    add_labels(rects2)

    # save image
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close(fig)

    return img

# ----Assessment Grades----
def barchart_asse_grade(database_path):
    # Select data from Assessment table
    conn = sqlite3.connect(database_path)
    query = "SELECT * FROM Assessment"
    assessment_df = pd.read_sql_query(query, conn)
    conn.close()

    bins = list(range(50, 110, 10))
    labels = [f"{i}-{i+9}" for i in range(50, 100, 10)]

    assessment_df['Grade_Range'] = pd.cut(assessment_df['Assessment_Grade'], bins=bins, labels=labels, right=False)
    grade_counts = assessment_df['Grade_Range'].value_counts().reindex(labels, fill_value=0)

    # draw bar chart
    fig, ax = plt.subplots()
    x = np.arange(len(labels))
    rects = ax.bar(x, grade_counts, color='#DFADBF')

    #label and title
    ax.set_xlabel('Grade Range')
    ax.set_ylabel('Number of Students')
    ax.set_title('Grade Distribution by Assessment')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)

    # match counts
    def add_labels(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    add_labels(rects)

    # save image
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close(fig)

    return img

# ====啦啦啦啦啦啦啦啦啦啦啦====
#    Draw graphs (嘿嘿嘿)
# ====啦啦啦啦啦啦啦啦啦啦啦====

def plot_asse_att(database_path):
    # 获取出勤率数据
    att_rate_df = Attendance_rate_calculate(database_path)

    # 从 Assessment 表中获取数据
    conn = sqlite3.connect(database_path)
    assessment_query = "SELECT Student_ID, Assessment_Grade FROM Assessment"
    assessment_df = pd.read_sql_query(assessment_query, conn)
    conn.close()

    # 合并出勤率和评估成绩数据
    merged_df = pd.merge(att_rate_df, assessment_df, on='Student_ID', how='inner')

    # 将出勤率转换为数值
    merged_df['Attendance_Rate'] = merged_df['Attendance_Rate'].str.rstrip('%').astype('float')

    # 绘制散点图
    fig, ax = plt.subplots()
    scatter = ax.scatter(merged_df['Assessment_Grade'], merged_df['Attendance_Rate'], color='blue')

    # 添加标签和标题
    ax.set_xlabel('Assessment Grade')
    ax.set_ylabel('Attendance Rate (%)')
    ax.set_title('Attendance Rate vs Assessment Grade')

    # save image
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close(fig)

    return img


