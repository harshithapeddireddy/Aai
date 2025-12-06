from flask import Flask, request, jsonify
from funcsw import Stress_level_calculate, filter_high_stress_students, Stress_report
import sqlite3
import pandas as pd

app = Flask(__name__)

# 数据库路径
DATABASE_PATH = 'user_data.db'
detabase_path = 'Student_wellbeing.db'

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

if __name__ == '__main__':
    app.run(debug=True)