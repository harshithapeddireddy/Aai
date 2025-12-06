import requests
import json

# API 的基础 URL
BASE_URL = "http://localhost:5000"


def get_user_info():
    response = requests.get(f"{BASE_URL}/get_user_info")
    if response.status_code == 200:
        users = response.json()
        print("All users:", users)
        return users
    else:
        print("Failed to get user information:", response.json())
        return []


def add_user(user_id, password):
    data = {"user_id": user_id, "password": password}
    response = requests.post(f"{BASE_URL}/add_user", json=data)
    if response.status_code == 200:
        print("User added successfully:", response.json())
    else:
        print("Failed to add user:", response.json())


def update_user_id(current_user_id, new_user_id, password):
    data = {"current_user_id": current_user_id, "new_user_id": new_user_id, "password": password}
    response = requests.post(f"{BASE_URL}/update_user_id", json=data)
    if response.status_code == 200:
        print("User ID updated successfully:", response.json())
    else:
        print("Failed to update user ID:", response.json())


def update_password(user_id, current_password, new_password):
    data = {"user_id": user_id, "current_password": current_password, "new_password": new_password}
    response = requests.post(f"{BASE_URL}/update_password", json=data)
    if response.status_code == 200:
        print("Password updated successfully:", response.json())
    else:
        print("Failed to update password:", response.json())


# 测试获取 stress_level_df
def test_get_stress_level_df():
    url = f"{BASE_URL}/get_stress_level_df"
    response = requests.get(url)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    assert 'stress_level_df' in data, "Expected 'stress_level_df' key in response"
    stress_level_df = json.loads(data['stress_level_df'])
    assert isinstance(stress_level_df, list), "Expected stress_level_df to be a list"
    assert len(stress_level_df) > 0, "Expected stress_level_df to contain data"
    print("Test get_stress_level_df passed.")
    print("stress_level_df:")
    print(json.dumps(stress_level_df, indent=2))

# 测试获取 high_stress_df
def test_get_high_stress_df():
    url = f"{BASE_URL}/get_high_stress_df"
    response = requests.get(url)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    assert 'high_stress_df' in data, "Expected 'high_stress_df' key in response"
    high_stress_df = json.loads(data['high_stress_df'])
    assert isinstance(high_stress_df, list), "Expected high_stress_df to be a list"
    assert len(high_stress_df) > 0, "Expected high_stress_df to contain data"
    print("Test get_high_stress_df passed.")
    print("high_stress_df:")
    print(json.dumps(high_stress_df, indent=2))

# 测试获取单个学生的报告（通过 student_id）
def test_get_report_by_id():
    url = f"{BASE_URL}/get_report?student_id=5699026"
    response = requests.get(url)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    assert 'report' in data, "Expected 'report' key in response"
    report = data['report']
    assert isinstance(report, str) and len(report) > 0, "Expected report to be a non-empty string"
    print("Test get_report_by_id passed.")
    print("Report for student_id 5699026:")
    print(report)

# 测试获取单个学生的报告（通过 student_name）
def test_get_report_by_name():
    url = f"{BASE_URL}/get_report?student_name=Ping HONG"
    response = requests.get(url)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    assert 'report' in data, "Expected 'report' key in response"
    report = data['report']
    assert isinstance(report, str) and len(report) > 0, "Expected report to be a non-empty string"
    print("Test get_report_by_name passed.")
    print("Report for student_name 'Ping HONG':")
    print(report)


def main():
    # 获取所有用户信息
    users = get_user_info()

    # 测试获取第一行和第二行的用户信息
    if len(users) >= 2:
        first_user = users[0]
        second_user = users[1]
        print("First user:", first_user)
        print("Second user:", second_user)
    else:
        print("Not enough users to test.")

    # 测试添加新用户
    add_user("newuser001", "newpassword123")

    # 再次获取所有用户信息，确认新用户已添加
    users = get_user_info()

    # 测试更改新用户的 user_id
    update_user_id("newuser001", "newuser111", "newpassword123")

    # 测试更改新用户的 password
    update_password("newuser111", "newpassword123", "newpassword456")

    # 再次获取所有用户信息，确认更改已生效
    users = get_user_info()

    test_get_stress_level_df()
    test_get_high_stress_df()
    test_get_report_by_id()
    test_get_report_by_name()


if __name__ == "__main__":
    main()