"""
Notification System for Student Wellbeing
- Alerts for low sleep levels
- Alerts for high stress levels
- Alerts for absent students
"""

import sqlite3
import pandas as pd
from datetime import datetime
from funcsw import Stress_level_calculate

DATABASE_PATH = 'Student_wellbeing.db'

# Notification storage (in production, use database)
notifications = []

# Thresholds for alerts
STRESS_THRESHOLD = 3.0  # High stress if > 3
SLEEP_THRESHOLD = 7  # Low sleep if <= 7 hours (adjusted for student wellbeing)
ATTENDANCE_THRESHOLD = 0.7  # Alert if attendance rate < 70%

def generate_stress_alerts(database_path=DATABASE_PATH):
    """Generate alerts for students with high stress levels"""
    stress_df = Stress_level_calculate(database_path)
    high_stress = stress_df[stress_df['stress_level'] > STRESS_THRESHOLD]
    
    alerts = []
    for _, row in high_stress.iterrows():
        alerts.append({
            'type': 'HIGH_STRESS',
            'severity': 'high' if row['stress_level'] > 5 else 'medium',
            'student_id': int(row['Student_ID']),
            'student_name': row['Student_Name'],
            'value': round(row['stress_level'], 2),
            'message': f"⚠️ {row['Student_Name']} (ID: {row['Student_ID']}) has high stress level: {row['stress_level']:.2f}",
            'timestamp': datetime.now().isoformat(),
            'category': 'wellbeing'
        })
    return alerts

def generate_sleep_alerts(database_path=DATABASE_PATH):
    """Generate alerts for students with low sleep"""
    stress_df = Stress_level_calculate(database_path)
    low_sleep = stress_df[stress_df['Sleep_Time'] <= SLEEP_THRESHOLD]
    
    alerts = []
    for _, row in low_sleep.iterrows():
        alerts.append({
            'type': 'LOW_SLEEP',
            'severity': 'high' if row['Sleep_Time'] < 6 else 'medium',
            'student_id': int(row['Student_ID']),
            'student_name': row['Student_Name'],
            'value': int(row['Sleep_Time']),
            'message': f"😴 {row['Student_Name']} (ID: {row['Student_ID']}) has low sleep: {row['Sleep_Time']} hours",
            'timestamp': datetime.now().isoformat(),
            'category': 'wellbeing'
        })
    return alerts

def get_attendance_data(database_path=DATABASE_PATH):
    """Get attendance data with statistics"""
    conn = sqlite3.connect(database_path)
    
    # Get attendance records
    attendance_query = """
    SELECT s.Student_ID, s.Student_Name, a.Weekly, a.Attendance_Status
    FROM Students s
    JOIN Attendance a ON s.Student_ID = a.Student_ID
    ORDER BY s.Student_ID, a.Weekly
    """
    attendance_df = pd.read_sql_query(attendance_query, conn)
    conn.close()
    
    # Calculate attendance rate per student
    # Attendance_Status: 0 = Absent, 1 = Partial, 2 = Full
    # Count as attended if status > 0
    def calc_attendance(group):
        attended = (group['Attendance_Status'] > 0).sum()
        total = len(group)
        return pd.Series({'Classes_Attended': attended, 'Total_Classes': total})
    
    attendance_summary = attendance_df.groupby(['Student_ID', 'Student_Name']).apply(calc_attendance).reset_index()
    attendance_summary['Attendance_Rate'] = attendance_summary['Classes_Attended'] / attendance_summary['Total_Classes']
    
    return attendance_df, attendance_summary

def generate_attendance_alerts(database_path=DATABASE_PATH):
    """Generate alerts for students with low attendance"""
    _, attendance_summary = get_attendance_data(database_path)
    low_attendance = attendance_summary[attendance_summary['Attendance_Rate'] < ATTENDANCE_THRESHOLD]
    
    alerts = []
    for _, row in low_attendance.iterrows():
        rate_percent = row['Attendance_Rate'] * 100
        alerts.append({
            'type': 'LOW_ATTENDANCE',
            'severity': 'high' if rate_percent < 50 else 'medium',
            'student_id': int(row['Student_ID']),
            'student_name': row['Student_Name'],
            'value': round(rate_percent, 1),
            'classes_attended': int(row['Classes_Attended']),
            'total_classes': int(row['Total_Classes']),
            'message': f"📋 {row['Student_Name']} (ID: {row['Student_ID']}) has low attendance: {rate_percent:.1f}% ({int(row['Classes_Attended'])}/{int(row['Total_Classes'])} classes)",
            'timestamp': datetime.now().isoformat(),
            'category': 'attendance'
        })
    return alerts

def get_absent_students(database_path=DATABASE_PATH):
    """Get list of students who have been absent"""
    conn = sqlite3.connect(database_path)
    
    query = """
    SELECT DISTINCT s.Student_ID, s.Student_Name, s.Gender,
           (SELECT COUNT(*) FROM Attendance a2 WHERE a2.Student_ID = s.Student_ID AND a2.Attendance_Status = 0) as Absences,
           (SELECT COUNT(*) FROM Attendance a3 WHERE a3.Student_ID = s.Student_ID) as Total_Classes
    FROM Students s
    JOIN Attendance a ON s.Student_ID = a.Student_ID
    WHERE a.Attendance_Status = 0
    ORDER BY Absences DESC
    """
    absent_df = pd.read_sql_query(query, conn)
    conn.close()
    
    absent_df['Absence_Rate'] = (absent_df['Absences'] / absent_df['Total_Classes'] * 100).round(1)
    return absent_df

def get_all_notifications(database_path=DATABASE_PATH, category=None):
    """Get all notifications, optionally filtered by category"""
    all_alerts = []
    
    # Generate all alerts
    all_alerts.extend(generate_stress_alerts(database_path))
    all_alerts.extend(generate_sleep_alerts(database_path))
    all_alerts.extend(generate_attendance_alerts(database_path))
    
    # Filter by category if specified
    if category:
        all_alerts = [a for a in all_alerts if a['category'] == category]
    
    # Sort by severity (high first) then by timestamp
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    all_alerts.sort(key=lambda x: (severity_order.get(x['severity'], 3), x['timestamp']), reverse=False)
    
    return all_alerts

def get_notification_summary(database_path=DATABASE_PATH):
    """Get summary of all notifications"""
    all_alerts = get_all_notifications(database_path)
    
    summary = {
        'total': len(all_alerts),
        'high_severity': len([a for a in all_alerts if a['severity'] == 'high']),
        'medium_severity': len([a for a in all_alerts if a['severity'] == 'medium']),
        'by_type': {
            'stress': len([a for a in all_alerts if a['type'] == 'HIGH_STRESS']),
            'sleep': len([a for a in all_alerts if a['type'] == 'LOW_SLEEP']),
            'attendance': len([a for a in all_alerts if a['type'] == 'LOW_ATTENDANCE'])
        },
        'by_category': {
            'wellbeing': len([a for a in all_alerts if a['category'] == 'wellbeing']),
            'attendance': len([a for a in all_alerts if a['category'] == 'attendance'])
        }
    }
    return summary
