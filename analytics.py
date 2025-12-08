"""
Analytics Module for Student Wellbeing
- Stress level analysis and visualization data
- Attendance correlation with grades
- Trend analysis
"""

import sqlite3
import pandas as pd
from funcsw import Stress_level_calculate

DATABASE_PATH = 'Student_wellbeing.db'

def get_stress_over_time_data(database_path=DATABASE_PATH):
    """
    Get stress level data formatted for time-series visualization.
    Since we have weekly attendance data, we'll correlate stress with weeks.
    """
    stress_df = Stress_level_calculate(database_path)
    
    # Create visualization-ready data
    chart_data = {
        'students': stress_df['Student_Name'].tolist(),
        'student_ids': stress_df['Student_ID'].tolist(),
        'stress_levels': stress_df['stress_level'].round(2).tolist(),
        'study_time': stress_df['Study_Time'].tolist(),
        'entertainment_time': stress_df['Entertainment_Time'].tolist(),
        'sleep_time': stress_df['Sleep_Time'].tolist()
    }
    
    # Statistics for the chart
    stats = {
        'average_stress': round(stress_df['stress_level'].mean(), 2),
        'max_stress': round(stress_df['stress_level'].max(), 2),
        'min_stress': round(stress_df['stress_level'].min(), 2),
        'std_stress': round(stress_df['stress_level'].std(), 2),
        'high_stress_count': int((stress_df['stress_level'] > 3).sum()),
        'total_students': len(stress_df)
    }
    
    # Distribution data for histogram
    bins = [0, 1, 2, 3, 4, 5, 10]
    labels = ['0-1', '1-2', '2-3', '3-4', '4-5', '5+']
    stress_df['stress_bin'] = pd.cut(stress_df['stress_level'], bins=bins, labels=labels, right=False)
    distribution = stress_df['stress_bin'].value_counts().sort_index().to_dict()
    
    return {
        'chart_data': chart_data,
        'statistics': stats,
        'distribution': {str(k): int(v) for k, v in distribution.items()}
    }

def get_attendance_assignment_correlation(database_path=DATABASE_PATH):
    """
    Calculate correlation between attendance and assignment grades.
    This helps identify if absent students perform worse.
    """
    conn = sqlite3.connect(database_path)
    
    # Get attendance rate per student (Attendance_Status: 0=Absent, 1=Partial, 2=Full)
    # Count as attended if status > 0
    attendance_query = """
    SELECT Student_ID,
           SUM(CASE WHEN Attendance_Status > 0 THEN 1 ELSE 0 END) as Classes_Attended,
           COUNT(*) as Total_Classes,
           CAST(SUM(CASE WHEN Attendance_Status > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as Attendance_Rate
    FROM Attendance
    GROUP BY Student_ID
    """
    attendance_df = pd.read_sql_query(attendance_query, conn)
    
    # Get average assignment grade per student
    assignment_query = """
    SELECT Student_ID,
           AVG(Assignment_Grade) as Avg_Assignment_Grade,
           COUNT(*) as Assignments_Submitted
    FROM Assignment
    GROUP BY Student_ID
    """
    assignment_df = pd.read_sql_query(assignment_query, conn)
    
    # Get student names
    students_query = "SELECT Student_ID, Student_Name FROM Students"
    students_df = pd.read_sql_query(students_query, conn)
    
    # Get assessment grades
    assessment_query = "SELECT Student_ID, Assessment_Grade FROM Assessment"
    assessment_df = pd.read_sql_query(assessment_query, conn)
    
    conn.close()
    
    # Merge all data
    correlation_df = students_df.merge(attendance_df, on='Student_ID')
    correlation_df = correlation_df.merge(assignment_df, on='Student_ID')
    correlation_df = correlation_df.merge(assessment_df, on='Student_ID', how='left')
    
    # Calculate correlations
    attendance_assignment_corr = correlation_df['Attendance_Rate'].corr(correlation_df['Avg_Assignment_Grade'])
    attendance_assessment_corr = correlation_df['Attendance_Rate'].corr(correlation_df['Assessment_Grade'])
    
    # Categorize students - using bins that match actual data distribution (mostly 70-100%)
    correlation_df['Attendance_Category'] = pd.cut(
        correlation_df['Attendance_Rate'],
        bins=[0, 75, 85, 95, 100.1],
        labels=['Below 75%', '75-85%', '85-95%', '95-100%'],
        include_lowest=True
    )
    
    # Average grades by attendance category
    category_analysis = correlation_df.groupby('Attendance_Category', observed=True).agg({
        'Avg_Assignment_Grade': 'mean',
        'Assessment_Grade': 'mean',
        'Student_ID': 'count'
    }).round(2).reset_index()
    category_analysis.columns = ['Attendance_Category', 'Avg_Assignment_Grade', 'Avg_Assessment_Grade', 'Student_Count']
    
    return {
        'correlation': {
            'attendance_vs_assignment': round(attendance_assignment_corr, 3) if pd.notna(attendance_assignment_corr) else 0,
            'attendance_vs_assessment': round(attendance_assessment_corr, 3) if pd.notna(attendance_assessment_corr) else 0
        },
        'interpretation': get_correlation_interpretation(attendance_assignment_corr),
        'category_analysis': category_analysis.to_dict(orient='records'),
        'student_data': correlation_df[['Student_Name', 'Student_ID', 'Attendance_Rate', 
                                        'Avg_Assignment_Grade', 'Assessment_Grade']].round(2).to_dict(orient='records')
    }

