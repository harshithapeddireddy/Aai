from flask import Flask, request, jsonify, send_file
from funcsw import Stress_level_calculate, filter_high_stress_students, Stress_report
from funcd import (
    Attendance_rate_calculate, 
    Students_grades, 
    barchart_assi_grade, 
    barchart_assi_subt, 
    barchart_asse_grade, 
    plot_asse_att
)
import sqlite3
import pandas as pd

app = Flask(__name__)

# Database paths
DATABASE_PATH = 'user_data.db'
detabase_path = 'Student_wellbeing.db'

# ==================== USER MANAGEMENT ENDPOINTS ====================

@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # 使用 pandas 读取所有用户信息
        query = "SELECT user_id, password FROM Users"
        df = pd.read_sql_query(query, conn)

        # 将结果转换为列表形式
        users = df.to_dict(orient='records')

        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# 添加新用户
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json
    user_id = data.get('user_id')
    password = data.get('password')

    if not user_id or not password:
        return jsonify({"error": "User ID and password are required"}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO Users (user_id, password) VALUES (?, ?)', (user_id, password))
        conn.commit()
        return jsonify({"message": "User added successfully"}), 200
    except sqlite3.IntegrityError:
        return jsonify({"error": "User ID already exists"}), 400
    finally:
        conn.close()

# 更新用户ID
@app.route('/update_user_id', methods=['POST'])
def update_user_id():
    data = request.json
    current_user_id = data.get('current_user_id')
    new_user_id = data.get('new_user_id')
    password = data.get('password')

    if not current_user_id or not new_user_id or not password:
        return jsonify({"error": "Current User ID, new User ID, and password are required"}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT password FROM Users WHERE user_id = ?', (current_user_id,))
        user = cursor.fetchone()

        if user and user[0] == password:
            try:
                cursor.execute('UPDATE Users SET user_id = ? WHERE user_id = ?', (new_user_id, current_user_id))
                conn.commit()
                return jsonify({"message": "User ID updated successfully"}), 200
            except sqlite3.IntegrityError:
                return jsonify({"error": "New User ID already exists"}), 400
        else:
            return jsonify({"error": "Invalid current User ID or password"}), 401
    finally:
        conn.close()

# 更新用户密码
@app.route('/update_password', methods=['POST'])
def update_password():
    data = request.json
    user_id = data.get('user_id')
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not user_id or not current_password or not new_password:
        return jsonify({"error": "User ID, current password, and new password are required"}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT password FROM Users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()

        if user and user[0] == current_password:
            cursor.execute('UPDATE Users SET password = ? WHERE user_id = ?', (new_password, user_id))
            conn.commit()
            return jsonify({"message": "Password updated successfully"}), 200
        else:
            return jsonify({"error": "Invalid User ID or current password"}), 401
    finally:
        conn.close()


@app.route('/get_stress_level_df', methods=['GET'])
def get_stress_level_df():
    # 获取 stress_level_df
    stress_level_df = Stress_level_calculate(detabase_path)
    # 将 DataFrame 转换为 JSON 格式
    stress_level_json = stress_level_df.to_json(orient='records')
    return jsonify({'stress_level_df': stress_level_json})

@app.route('/get_high_stress_df', methods=['GET'])
def get_high_stress_df():
    # 获取 high_stress_df
    high_stress_df = filter_high_stress_students(detabase_path)
    # 将 DataFrame 转换为 JSON 格式
    high_stress_json = high_stress_df.to_json(orient='records')
    return jsonify({'high_stress_df': high_stress_json})

@app.route('/get_report', methods=['GET'])
def get_report():
    # 获取请求参数
    student_id = request.args.get('student_id')
    student_name = request.args.get('student_name')

    if student_id:
        report = Stress_report(detabase_path, int(student_id))
    elif student_name:
        # 查询学生ID
        conn = sqlite3.connect(detabase_path)
        query = "SELECT Student_ID FROM Students WHERE Student_Name = ?"
        result = pd.read_sql_query(query, conn, params=[student_name])
        conn.close()
        if result.empty:
            return jsonify({'error': f"No data found for Student Name: {student_name}"})
        student_id = result['Student_ID'].values[0]
        report = Stress_report(detabase_path, student_id)
    else:
        return jsonify({'error': 'Either student_id or student_name must be provided'})

    return jsonify({'report': report})

# ==================== ATTENDANCE ENDPOINTS (from funcd.py) ====================

@app.route('/get_attendance_rate', methods=['GET'])
def get_attendance_rate():
    """Get attendance rate for all students"""
    try:
        attendance_df = Attendance_rate_calculate(detabase_path)
        attendance_json = attendance_df.to_json(orient='records')
        return jsonify({'attendance_rate_df': attendance_json})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_student_attendance', methods=['GET'])
def get_student_attendance():
    """Get attendance rate for a specific student by ID or name"""
    student_id = request.args.get('student_id')
    student_name = request.args.get('student_name')
    
    try:
        attendance_df = Attendance_rate_calculate(detabase_path)
        
        if student_id:
            result = attendance_df[attendance_df['Student_ID'] == int(student_id)]
        elif student_name:
            result = attendance_df[attendance_df['Student_Name'].str.lower() == student_name.lower()]
        else:
            return jsonify({'error': 'Either student_id or student_name must be provided'}), 400
        
        if result.empty:
            return jsonify({'error': 'Student not found'}), 404
        
        return jsonify({'attendance': result.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== GRADES ENDPOINTS (from funcd.py) ====================

@app.route('/get_student_grades', methods=['GET'])
def get_student_grades():
    """Get all grades (Assignment 1, Assignment 2, Assessment) for all students"""
    try:
        grades_df = Students_grades(detabase_path)
        grades_json = grades_df.to_json(orient='records')
        return jsonify({'grades_df': grades_json})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_grades_by_student', methods=['GET'])
def get_grades_by_student():
    """Get grades for a specific student by ID or name"""
    student_id = request.args.get('student_id')
    student_name = request.args.get('student_name')
    
    try:
        grades_df = Students_grades(detabase_path)
        
        if student_id:
            result = grades_df[grades_df['Student_ID'] == int(student_id)]
        elif student_name:
            result = grades_df[grades_df['Student_Name'].str.lower() == student_name.lower()]
        else:
            return jsonify({'error': 'Either student_id or student_name must be provided'}), 400
        
        if result.empty:
            return jsonify({'error': 'Student not found'}), 404
        
        return jsonify({'grades': result.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== CHART ENDPOINTS (from funcd.py) ====================

@app.route('/chart/assignment_grades', methods=['GET'])
def chart_assignment_grades():
    """Get bar chart of assignment grade distribution"""
    try:
        img = barchart_assi_grade(detabase_path)
        return send_file(img, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chart/assignment_submissions', methods=['GET'])
def chart_assignment_submissions():
    """Get bar chart of assignment submission times by week"""
    try:
        img = barchart_assi_subt(detabase_path)
        return send_file(img, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chart/assessment_grades', methods=['GET'])
def chart_assessment_grades():
    """Get bar chart of assessment grade distribution"""
    try:
        img = barchart_asse_grade(detabase_path)
        return send_file(img, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chart/attendance_vs_assessment', methods=['GET'])
def chart_attendance_vs_assessment():
    """Get scatter plot of attendance rate vs assessment grade"""
    try:
        img = plot_asse_att(detabase_path)
        return send_file(img, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== COMBINED DATA ENDPOINTS ====================

@app.route('/get_student_overview', methods=['GET'])
def get_student_overview():
    """Get complete overview for a student including stress, attendance, and grades"""
    student_id = request.args.get('student_id')
    student_name = request.args.get('student_name')
    
    if not student_id and not student_name:
        return jsonify({'error': 'Either student_id or student_name must be provided'}), 400
    
    try:
        # If only name provided, get the ID first
        if not student_id and student_name:
            conn = sqlite3.connect(detabase_path)
            query = "SELECT Student_ID FROM Students WHERE Student_Name = ?"
            result = pd.read_sql_query(query, conn, params=[student_name])
            conn.close()
            if result.empty:
                return jsonify({'error': f"No data found for Student Name: {student_name}"}), 404
            student_id = int(result['Student_ID'].values[0])
        else:
            student_id = int(student_id)
        
        # Get stress data
        stress_df = Stress_level_calculate(detabase_path)
        stress_data = stress_df[stress_df['Student_ID'] == student_id]
        
        # Get attendance data
        attendance_df = Attendance_rate_calculate(detabase_path)
        attendance_data = attendance_df[attendance_df['Student_ID'] == student_id]
        
        # Get grades data
        grades_df = Students_grades(detabase_path)
        grades_data = grades_df[grades_df['Student_ID'] == student_id]
        
        # Get stress report
        report = Stress_report(detabase_path, student_id)
        
        if stress_data.empty:
            return jsonify({'error': 'Student not found'}), 404
        
        overview = {
            'student_id': student_id,
            'student_name': stress_data['Student_Name'].values[0],
            'stress': {
                'stress_level': int(stress_data['stress_level'].values[0]),
                'study_time': int(stress_data['Study_Time'].values[0]),
                'entertainment_time': int(stress_data['Entertainment_Time'].values[0]),
                'sleep_time': int(stress_data['Sleep_Time'].values[0])
            },
            'attendance': {
                'attendance_rate': attendance_data['Attendance_Rate'].values[0] if not attendance_data.empty else 'N/A'
            },
            'grades': {
                'assignment_1': int(grades_data['Assignment_1_Grade'].values[0]) if not grades_data.empty else 'N/A',
                'assignment_2': int(grades_data['Assignment_2_Grade'].values[0]) if not grades_data.empty else 'N/A',
                'assessment': int(grades_data['Assessment_Grade'].values[0]) if not grades_data.empty else 'N/A'
            },
            'report': report
        }
        
        return jsonify({'overview': overview})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_all_students', methods=['GET'])
def get_all_students():
    """Get list of all students with their IDs"""
    try:
        conn = sqlite3.connect(detabase_path)
        query = "SELECT Student_ID, Student_Name, Gender FROM Students"
        students_df = pd.read_sql_query(query, conn)
        conn.close()
        return jsonify({'students': students_df.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_dashboard_summary', methods=['GET'])
def get_dashboard_summary():
    """Get summary statistics for dashboard"""
    try:
        # Get stress data
        stress_df = Stress_level_calculate(detabase_path)
        high_stress_count = len(stress_df[stress_df['stress_level'] > 3])
        avg_stress = stress_df['stress_level'].mean()
        
        # Get attendance data
        attendance_df = Attendance_rate_calculate(detabase_path)
        attendance_df['Rate_Numeric'] = attendance_df['Attendance_Rate'].str.rstrip('%').astype(float)
        avg_attendance = attendance_df['Rate_Numeric'].mean()
        low_attendance_count = len(attendance_df[attendance_df['Rate_Numeric'] < 70])
        
        # Get grades data
        grades_df = Students_grades(detabase_path)
        avg_assignment1 = grades_df['Assignment_1_Grade'].mean()
        avg_assignment2 = grades_df['Assignment_2_Grade'].mean()
        avg_assessment = grades_df['Assessment_Grade'].mean()
        
        summary = {
            'total_students': len(stress_df),
            'stress': {
                'average_stress_level': round(avg_stress, 2),
                'high_stress_students': high_stress_count
            },
            'attendance': {
                'average_attendance_rate': f"{avg_attendance:.1f}%",
                'low_attendance_students': low_attendance_count
            },
            'grades': {
                'average_assignment_1': round(avg_assignment1, 2),
                'average_assignment_2': round(avg_assignment2, 2),
                'average_assessment': round(avg_assessment, 2)
            }
        }
        
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== API DOCUMENTATION ====================

@app.route('/', methods=['GET'])
def api_docs():
    """API Documentation endpoint"""
    docs = {
        'name': 'Student Wellbeing API',
        'version': '1.0',
        'endpoints': {
            'User Management': {
                'GET /get_user_info': 'Get all users',
                'POST /add_user': 'Add a new user (body: user_id, password)',
                'POST /update_user_id': 'Update user ID (body: current_user_id, new_user_id, password)',
                'POST /update_password': 'Update password (body: user_id, current_password, new_password)'
            },
            'Stress Analysis (funcsw.py)': {
                'GET /get_stress_level_df': 'Get stress levels for all students',
                'GET /get_high_stress_df': 'Get students with high stress (>3)',
                'GET /get_report?student_id=X': 'Get stress report for a student',
                'GET /get_report?student_name=X': 'Get stress report by student name'
            },
            'Attendance (funcd.py)': {
                'GET /get_attendance_rate': 'Get attendance rates for all students',
                'GET /get_student_attendance?student_id=X': 'Get attendance for specific student',
                'GET /get_student_attendance?student_name=X': 'Get attendance by student name'
            },
            'Grades (funcd.py)': {
                'GET /get_student_grades': 'Get all grades for all students',
                'GET /get_grades_by_student?student_id=X': 'Get grades for specific student',
                'GET /get_grades_by_student?student_name=X': 'Get grades by student name'
            },
            'Charts (funcd.py)': {
                'GET /chart/assignment_grades': 'Bar chart of assignment grade distribution (PNG)',
                'GET /chart/assignment_submissions': 'Bar chart of submission times by week (PNG)',
                'GET /chart/assessment_grades': 'Bar chart of assessment grade distribution (PNG)',
                'GET /chart/attendance_vs_assessment': 'Scatter plot of attendance vs assessment (PNG)'
            },
            'Combined Data': {
                'GET /get_student_overview?student_id=X': 'Complete student overview',
                'GET /get_all_students': 'List all students',
                'GET /get_dashboard_summary': 'Dashboard summary statistics'
            }
        }
    }
    return jsonify(docs)

if __name__ == '__main__':
    app.run(debug=True)