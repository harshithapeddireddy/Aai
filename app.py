"""
Student Wellbeing Application
Main Flask application with all features integrated
"""

from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3
import pandas as pd

from auth import authenticate_user, create_session, get_user_from_token, logout_user, require_auth, require_role
from notifications import (
    get_all_notifications, get_notification_summary, 
    generate_stress_alerts, generate_sleep_alerts, generate_attendance_alerts,
    get_absent_students, get_attendance_data
)
from analytics import (
    get_stress_over_time_data, get_attendance_assignment_correlation,
    get_participation_overview, get_grade_distribution_by_week
)
from funcsw import Stress_level_calculate, filter_high_stress_students, Stress_report
from funcd import (
    Attendance_rate_calculate, Students_grades,
    barchart_assi_grade, barchart_assi_subt, barchart_asse_grade, plot_asse_att
)

app = Flask(__name__)

DATABASE_PATH = 'Student_wellbeing.db'

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.route('/login', methods=['POST'])
def login():
    """Login endpoint - returns session token"""
    data = request.json or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    user = authenticate_user(username, password)
    if user:
        token = create_session(user)
        return jsonify({
            'success': True,
            'message': f"Welcome, {user['name']}!",
            'token': token,
            'user': user
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Invalid username or password'
        }), 401

@app.route('/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if logout_user(token):
        return jsonify({'success': True, 'message': 'Logged out successfully'}), 200
    return jsonify({'success': False, 'error': 'Invalid session'}), 400

# ==================== WELLBEING OFFICER ENDPOINTS ====================

@app.route('/api/stress-levels', methods=['GET'])
@require_auth('view_stress')
def get_stress_levels():
    """Get all student stress levels - Wellbeing Officers only"""
    stress_df = Stress_level_calculate(DATABASE_PATH)
    return jsonify({
        'success': True,
        'data': stress_df.to_dict(orient='records'),
        'accessed_by': request.current_user['name']
    })

@app.route('/api/high-stress-students', methods=['GET'])
@require_auth('view_stress')
def get_high_stress():
    """Get students with high stress - Wellbeing Officers only"""
    high_stress_df = filter_high_stress_students(DATABASE_PATH)
    return jsonify({
        'success': True,
        'data': high_stress_df.to_dict(orient='records'),
        'count': len(high_stress_df),
        'accessed_by': request.current_user['name']
    })

@app.route('/api/student-report/<int:student_id>', methods=['GET'])
@require_auth('view_reports')
def get_student_report(student_id):
    """Get individual student report - Wellbeing Officers only"""
    report = Stress_report(DATABASE_PATH, student_id)
    return jsonify({
        'success': True,
        'report': report,
        'accessed_by': request.current_user['name']
    })

@app.route('/api/sleep-alerts', methods=['GET'])
@require_auth('view_sleep')
def get_sleep_alerts():
    """Get sleep-related alerts - Wellbeing Officers only"""
    alerts = generate_sleep_alerts(DATABASE_PATH)
    return jsonify({
        'success': True,
        'alerts': alerts,
        'count': len(alerts),
        'accessed_by': request.current_user['name']
    })

@app.route('/api/stress-visualization', methods=['GET'])
@require_auth('view_stress')
def get_stress_visualization():
    """Get stress data for visualization - Wellbeing Officers only"""
    viz_data = get_stress_over_time_data(DATABASE_PATH)
    return jsonify({
        'success': True,
        'data': viz_data,
        'accessed_by': request.current_user['name']
    })

@app.route('/api/stress-heatmap', methods=['GET'])
@require_auth('view_stress')
def get_stress_heatmap():
    """Get stress heatmap data - Wellbeing Officers only"""
    stress_df = Stress_level_calculate(DATABASE_PATH)
    
    # Create heatmap data with all factors
    heatmap_data = []
    for _, row in stress_df.iterrows():
        heatmap_data.append({
            'student_name': row['Student_Name'],
            'student_id': int(row['Student_ID']),
            'stress_level': round(row['stress_level'], 2),
            'study_time': int(row['Study_Time']),
            'entertainment_time': int(row['Entertainment_Time']),
            'sleep_time': int(row['Sleep_Time']),
            # Normalized values for heatmap coloring (0-1 scale)
            'stress_normalized': min(1, max(0, row['stress_level'] / 6)),
            'study_normalized': min(1, max(0, row['Study_Time'] / 12)),
            'entertainment_normalized': min(1, max(0, row['Entertainment_Time'] / 8)),
            'sleep_normalized': min(1, max(0, (10 - row['Sleep_Time']) / 10))  # Inverted: less sleep = higher concern
        })
    
    # Sort by stress level descending
    heatmap_data.sort(key=lambda x: x['stress_level'], reverse=True)
    
    return jsonify({
        'success': True,
        'data': heatmap_data,
        'factors': ['Stress Level', 'Study Time', 'Entertainment', 'Sleep (Concern)'],
        'accessed_by': request.current_user['name']
    })

# ==================== COURSE LEAD ENDPOINTS ====================

@app.route('/api/attendance', methods=['GET'])
@require_auth('view_attendance')
def get_attendance():
    """Get attendance data - Course Lead only"""
    attendance_df, summary_df = get_attendance_data(DATABASE_PATH)
    return jsonify({
        'success': True,
        'summary': summary_df.to_dict(orient='records'),
        'accessed_by': request.current_user['name']
    })

@app.route('/api/absent-students', methods=['GET'])
@require_auth('view_absent_students')
def get_absent_students_list():
    """Get list of absent students - Course Lead only"""
    absent_df = get_absent_students(DATABASE_PATH)
    return jsonify({
        'success': True,
        'data': absent_df.to_dict(orient='records'),
        'count': len(absent_df),
        'accessed_by': request.current_user['name']
    })

@app.route('/api/attendance-alerts', methods=['GET'])
@require_auth('view_attendance')
def get_attendance_alerts():
    """Get attendance-related alerts - Course Lead only"""
    alerts = generate_attendance_alerts(DATABASE_PATH)
    return jsonify({
        'success': True,
        'alerts': alerts,
        'count': len(alerts),
        'accessed_by': request.current_user['name']
    })

@app.route('/api/correlation', methods=['GET'])
@require_auth('view_correlation')
def get_correlation():
    """Get attendance-grade correlation - Course Lead only"""
    correlation_data = get_attendance_assignment_correlation(DATABASE_PATH)
    return jsonify({
        'success': True,
        'data': correlation_data,
        'accessed_by': request.current_user['name']
    })

@app.route('/api/participation', methods=['GET'])
@require_auth('view_attendance')
def get_participation():
    """Get participation overview - Course Lead only"""
    participation_data = get_participation_overview(DATABASE_PATH)
    return jsonify({
        'success': True,
        'data': participation_data,
        'accessed_by': request.current_user['name']
    })

@app.route('/api/grade-distribution', methods=['GET'])
@require_auth('view_attendance')
def get_grade_dist():
    """Get grade distribution by submission week - Course Lead only"""
    grade_data = get_grade_distribution_by_week(DATABASE_PATH)
    return jsonify({
        'success': True,
        'data': grade_data,
        'accessed_by': request.current_user['name']
    })

# ==================== SHARED ENDPOINTS ====================

@app.route('/api/notifications', methods=['GET'])
@require_auth('view_notifications')
def get_notifications():
    """Get notifications based on user role"""
    user = request.current_user
    
    if user['role'] == 'wellbeing_officer':
        # Wellbeing officers see stress and sleep alerts
        notifications = get_all_notifications(DATABASE_PATH, category='wellbeing')
    elif user['role'] == 'course_lead':
        # Course lead sees attendance alerts
        notifications = get_all_notifications(DATABASE_PATH, category='attendance')
    else:
        # Admin sees all
        notifications = get_all_notifications(DATABASE_PATH)
    
    return jsonify({
        'success': True,
        'notifications': notifications,
        'count': len(notifications),
        'accessed_by': user['name']
    })

@app.route('/api/notification-summary', methods=['GET'])
@require_auth('view_notifications')
def get_notif_summary():
    """Get notification summary"""
    summary = get_notification_summary(DATABASE_PATH)
    return jsonify({
        'success': True,
        'summary': summary,
        'accessed_by': request.current_user['name']
    })

# ==================== ADMIN ENDPOINTS (Student Management) ====================

@app.route('/api/admin/students', methods=['GET'])
@require_auth('manage_students')
def admin_get_students():
    """Get all students for admin management"""
    conn = sqlite3.connect(DATABASE_PATH)
    query = """
    SELECT s.Student_ID, s.Student_Name, s.Gender,
           (SELECT AVG(CASE WHEN Attendance_Status > 0 THEN 1.0 ELSE 0.0 END) * 100 
            FROM Attendance a WHERE a.Student_ID = s.Student_ID) as Attendance_Rate,
           (SELECT Assessment_Grade FROM Assessment ass WHERE ass.Student_ID = s.Student_ID) as Assessment_Grade
    FROM Students s
    ORDER BY s.Student_Name
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return jsonify({
        'success': True,
        'students': df.to_dict(orient='records'),
        'total': len(df)
    })

@app.route('/api/admin/students', methods=['POST'])
@require_auth('add_student')
def admin_add_student():
    """Add a new student"""
    data = request.json or {}
    student_name = data.get('student_name', '').strip()
    gender = data.get('gender', '').strip()
    
    if not student_name:
        return jsonify({'success': False, 'error': 'Student name is required'}), 400
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Get next student ID
        cursor.execute("SELECT MAX(Student_ID) FROM Students")
        max_id = cursor.fetchone()[0] or 5686822
        new_id = max_id + 1
        
        # Insert student
        cursor.execute("INSERT INTO Students (Student_ID, Student_Name, Gender) VALUES (?, ?, ?)",
                      (new_id, student_name, gender))
        
        # Initialize with default survey data
        cursor.execute("INSERT INTO Survey (Student_ID, Study_Time, Entertainment_Time, Sleep_Time) VALUES (?, ?, ?, ?)",
                      (new_id, 5, 3, 7))
        
        # Initialize with default assessment
        cursor.execute("INSERT INTO Assessment (Student_ID, Assessment_Grade) VALUES (?, ?)",
                      (new_id, 70))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Student {student_name} added successfully',
            'student_id': new_id
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/students/<int:student_id>', methods=['PUT'])
@require_auth('update_student')
def admin_update_student(student_id):
    """Update an existing student"""
    data = request.json or {}
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if student exists
        cursor.execute("SELECT Student_ID FROM Students WHERE Student_ID = ?", (student_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        updates = []
        params = []
        
        if 'student_name' in data:
            updates.append("Student_Name = ?")
            params.append(data['student_name'])
        if 'gender' in data:
            updates.append("Gender = ?")
            params.append(data['gender'])
        
        if updates:
            params.append(student_id)
            cursor.execute(f"UPDATE Students SET {', '.join(updates)} WHERE Student_ID = ?", params)
        
        # Update survey data if provided
        if any(k in data for k in ['study_time', 'entertainment_time', 'sleep_time']):
            survey_updates = []
            survey_params = []
            if 'study_time' in data:
                survey_updates.append("Study_Time = ?")
                survey_params.append(data['study_time'])
            if 'entertainment_time' in data:
                survey_updates.append("Entertainment_Time = ?")
                survey_params.append(data['entertainment_time'])
            if 'sleep_time' in data:
                survey_updates.append("Sleep_Time = ?")
                survey_params.append(data['sleep_time'])
            
            if survey_updates:
                survey_params.append(student_id)
                cursor.execute(f"UPDATE Survey SET {', '.join(survey_updates)} WHERE Student_ID = ?", survey_params)
        
        # Update assessment grade if provided
        if 'assessment_grade' in data:
            cursor.execute("UPDATE Assessment SET Assessment_Grade = ? WHERE Student_ID = ?",
                          (data['assessment_grade'], student_id))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Student {student_id} updated successfully'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/students/<int:student_id>', methods=['DELETE'])
@require_auth('delete_student')
def admin_delete_student(student_id):
    """Delete a student and all related records"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if student exists
        cursor.execute("SELECT Student_Name FROM Students WHERE Student_ID = ?", (student_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        student_name = result[0]
        
        # Delete from all related tables
        cursor.execute("DELETE FROM Attendance WHERE Student_ID = ?", (student_id,))
        cursor.execute("DELETE FROM Assignment WHERE Student_ID = ?", (student_id,))
        cursor.execute("DELETE FROM Assessment WHERE Student_ID = ?", (student_id,))
        cursor.execute("DELETE FROM Survey WHERE Student_ID = ?", (student_id,))
        cursor.execute("DELETE FROM Students WHERE Student_ID = ?", (student_id,))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Student {student_name} (ID: {student_id}) deleted successfully'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/students/<int:student_id>', methods=['GET'])
@require_auth('manage_students')
def admin_get_student(student_id):
    """Get detailed info for a specific student"""
    conn = sqlite3.connect(DATABASE_PATH)
    
    try:
        # Get student info
        student = pd.read_sql_query("SELECT * FROM Students WHERE Student_ID = ?", conn, params=[student_id])
        if student.empty:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Get survey data
        survey = pd.read_sql_query("SELECT * FROM Survey WHERE Student_ID = ?", conn, params=[student_id])
        
        # Get assessment data
        assessment = pd.read_sql_query("SELECT * FROM Assessment WHERE Student_ID = ?", conn, params=[student_id])
        
        # Get attendance summary
        attendance = pd.read_sql_query("""
            SELECT COUNT(*) as Total_Classes,
                   SUM(CASE WHEN Attendance_Status > 0 THEN 1 ELSE 0 END) as Classes_Attended
            FROM Attendance WHERE Student_ID = ?
        """, conn, params=[student_id])
        
        # Get assignments
        assignments = pd.read_sql_query("SELECT * FROM Assignment WHERE Student_ID = ?", conn, params=[student_id])
        
        return jsonify({
            'success': True,
            'student': student.to_dict(orient='records')[0],
            'survey': survey.to_dict(orient='records')[0] if not survey.empty else {},
            'assessment': assessment.to_dict(orient='records')[0] if not assessment.empty else {},
            'attendance': attendance.to_dict(orient='records')[0] if not attendance.empty else {},
            'assignments': assignments.to_dict(orient='records')
        })
    finally:
        conn.close()

# ==================== DASHBOARD ====================

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Wellbeing Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        
        .login-container {
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .login-box {
            background: white; padding: 40px; border-radius: 10px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.2); width: 350px;
        }
        .login-box h2 { text-align: center; margin-bottom: 30px; color: #333; }
        .login-box input {
            width: 100%; padding: 12px; margin-bottom: 15px;
            border: 1px solid #ddd; border-radius: 5px; font-size: 14px;
        }
        .login-box button {
            width: 100%; padding: 12px; background: #667eea;
            color: white; border: none; border-radius: 5px;
            font-size: 16px; cursor: pointer; transition: background 0.3s;
        }
        .login-box button:hover { background: #5a6fd6; }
        .error { color: #e74c3c; text-align: center; margin-bottom: 15px; }
        
        .dashboard { display: none; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px 40px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .header h1 { font-size: 24px; }
        .user-info { display: flex; align-items: center; gap: 15px; }
        .user-info span { font-size: 14px; }
        .logout-btn {
            background: rgba(255,255,255,0.2); border: none;
            color: white; padding: 8px 16px; border-radius: 5px; cursor: pointer;
        }
        
        .nav-tabs {
            background: white; padding: 0 40px;
            border-bottom: 1px solid #e0e0e0; display: flex; gap: 5px;
        }
        .nav-tab {
            padding: 15px 25px; cursor: pointer; border: none;
            background: none; font-size: 14px; color: #666;
            border-bottom: 3px solid transparent; transition: all 0.3s;
        }
        .nav-tab:hover { color: #667eea; }
        .nav-tab.active { color: #667eea; border-bottom-color: #667eea; }
        .nav-tab.disabled { color: #ccc; cursor: not-allowed; }
        
        .content { padding: 30px 40px; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card {
            background: white; padding: 25px; border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }
        .card h3 { font-size: 14px; color: #666; margin-bottom: 10px; }
        .card .value { font-size: 32px; font-weight: bold; color: #333; }
        .card .value.warning { color: #e74c3c; }
        .card .value.success { color: #27ae60; }
        
        .chart-container { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 30px; }
        .chart-container h3 { margin-bottom: 20px; color: #333; }
        
        .table-container { background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); overflow: hidden; }
        .table-container h3 { padding: 20px 25px; border-bottom: 1px solid #eee; color: #333; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 25px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; color: #666; }
        tr:hover { background: #f8f9fa; }
        
        .alert-list { max-height: 400px; overflow-y: auto; }
        .alert-item {
            padding: 15px 25px; border-bottom: 1px solid #eee;
            display: flex; align-items: center; gap: 15px;
        }
        .alert-badge {
            padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600;
        }
        .alert-badge.high { background: #ffeaea; color: #e74c3c; }
        .alert-badge.medium { background: #fff3e0; color: #f39c12; }
        
        .correlation-box {
            background: white; padding: 25px; border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 20px;
        }
        .correlation-value { font-size: 48px; font-weight: bold; text-align: center; margin: 20px 0; }
        .correlation-value.positive { color: #27ae60; }
        .correlation-value.negative { color: #e74c3c; }
        .interpretation { text-align: center; color: #666; font-size: 14px; }
        
        /* Heatmap Styles */
        .heatmap-container {
            background: white; padding: 25px; border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 30px;
            overflow-x: auto;
        }
        .heatmap-container h3 { margin-bottom: 20px; color: #333; }
        .heatmap-legend {
            display: flex; align-items: center; gap: 20px;
            margin-bottom: 20px; font-size: 12px; color: #666;
        }
        .legend-gradient {
            width: 200px; height: 20px; border-radius: 4px;
            background: linear-gradient(to right, #27ae60, #f39c12, #e74c3c);
        }
        .heatmap-table { width: 100%; border-collapse: collapse; }
        .heatmap-table th { 
            padding: 12px 15px; text-align: left; 
            background: #f8f9fa; font-weight: 600; color: #666;
            border-bottom: 2px solid #e0e0e0;
        }
        .heatmap-table td { 
            padding: 10px 15px; text-align: center;
            border-bottom: 1px solid #eee; font-weight: 500;
        }
        .heatmap-table td:first-child { text-align: left; }
        .heatmap-cell {
            padding: 8px 12px; border-radius: 6px;
            display: inline-block; min-width: 60px;
            color: white; text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }
        .heatmap-row:hover { background: #f5f7fa; }
        
        /* Attendance Alert Banner Styles */
        .alert-banner {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
            color: white; padding: 20px 25px; border-radius: 10px;
            margin-bottom: 20px; box-shadow: 0 4px 15px rgba(238, 90, 90, 0.3);
        }
        .alert-banner h3 { margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        .alert-banner .alert-count {
            background: white; color: #e74c3c; padding: 4px 12px;
            border-radius: 20px; font-size: 14px; font-weight: bold;
        }
        .alert-banner ul { list-style: none; padding: 0; margin: 0; }
        .alert-banner li {
            padding: 10px 15px; background: rgba(255,255,255,0.15);
            border-radius: 6px; margin-bottom: 8px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .alert-banner li:last-child { margin-bottom: 0; }
        .alert-banner .student-info { font-weight: 500; }
        .alert-banner .attendance-rate {
            background: rgba(255,255,255,0.25); padding: 4px 10px;
            border-radius: 4px; font-weight: bold;
        }
        .alert-banner.no-alerts {
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            box-shadow: 0 4px 15px rgba(46, 204, 113, 0.3);
        }
    </style>
</head>
<body>
    <!-- Login Section -->
    <div class="login-container" id="loginSection">
        <div class="login-box">
            <h2>🎓 Student Wellbeing</h2>
            <div class="error" id="loginError"></div>
            <input type="text" id="username" placeholder="Username">
            <input type="password" id="password" placeholder="Password">
            <button onclick="login()">Login</button>
            <p style="margin-top:20px; font-size:12px; color:#666; text-align:center;">
                <strong>Wellbeing Officers:</strong> kayla, abigail, john<br>
                <strong>Course Lead:</strong> courselead<br>
                <small>(passwords: [name]123 or lead123)</small>
            </p>
        </div>
    </div>
    
    <!-- Dashboard Section -->
    <div class="dashboard" id="dashboard">
        <div class="header">
            <h1>🎓 Student Wellbeing Dashboard</h1>
            <div class="user-info">
                <span>Welcome, <strong id="userName"></strong> (<span id="userRole"></span>)</span>
                <button class="logout-btn" onclick="logout()">Logout</button>
            </div>
        </div>
        
        <div class="nav-tabs">
            <button class="nav-tab active" data-tab="overview" onclick="showTab('overview')">📊 Overview</button>
            <button class="nav-tab" data-tab="notifications" onclick="showTab('notifications')">🔔 Notifications</button>
            <button class="nav-tab" data-tab="stress" id="stressTab" onclick="showTab('stress')">😰 Stress Levels</button>
            <button class="nav-tab" data-tab="attendance" id="attendanceTab" onclick="showTab('attendance')">📋 Attendance</button>
            <button class="nav-tab" data-tab="correlation" id="correlationTab" onclick="showTab('correlation')">📈 Correlation</button>
            <button class="nav-tab" data-tab="admin" id="adminTab" onclick="showTab('admin')">⚙️ Admin</button>
        </div>
        
        <div class="content">
            <!-- Overview Tab -->
            <div class="tab-content active" id="overview">
                <div class="cards" id="overviewCards"></div>
                <div class="chart-container">
                    <h3>Quick Summary</h3>
                    <div id="quickSummary"></div>
                </div>
            </div>
            
            <!-- Notifications Tab -->
            <div class="tab-content" id="notifications">
                <div class="cards" id="notificationCards"></div>
                
                <!-- Sleep Alerts Section (for Wellbeing Officers) -->
                <div class="alert-banner" id="sleepAlertBanner" style="display:none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                    <h3>😴 Low Sleep Alert <span class="alert-count" id="lowSleepCount">0</span></h3>
                    <p style="margin-bottom:15px; opacity:0.9;">The following students have low sleep (≤7 hours) and may need support:</p>
                    <ul id="lowSleepList" style="list-style: none; padding: 0;"></ul>
                </div>
                
                <!-- Stress Alerts Section (for Wellbeing Officers) -->
                <div class="alert-banner" id="stressAlertBanner" style="display:none; background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);">
                    <h3>⚠️ High Stress Alert <span class="alert-count" id="highStressCount">0</span></h3>
                    <p style="margin-bottom:15px; opacity:0.9;">The following students have high stress levels and may need intervention:</p>
                    <ul id="highStressList" style="list-style: none; padding: 0;"></ul>
                </div>
                
                <div class="table-container">
                    <h3>🔔 All Active Alerts</h3>
                    <div class="alert-list" id="alertList"></div>
                </div>
            </div>
            
            <!-- Stress Tab -->
            <div class="tab-content" id="stress">
                <div class="cards" id="stressCards"></div>
                
                <!-- Stress Heatmap -->
                <div class="heatmap-container">
                    <h3>🔥 Stress Levels Heatmap</h3>
                    <div class="heatmap-legend">
                        <span>Low Risk</span>
                        <div class="legend-gradient"></div>
                        <span>High Risk</span>
                    </div>
                    <table class="heatmap-table" id="stressHeatmap">
                        <thead>
                            <tr>
                                <th>Student</th>
                                <th>Stress Level</th>
                                <th>Study Time (hrs)</th>
                                <th>Entertainment (hrs)</th>
                                <th>Sleep Concern</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
                
                <div class="chart-container">
                    <h3>📊 Stress Level Distribution</h3>
                    <canvas id="stressChart"></canvas>
                </div>
                <div class="table-container">
                    <h3>🚨 High Stress Students</h3>
                    <table id="stressTable">
                        <thead><tr><th>Student Name</th><th>ID</th><th>Stress Level</th></tr></thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
            
            <!-- Attendance Tab -->
            <div class="tab-content" id="attendance">
                <!-- Low Attendance Alert Banner -->
                <div class="alert-banner" id="attendanceAlertBanner" style="display:none;">
                    <h3>⚠️ Low Attendance Alert <span class="alert-count" id="lowAttendanceCount">0</span></h3>
                    <p style="margin-bottom:15px; opacity:0.9;">The following students have attendance below 70% and may need support:</p>
                    <ul id="lowAttendanceList"></ul>
                </div>
                
                <div class="cards" id="attendanceCards"></div>
                <div class="chart-container">
                    <h3>📅 Weekly Attendance Trend</h3>
                    <canvas id="attendanceChart"></canvas>
                </div>
                <div class="table-container">
                    <h3>❌ Absent Students</h3>
                    <table id="absentTable">
                        <thead><tr><th>Student Name</th><th>ID</th><th>Absences</th><th>Absence Rate</th></tr></thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
            
            <!-- Correlation Tab -->
            <div class="tab-content" id="correlation">
                <div class="correlation-box">
                    <h3>📈 Attendance vs Assignment Grades Correlation</h3>
                    <div class="correlation-value" id="correlationValue">--</div>
                    <p class="interpretation" id="correlationInterpretation"></p>
                </div>
                <div class="chart-container">
                    <h3>Attendance Category Analysis</h3>
                    <canvas id="correlationChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>📊 Grade Distribution by Submission Week</h3>
                    <canvas id="gradeDistributionChart"></canvas>
                </div>
                
                <!-- Matplotlib Charts from funcd.py -->
                <h2 style="margin-top: 30px; color: #667eea;">📈 Detailed Analytics Charts</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; margin-top: 20px;">
                    <div class="chart-container">
                        <h3>📊 Assignment Grade Distribution</h3>
                        <img id="chartAssignmentGrades" alt="Assignment Grades Chart" style="max-width:100%; height:auto; border-radius:8px;">
                    </div>
                    <div class="chart-container">
                        <h3>📅 Assignment Submissions by Week</h3>
                        <img id="chartAssignmentSubmissions" alt="Assignment Submissions Chart" style="max-width:100%; height:auto; border-radius:8px;">
                    </div>
                    <div class="chart-container">
                        <h3>📊 Assessment Grade Distribution</h3>
                        <img id="chartAssessmentGrades" alt="Assessment Grades Chart" style="max-width:100%; height:auto; border-radius:8px;">
                    </div>
                    <div class="chart-container">
                        <h3>📉 Attendance vs Assessment Correlation</h3>
                        <img id="chartAttendanceAssessment" alt="Attendance vs Assessment Chart" style="max-width:100%; height:auto; border-radius:8px;">
                    </div>
                </div>
                
                <div class="table-container">
                    <h3>Student Performance Data</h3>
                    <table id="correlationTable">
                        <thead><tr><th>Student</th><th>Attendance %</th><th>Avg Assignment</th><th>Assessment</th></tr></thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
            
            <!-- Admin Tab -->
            <div class="tab-content" id="admin">
                <div class="admin-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                    <h2 style="color:#667eea;">👥 Student Management</h2>
                    <button onclick="showAddStudentModal()" style="background:#27ae60; color:white; padding:12px 24px; border:none; border-radius:5px; cursor:pointer; font-size:14px;">
                        ➕ Add New Student
                    </button>
                </div>
                
                <div class="table-container">
                    <table id="adminStudentsTable">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Gender</th>
                                <th>Attendance %</th>
                                <th>Assessment Grade</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Add/Edit Student Modal -->
    <div id="studentModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000; justify-content:center; align-items:center;">
        <div style="background:white; padding:30px; border-radius:10px; width:450px; max-width:90%;">
            <h3 id="modalTitle" style="margin-bottom:20px; color:#333;">Add New Student</h3>
            <input type="hidden" id="editStudentId">
            <div style="margin-bottom:15px;">
                <label style="display:block; margin-bottom:5px; font-weight:600;">Student Name *</label>
                <input type="text" id="studentName" placeholder="Enter student name" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
            </div>
            <div style="margin-bottom:15px;">
                <label style="display:block; margin-bottom:5px; font-weight:600;">Gender</label>
                <select id="studentGender" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
                    <option value="">Select Gender</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                </select>
            </div>
            <div id="editOnlyFields" style="display:none;">
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:600;">Study Time (hours/day)</label>
                    <input type="number" id="studyTime" placeholder="5" min="0" max="24" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
                </div>
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:600;">Entertainment Time (hours/day)</label>
                    <input type="number" id="entertainmentTime" placeholder="3" min="0" max="24" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
                </div>
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:600;">Sleep Time (hours/day)</label>
                    <input type="number" id="sleepTime" placeholder="7" min="0" max="24" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
                </div>
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:600;">Assessment Grade</label>
                    <input type="number" id="assessmentGrade" placeholder="70" min="0" max="100" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
                </div>
            </div>
            <div style="display:flex; gap:10px; justify-content:flex-end; margin-top:20px;">
                <button onclick="closeModal()" style="padding:10px 20px; border:1px solid #ddd; background:white; border-radius:5px; cursor:pointer;">Cancel</button>
                <button onclick="saveStudent()" style="padding:10px 20px; background:#667eea; color:white; border:none; border-radius:5px; cursor:pointer;">Save</button>
            </div>
        </div>
    </div>
    
    <!-- Delete Confirmation Modal -->
    <div id="deleteModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000; justify-content:center; align-items:center;">
        <div style="background:white; padding:30px; border-radius:10px; width:400px; max-width:90%; text-align:center;">
            <h3 style="margin-bottom:15px; color:#e74c3c;">⚠️ Confirm Delete</h3>
            <p id="deleteMessage" style="margin-bottom:20px; color:#666;">Are you sure you want to delete this student?</p>
            <input type="hidden" id="deleteStudentId">
            <div style="display:flex; gap:10px; justify-content:center;">
                <button onclick="closeDeleteModal()" style="padding:10px 20px; border:1px solid #ddd; background:white; border-radius:5px; cursor:pointer;">Cancel</button>
                <button onclick="confirmDelete()" style="padding:10px 20px; background:#e74c3c; color:white; border:none; border-radius:5px; cursor:pointer;">Delete</button>
            </div>
        </div>
    </div>
    
    <script>
        let token = '';
        let user = null;
        let charts = {};
        
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await response.json();
                
                if (data.success) {
                    token = data.token;
                    user = data.user;
                    showDashboard();
                } else {
                    document.getElementById('loginError').textContent = data.error;
                }
            } catch (error) {
                document.getElementById('loginError').textContent = 'Connection error';
            }
        }
        
        function logout() {
            token = '';
            user = null;
            document.getElementById('loginSection').style.display = 'flex';
            document.getElementById('dashboard').style.display = 'none';
        }
        
        function showDashboard() {
            document.getElementById('loginSection').style.display = 'none';
            document.getElementById('dashboard').style.display = 'block';
            document.getElementById('userName').textContent = user.name;
            document.getElementById('userRole').textContent = user.role.replace('_', ' ');
            
            // Configure tabs based on role
            const stressTab = document.getElementById('stressTab');
            const attendanceTab = document.getElementById('attendanceTab');
            const correlationTab = document.getElementById('correlationTab');
            const adminTab = document.getElementById('adminTab');
            
            // Hide admin tab for non-admin users
            if (user.role !== 'admin') {
                adminTab.style.display = 'none';
            }
            
            if (user.role === 'wellbeing_officer') {
                attendanceTab.classList.add('disabled');
                correlationTab.classList.add('disabled');
                // Wellbeing officers see Overview tab first (which shows stress summary)
                // They can also access the full Stress tab for detailed view
                showTab('overview');
            } else if (user.role === 'course_lead') {
                stressTab.classList.add('disabled');
                // Course lead can see attendance and correlation tabs
                // Auto-switch to attendance tab for course lead
                showTab('attendance');
            } else if (user.role === 'admin') {
                // Admin can see all tabs, auto-switch to admin tab
                showTab('admin');
            }
            
            loadData();
        }
        
        function showTab(tabName) {
            const tab = document.querySelector(`[data-tab="${tabName}"]`);
            if (tab.classList.contains('disabled')) return;
            
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            tab.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }
        
        async function fetchAPI(endpoint) {
            const response = await fetch(`/api/${endpoint}?token=${token}`);
            return response.json();
        }
        
        async function loadData() {
            // Load notifications
            loadNotifications();
            
            // Load role-specific data
            if (user.role === 'wellbeing_officer' || user.role === 'admin') {
                loadStressData();
            }
            if (user.role === 'course_lead' || user.role === 'admin') {
                loadAttendanceData();
                loadCorrelationData();
            }
            if (user.role === 'admin') {
                loadAdminData();
            }
            
            loadOverview();
        }
        
        async function loadOverview() {
            const summary = await fetchAPI('notification-summary');
            if (summary.success) {
                const s = summary.summary;
                document.getElementById('overviewCards').innerHTML = `
                    <div class="card">
                        <h3>Total Alerts</h3>
                        <div class="value ${s.high_severity > 0 ? 'warning' : ''}">${s.total}</div>
                    </div>
                    <div class="card">
                        <h3>High Severity</h3>
                        <div class="value warning">${s.high_severity}</div>
                    </div>
                    <div class="card">
                        <h3>Wellbeing Alerts</h3>
                        <div class="value">${s.by_category.wellbeing}</div>
                    </div>
                    <div class="card">
                        <h3>Attendance Alerts</h3>
                        <div class="value">${s.by_category.attendance}</div>
                    </div>
                `;
            }
            
            // Show stress levels summary for wellbeing officers (always visible)
            if (user.role === 'wellbeing_officer' || user.role === 'admin') {
                const stressData = await fetchAPI('stress-visualization');
                const sleepData = await fetchAPI('sleep-alerts');
                
                if (stressData.success) {
                    const stats = stressData.data.statistics;
                    const chartData = stressData.data.chart_data;
                    
                    // Find top 5 highest stress students
                    const stressStudents = chartData.students.map((name, i) => ({
                        name: name,
                        stress: chartData.stress_levels[i]
                    })).sort((a, b) => b.stress - a.stress).slice(0, 5);
                    
                    // Get sleep alerts count
                    const sleepAlertCount = sleepData.success ? sleepData.count : 0;
                    const sleepAlerts = sleepData.success ? sleepData.alerts.slice(0, 5) : [];
                    
                    document.getElementById('quickSummary').innerHTML = `
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                            <div class="card" style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white;">
                                <h3 style="color: white;">⚠️ Stress Level Summary</h3>
                                <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                                    <div style="text-align: center;">
                                        <div style="font-size: 2.5em; font-weight: bold;">${stats.average_stress}</div>
                                        <div style="opacity: 0.8;">Avg Stress</div>
                                    </div>
                                    <div style="text-align: center;">
                                        <div style="font-size: 2.5em; font-weight: bold; color: #ffeb3b;">${stats.high_stress_count}</div>
                                        <div style="opacity: 0.8;">High Stress</div>
                                    </div>
                                    <div style="text-align: center;">
                                        <div style="font-size: 2.5em; font-weight: bold;">${stats.total_students}</div>
                                        <div style="opacity: 0.8;">Total Students</div>
                                    </div>
                                </div>
                            </div>
                            <div class="card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                <h3 style="color: white;">😴 Sleep Alert Summary</h3>
                                <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                                    <div style="text-align: center;">
                                        <div style="font-size: 2.5em; font-weight: bold; color: ${sleepAlertCount > 0 ? '#ffeb3b' : 'white'};">${sleepAlertCount}</div>
                                        <div style="opacity: 0.8;">Low Sleep Students</div>
                                    </div>
                                    <div style="text-align: center;">
                                        <div style="font-size: 2.5em; font-weight: bold;">≤7h</div>
                                        <div style="opacity: 0.8;">Threshold</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                            <div class="card">
                                <h3>🚨 Top 5 High Stress Students</h3>
                                <table style="width: 100%; margin-top: 10px;">
                                    <thead><tr><th style="text-align: left;">Student</th><th style="text-align: right;">Stress Level</th></tr></thead>
                                    <tbody>
                                        ${stressStudents.map(s => `
                                            <tr>
                                                <td>${s.name}</td>
                                                <td style="text-align: right; color: ${s.stress > 3 ? '#e74c3c' : s.stress > 2 ? '#f39c12' : '#27ae60'}; font-weight: bold;">
                                                    ${s.stress.toFixed(2)}
                                                </td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                            <div class="card">
                                <h3>😴 Students with Low Sleep</h3>
                                <table style="width: 100%; margin-top: 10px;">
                                    <thead><tr><th style="text-align: left;">Student</th><th style="text-align: right;">Sleep Hours</th></tr></thead>
                                    <tbody>
                                        ${sleepAlerts.length > 0 ? sleepAlerts.map(s => `
                                            <tr>
                                                <td>${s.student_name}</td>
                                                <td style="text-align: right; color: ${s.value < 6 ? '#e74c3c' : '#f39c12'}; font-weight: bold;">
                                                    ${s.value} hours
                                                </td>
                                            </tr>
                                        `).join('') : '<tr><td colspan="2" style="text-align: center; color: #27ae60;">No low sleep alerts ✓</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                }
            }
        }
        
        async function loadNotifications() {
            const data = await fetchAPI('notifications');
            if (data.success) {
                // Count by type
                const sleepAlerts = data.notifications.filter(n => n.type === 'LOW_SLEEP');
                const stressAlerts = data.notifications.filter(n => n.type === 'HIGH_STRESS');
                
                document.getElementById('notificationCards').innerHTML = `
                    <div class="card">
                        <h3>Total Alerts</h3>
                        <div class="value">${data.count}</div>
                    </div>
                    <div class="card">
                        <h3>😴 Sleep Alerts</h3>
                        <div class="value ${sleepAlerts.length > 0 ? 'warning' : ''}">${sleepAlerts.length}</div>
                    </div>
                    <div class="card">
                        <h3>⚠️ Stress Alerts</h3>
                        <div class="value ${stressAlerts.length > 0 ? 'warning' : ''}">${stressAlerts.length}</div>
                    </div>
                `;
                
                // Show sleep alerts banner for wellbeing officers
                if ((user.role === 'wellbeing_officer' || user.role === 'admin') && sleepAlerts.length > 0) {
                    const sleepBanner = document.getElementById('sleepAlertBanner');
                    sleepBanner.style.display = 'block';
                    document.getElementById('lowSleepCount').textContent = sleepAlerts.length + ' students';
                    document.getElementById('lowSleepList').innerHTML = sleepAlerts.map(a => `
                        <li style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.2);">
                            <span style="font-weight: bold;">👤 ${a.student_name}</span> (ID: ${a.student_id})
                            <span style="float: right; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">
                                ${a.value} hours sleep
                            </span>
                        </li>
                    `).join('');
                }
                
                // Show stress alerts banner for wellbeing officers
                if ((user.role === 'wellbeing_officer' || user.role === 'admin') && stressAlerts.length > 0) {
                    const stressBanner = document.getElementById('stressAlertBanner');
                    stressBanner.style.display = 'block';
                    document.getElementById('highStressCount').textContent = stressAlerts.length + ' students';
                    document.getElementById('highStressList').innerHTML = stressAlerts.map(a => `
                        <li style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.2);">
                            <span style="font-weight: bold;">👤 ${a.student_name}</span> (ID: ${a.student_id})
                            <span style="float: right; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">
                                Stress: ${a.value}
                            </span>
                        </li>
                    `).join('');
                }
                
                const alertList = document.getElementById('alertList');
                alertList.innerHTML = data.notifications.map(n => `
                    <div class="alert-item">
                        <span class="alert-badge ${n.severity}">${n.severity.toUpperCase()}</span>
                        <span>${n.message}</span>
                    </div>
                `).join('');
            }
        }
        
        // Helper function to get heatmap color based on normalized value
        function getHeatmapColor(value) {
            // Gradient from green (0) -> yellow (0.5) -> red (1)
            if (value <= 0.5) {
                const ratio = value * 2;
                const r = Math.round(39 + (243 - 39) * ratio);
                const g = Math.round(174 + (156 - 174) * ratio);
                const b = Math.round(96 + (18 - 96) * ratio);
                return `rgb(${r}, ${g}, ${b})`;
            } else {
                const ratio = (value - 0.5) * 2;
                const r = Math.round(243 + (231 - 243) * ratio);
                const g = Math.round(156 + (76 - 156) * ratio);
                const b = Math.round(18 + (60 - 18) * ratio);
                return `rgb(${r}, ${g}, ${b})`;
            }
        }
        
        async function loadStressData() {
            const data = await fetchAPI('stress-visualization');
            if (data.success) {
                const stats = data.data.statistics;
                document.getElementById('stressCards').innerHTML = `
                    <div class="card">
                        <h3>Average Stress Level</h3>
                        <div class="value">${stats.average_stress}</div>
                    </div>
                    <div class="card">
                        <h3>High Stress Students</h3>
                        <div class="value warning">${stats.high_stress_count}</div>
                    </div>
                    <div class="card">
                        <h3>Total Students</h3>
                        <div class="value">${stats.total_students}</div>
                    </div>
                `;
                
                // Create stress chart
                const ctx = document.getElementById('stressChart').getContext('2d');
                if (charts.stress) charts.stress.destroy();
                charts.stress = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.data.chart_data.students,
                        datasets: [{
                            label: 'Stress Level',
                            data: data.data.chart_data.stress_levels,
                            backgroundColor: data.data.chart_data.stress_levels.map(v => 
                                v > 3 ? '#e74c3c' : v > 2 ? '#f39c12' : '#27ae60'
                            )
                        }]
                    },
                    options: { responsive: true }
                });
            }
            
            // Load heatmap data
            const heatmapData = await fetchAPI('stress-heatmap');
            if (heatmapData.success) {
                const tbody = document.querySelector('#stressHeatmap tbody');
                tbody.innerHTML = heatmapData.data.map(s => `
                    <tr class="heatmap-row">
                        <td><strong>${s.student_name}</strong><br><small style="color:#888">ID: ${s.student_id}</small></td>
                        <td><span class="heatmap-cell" style="background:${getHeatmapColor(s.stress_normalized)}">${s.stress_level}</span></td>
                        <td><span class="heatmap-cell" style="background:${getHeatmapColor(s.study_normalized)}">${s.study_time}h</span></td>
                        <td><span class="heatmap-cell" style="background:${getHeatmapColor(s.entertainment_normalized)}">${s.entertainment_time}h</span></td>
                        <td><span class="heatmap-cell" style="background:${getHeatmapColor(s.sleep_normalized)}">${s.sleep_time}h</span></td>
                    </tr>
                `).join('');
            }
            
            // Load high stress table
            const highStress = await fetchAPI('high-stress-students');
            if (highStress.success) {
                const tbody = document.querySelector('#stressTable tbody');
                tbody.innerHTML = highStress.data.map(s => `
                    <tr>
                        <td>${s.Student_Name}</td>
                        <td>${s.Student_ID}</td>
                        <td style="color:#e74c3c;font-weight:bold">${s.stress_level.toFixed(2)}</td>
                    </tr>
                `).join('');
            }
        }
        
        async function loadAttendanceData() {
            // Load attendance alerts first
            const alertsData = await fetchAPI('attendance-alerts');
            if (alertsData.success && alertsData.alerts.length > 0) {
                const banner = document.getElementById('attendanceAlertBanner');
                banner.style.display = 'block';
                document.getElementById('lowAttendanceCount').textContent = alertsData.alerts.length + ' students';
                document.getElementById('lowAttendanceList').innerHTML = alertsData.alerts.map(a => `
                    <li>
                        <span class="student-info">👤 ${a.student_name} (ID: ${a.student_id})</span>
                        <span class="attendance-rate">${a.value}% attendance (${a.classes_attended}/${a.total_classes} classes)</span>
                    </li>
                `).join('');
            } else {
                const banner = document.getElementById('attendanceAlertBanner');
                banner.style.display = 'block';
                banner.className = 'alert-banner no-alerts';
                banner.innerHTML = '<h3>✅ All Students Meeting Attendance Requirements</h3><p>No students have attendance below 70%. Great job!</p>';
            }
            
            const data = await fetchAPI('participation');
            if (data.success) {
                const overall = data.data.overall;
                document.getElementById('attendanceCards').innerHTML = `
                    <div class="card">
                        <h3>Overall Attendance Rate</h3>
                        <div class="value ${overall.overall_attendance_rate < 70 ? 'warning' : 'success'}">${overall.overall_attendance_rate}%</div>
                    </div>
                    <div class="card">
                        <h3>Total Students</h3>
                        <div class="value">${overall.total_students}</div>
                    </div>
                    <div class="card">
                        <h3>Total Classes</h3>
                        <div class="value">${overall.total_classes}</div>
                    </div>
                `;
                
                // Create attendance chart
                const ctx = document.getElementById('attendanceChart').getContext('2d');
                if (charts.attendance) charts.attendance.destroy();
                charts.attendance = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.data.weekly_trend.weeks.map(w => 'Week ' + w),
                        datasets: [{
                            label: 'Attendance Rate %',
                            data: data.data.weekly_trend.attendance_rates,
                            borderColor: '#667eea',
                            tension: 0.1,
                            fill: false
                        }]
                    },
                    options: { responsive: true }
                });
            }
            
            // Load absent students
            const absent = await fetchAPI('absent-students');
            if (absent.success) {
                const tbody = document.querySelector('#absentTable tbody');
                tbody.innerHTML = absent.data.map(s => `
                    <tr>
                        <td>${s.Student_Name}</td>
                        <td>${s.Student_ID}</td>
                        <td>${s.Absences}</td>
                        <td style="color:${s.Absence_Rate > 30 ? '#e74c3c' : '#f39c12'}">${s.Absence_Rate}%</td>
                    </tr>
                `).join('');
            }
        }
        
        async function loadCorrelationData() {
            const data = await fetchAPI('correlation');
            if (data.success) {
                const corr = data.data.correlation.attendance_vs_assignment;
                const corrEl = document.getElementById('correlationValue');
                corrEl.textContent = corr.toFixed(3);
                corrEl.className = 'correlation-value ' + (corr > 0 ? 'positive' : 'negative');
                document.getElementById('correlationInterpretation').textContent = data.data.interpretation;
                
                // Create correlation chart
                const ctx = document.getElementById('correlationChart').getContext('2d');
                if (charts.correlation) charts.correlation.destroy();
                charts.correlation = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.data.category_analysis.map(c => c.Attendance_Category),
                        datasets: [{
                            label: 'Avg Assignment Grade',
                            data: data.data.category_analysis.map(c => c.Avg_Assignment_Grade),
                            backgroundColor: '#667eea'
                        }]
                    },
                    options: { responsive: true }
                });
                
                // Load correlation table
                const tbody = document.querySelector('#correlationTable tbody');
                tbody.innerHTML = data.data.student_data.map(s => `
                    <tr>
                        <td>${s.Student_Name}</td>
                        <td>${s.Attendance_Rate.toFixed(1)}%</td>
                        <td>${s.Avg_Assignment_Grade}</td>
                        <td>${s.Assessment_Grade}</td>
                    </tr>
                `).join('');
            }
            
            // Load grade distribution by week
            const gradeData = await fetchAPI('grade-distribution');
            if (gradeData.success) {
                const ctx2 = document.getElementById('gradeDistributionChart').getContext('2d');
                if (charts.gradeDistribution) charts.gradeDistribution.destroy();
                
                const dist = gradeData.data.grade_distribution;
                const colors = [
                    'rgba(231, 76, 60, 0.8)',    // 0-50 (red)
                    'rgba(243, 156, 18, 0.8)',   // 50-60 (orange)
                    'rgba(241, 196, 15, 0.8)',   // 60-70 (yellow)
                    'rgba(46, 204, 113, 0.8)',   // 70-80 (green)
                    'rgba(52, 152, 219, 0.8)',   // 80-90 (blue)
                    'rgba(155, 89, 182, 0.8)'    // 90-100 (purple)
                ];
                
                const datasets = dist.ranges.map((range, i) => ({
                    label: range,
                    data: dist.data[range],
                    backgroundColor: colors[i]
                }));
                
                charts.gradeDistribution = new Chart(ctx2, {
                    type: 'bar',
                    data: {
                        labels: dist.weeks.map(w => w.charAt(0).toUpperCase() + w.slice(1)),
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Grade Distribution by Submission Week (Total: ' + gradeData.data.summary.total_assignments + ' assignments, Avg: ' + gradeData.data.summary.overall_avg + ')'
                            },
                            legend: { position: 'top' }
                        },
                        scales: {
                            x: { stacked: true, title: { display: true, text: 'Submission Week' } },
                            y: { stacked: true, title: { display: true, text: 'Number of Assignments' } }
                        }
                    }
                });
            }
            
            // Load matplotlib chart images from funcd.py
            loadChartImages();
        }
        
        function loadChartImages() {
            // Add timestamp to prevent caching
            const ts = new Date().getTime();
            
            // Assignment Grade Distribution Chart
            document.getElementById('chartAssignmentGrades').src = '/api/chart/assignment-grades?token=' + token + '&t=' + ts;
            
            // Assignment Submissions by Week Chart
            document.getElementById('chartAssignmentSubmissions').src = '/api/chart/assignment-submissions?token=' + token + '&t=' + ts;
            
            // Assessment Grade Distribution Chart
            document.getElementById('chartAssessmentGrades').src = '/api/chart/assessment-grades?token=' + token + '&t=' + ts;
            
            // Attendance vs Assessment Scatter Plot
            document.getElementById('chartAttendanceAssessment').src = '/api/chart/attendance-vs-assessment?token=' + token + '&t=' + ts;
        }
        
        // ==================== ADMIN FUNCTIONS ====================
        
        async function loadAdminData() {
            const response = await fetch(`/api/admin/students?token=${token}`);
            const data = await response.json();
            
            if (data.success) {
                const tbody = document.querySelector('#adminStudentsTable tbody');
                tbody.innerHTML = data.students.map(s => `
                    <tr>
                        <td>${s.Student_ID}</td>
                        <td>${s.Student_Name}</td>
                        <td>${s.Gender || '-'}</td>
                        <td>${s.Attendance_Rate ? s.Attendance_Rate.toFixed(1) + '%' : '-'}</td>
                        <td>${s.Assessment_Grade || '-'}</td>
                        <td>
                            <button onclick="editStudent(${s.Student_ID})" style="background:#3498db; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; margin-right:5px;">✏️ Edit</button>
                            <button onclick="deleteStudent(${s.Student_ID}, '${s.Student_Name}')" style="background:#e74c3c; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">🗑️ Delete</button>
                        </td>
                    </tr>
                `).join('');
            }
        }
        
        function showAddStudentModal() {
            document.getElementById('modalTitle').textContent = 'Add New Student';
            document.getElementById('editStudentId').value = '';
            document.getElementById('studentName').value = '';
            document.getElementById('studentGender').value = '';
            document.getElementById('editOnlyFields').style.display = 'none';
            document.getElementById('studentModal').style.display = 'flex';
        }
        
        async function editStudent(studentId) {
            const response = await fetch(`/api/admin/students/${studentId}?token=${token}`);
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('modalTitle').textContent = 'Edit Student';
                document.getElementById('editStudentId').value = studentId;
                document.getElementById('studentName').value = data.student.Student_Name || '';
                document.getElementById('studentGender').value = data.student.Gender || '';
                document.getElementById('studyTime').value = data.survey.Study_Time || '';
                document.getElementById('entertainmentTime').value = data.survey.Entertainment_Time || '';
                document.getElementById('sleepTime').value = data.survey.Sleep_Time || '';
                document.getElementById('assessmentGrade').value = data.assessment.Assessment_Grade || '';
                document.getElementById('editOnlyFields').style.display = 'block';
                document.getElementById('studentModal').style.display = 'flex';
            } else {
                alert('Error loading student data: ' + data.error);
            }
        }
        
        function closeModal() {
            document.getElementById('studentModal').style.display = 'none';
        }
        
        async function saveStudent() {
            const studentId = document.getElementById('editStudentId').value;
            const studentName = document.getElementById('studentName').value.trim();
            const gender = document.getElementById('studentGender').value;
            
            if (!studentName) {
                alert('Student name is required');
                return;
            }
            
            let url, method, body;
            
            if (studentId) {
                // Update existing student
                url = `/api/admin/students/${studentId}?token=${token}`;
                method = 'PUT';
                body = {
                    student_name: studentName,
                    gender: gender,
                    study_time: parseInt(document.getElementById('studyTime').value) || null,
                    entertainment_time: parseInt(document.getElementById('entertainmentTime').value) || null,
                    sleep_time: parseInt(document.getElementById('sleepTime').value) || null,
                    assessment_grade: parseInt(document.getElementById('assessmentGrade').value) || null
                };
            } else {
                // Add new student
                url = `/api/admin/students?token=${token}`;
                method = 'POST';
                body = {
                    student_name: studentName,
                    gender: gender
                };
            }
            
            try {
                const response = await fetch(url, {
                    method: method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message);
                    closeModal();
                    loadAdminData();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error saving student: ' + error.message);
            }
        }
        
        function deleteStudent(studentId, studentName) {
            document.getElementById('deleteStudentId').value = studentId;
            document.getElementById('deleteMessage').textContent = `Are you sure you want to delete "${studentName}" (ID: ${studentId})? This will remove all their records including attendance, assignments, and assessments.`;
            document.getElementById('deleteModal').style.display = 'flex';
        }
        
        function closeDeleteModal() {
            document.getElementById('deleteModal').style.display = 'none';
        }
        
        async function confirmDelete() {
            const studentId = document.getElementById('deleteStudentId').value;
            
            try {
                const response = await fetch(`/api/admin/students/${studentId}?token=${token}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message);
                    closeDeleteModal();
                    loadAdminData();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error deleting student: ' + error.message);
            }
        }
        
        // Enter key to login
        document.getElementById('password').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') login();
        });
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    """Serve the main dashboard"""
    return render_template_string(DASHBOARD_HTML)

# Keep original endpoints for backward compatibility
@app.route('/get_stress_level_df', methods=['GET'])
def get_stress_level_df_legacy():
    stress_level_df = Stress_level_calculate(DATABASE_PATH)
    return jsonify({'stress_level_df': stress_level_df.to_json(orient='records')})

@app.route('/get_high_stress_df', methods=['GET'])
def get_high_stress_df_legacy():
    high_stress_df = filter_high_stress_students(DATABASE_PATH)
    return jsonify({'high_stress_df': high_stress_df.to_json(orient='records')})

# ==================== CHART IMAGE ENDPOINTS (from funcd.py) ====================

@app.route('/api/chart/assignment-grades', methods=['GET'])
@require_auth('view_attendance')
def api_chart_assignment_grades():
    """Get bar chart of assignment grade distribution as PNG image"""
    try:
        img = barchart_assi_grade(DATABASE_PATH)
        return send_file(img, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart/assignment-submissions', methods=['GET'])
@require_auth('view_attendance')
def api_chart_assignment_submissions():
    """Get bar chart of assignment submission times by week as PNG image"""
    try:
        img = barchart_assi_subt(DATABASE_PATH)
        return send_file(img, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart/assessment-grades', methods=['GET'])
@require_auth('view_attendance')
def api_chart_assessment_grades():
    """Get bar chart of assessment grade distribution as PNG image"""
    try:
        img = barchart_asse_grade(DATABASE_PATH)
        return send_file(img, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart/attendance-vs-assessment', methods=['GET'])
@require_auth('view_attendance')
def api_chart_attendance_vs_assessment():
    """Get scatter plot of attendance rate vs assessment grade as PNG image"""
    try:
        img = plot_asse_att(DATABASE_PATH)
        return send_file(img, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