def get_correlation_interpretation(corr_value):
    """Interpret correlation coefficient"""
    if pd.isna(corr_value):
        return "Unable to calculate correlation"
    
    abs_corr = abs(corr_value)
    direction = "positive" if corr_value > 0 else "negative"
    
    if abs_corr < 0.2:
        strength = "very weak"
    elif abs_corr < 0.4:
        strength = "weak"
    elif abs_corr < 0.6:
        strength = "moderate"
    elif abs_corr < 0.8:
        strength = "strong"
    else:
        strength = "very strong"
    
    if corr_value > 0:
        message = f"There is a {strength} {direction} correlation ({corr_value:.3f}). Students with higher attendance tend to have better grades."
    else:
        message = f"There is a {strength} {direction} correlation ({corr_value:.3f}). This is unusual and may warrant investigation."
    
    return message

def get_participation_overview(database_path=DATABASE_PATH):
    """Get overall participation metrics for the course"""
    conn = sqlite3.connect(database_path)
    
    # Overall attendance - Note: Attendance_Status can be 0, 1, or 2
    # 2 = Full attendance, 1 = Partial, 0 = Absent
    # We normalize by dividing by 2 (max possible value) to get proper percentage
    attendance_query = """
    SELECT 
        COUNT(DISTINCT Student_ID) as Total_Students,
        SUM(Attendance_Status) as Total_Attended_Points,
        COUNT(*) as Total_Records,
        SUM(CASE WHEN Attendance_Status > 0 THEN 1 ELSE 0 END) as Classes_With_Attendance,
        CAST(SUM(CASE WHEN Attendance_Status > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as Overall_Attendance_Rate
    FROM Attendance
    """
    overall = pd.read_sql_query(attendance_query, conn)
    
    # Weekly attendance trend - count students who attended (status > 0)
    weekly_query = """
    SELECT Weekly,
           SUM(CASE WHEN Attendance_Status > 0 THEN 1 ELSE 0 END) as Attended,
           COUNT(*) as Total,
           CAST(SUM(CASE WHEN Attendance_Status > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as Attendance_Rate
    FROM Attendance
    GROUP BY Weekly
    ORDER BY Weekly
    """
    weekly_df = pd.read_sql_query(weekly_query, conn)
    
    # Assignment submission stats
    assignment_query = """
    SELECT Assignment_Name,
           COUNT(*) as Submissions,
           AVG(Assignment_Grade) as Avg_Grade
    FROM Assignment
    GROUP BY Assignment_Name
    """
    assignment_df = pd.read_sql_query(assignment_query, conn)
    
    conn.close()
    
    return {
        'overall': {
            'total_students': int(overall['Total_Students'].iloc[0]),
            'overall_attendance_rate': round(overall['Overall_Attendance_Rate'].iloc[0], 1),
            'total_classes': int(overall['Total_Records'].iloc[0] / overall['Total_Students'].iloc[0])
        },
        'weekly_trend': {
            'weeks': weekly_df['Weekly'].tolist(),
            'attendance_rates': weekly_df['Attendance_Rate'].round(1).tolist(),
            'attended': weekly_df['Attended'].tolist(),
            'total': weekly_df['Total'].tolist()
        },
        'assignments': assignment_df.to_dict(orient='records')
    }


def get_grade_distribution_by_week(database_path=DATABASE_PATH):
    """
    Get grade distribution by submission week for bar chart visualization.
    Shows how grades vary based on when assignments were submitted.
    """
    conn = sqlite3.connect(database_path)
    
    # Normalize week names (some have lowercase 'week', some have 'Week')
    query = """
    SELECT 
        LOWER(Submission_Week) as Submission_Week,
        Assignment_Grade
    FROM Assignment
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Create grade bins for distribution
    bins = [0, 50, 60, 70, 80, 90, 100]
    labels = ['0-50', '50-60', '60-70', '70-80', '80-90', '90-100']
    df['Grade_Range'] = pd.cut(df['Assignment_Grade'], bins=bins, labels=labels, include_lowest=True)
    
    # Group by week and get statistics
    week_stats = df.groupby('Submission_Week').agg({
        'Assignment_Grade': ['count', 'mean', 'min', 'max', 'std']
    }).round(2)
    week_stats.columns = ['Count', 'Avg_Grade', 'Min_Grade', 'Max_Grade', 'Std_Dev']
    week_stats = week_stats.reset_index()
    
    # Sort weeks properly
    def sort_week(week):
        try:
            return int(week.replace('week ', ''))
        except:
            return 99
    
    week_stats['week_num'] = week_stats['Submission_Week'].apply(sort_week)
    week_stats = week_stats.sort_values('week_num')
    
    # Get grade distribution per week
    grade_dist = df.groupby(['Submission_Week', 'Grade_Range'], observed=True).size().unstack(fill_value=0)
    
    # Ensure all grade ranges exist
    for label in labels:
        if label not in grade_dist.columns:
            grade_dist[label] = 0
    grade_dist = grade_dist[labels]  # Reorder columns
    
    # Sort by week number
    grade_dist['week_num'] = grade_dist.index.map(sort_week)
    grade_dist = grade_dist.sort_values('week_num')
    grade_dist = grade_dist.drop('week_num', axis=1)
    
    return {
        'weeks': week_stats['Submission_Week'].tolist(),
        'avg_grades': week_stats['Avg_Grade'].tolist(),
        'counts': week_stats['Count'].tolist(),
        'min_grades': week_stats['Min_Grade'].tolist(),
        'max_grades': week_stats['Max_Grade'].tolist(),
        'grade_distribution': {
            'weeks': grade_dist.index.tolist(),
            'ranges': labels,
            'data': {label: grade_dist[label].tolist() for label in labels}
        },
        'summary': {
            'total_assignments': len(df),
            'overall_avg': round(df['Assignment_Grade'].mean(), 2),
            'overall_std': round(df['Assignment_Grade'].std(), 2)
        }
    }
