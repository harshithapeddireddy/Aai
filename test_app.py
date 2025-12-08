"""
Test Suite for Student Wellbeing System
========================================
Comprehensive unit tests for all modules including:
- Database operations
- Authentication
- Analytics
- Notifications
- Chart generation (funcd.py)
- API endpoints
"""

import unittest
import sqlite3
import os
import sys
import json
import tempfile
import shutil
from io import BytesIO

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test - handle database.py auto-execution
try:
    from database import create_database
except Exception:
    def create_database(db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.close()
        
from auth import authenticate_user, get_user_from_token, create_session, AUTHORIZED_USERS
from analytics import (
    get_attendance_assignment_correlation,
    get_stress_over_time_data,
    get_participation_overview
)
from notifications import (
    generate_stress_alerts,
    generate_sleep_alerts,
    generate_attendance_alerts,
    get_notification_summary,
    get_absent_students
)

import matplotlib
matplotlib.use('Agg')

from funcd import (
    Attendance_rate_calculate,
    Students_grades,
    barchart_assi_grade,
    barchart_assi_subt,
    barchart_asse_grade,
    plot_asse_att
)


class TestAuthentication(unittest.TestCase):
    """Test cases for authentication module"""
    
    def test_valid_wellbeing_officer_login(self):
        """Test login with valid wellbeing officer credentials"""
        result = authenticate_user('kayla', 'kayla123')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['role'], 'wellbeing_officer')
        self.assertEqual(result['username'], 'kayla')
    
    def test_valid_course_lead_login(self):
        """Test login with valid course lead credentials"""
        result = authenticate_user('courselead', 'lead123')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['role'], 'course_lead')
        self.assertEqual(result['username'], 'courselead')
    
    def test_valid_admin_login(self):
        """Test login with valid admin credentials"""
        result = authenticate_user('admin', 'admin123')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['role'], 'admin')
        self.assertEqual(result['username'], 'admin')
    
    def test_invalid_username(self):
        """Test login with invalid username"""
        result = authenticate_user('invaliduser', 'password123')
        
        self.assertIsNone(result)
    
    def test_invalid_password(self):
        """Test login with invalid password"""
        result = authenticate_user('kayla', 'wrongpassword')
        
        self.assertIsNone(result)
    
    def test_token_verification(self):
        """Test that generated token can be verified"""
        user_info = authenticate_user('kayla', 'kayla123')
        # authenticate_user returns user info, create_session creates the token
        token = create_session(user_info)
        
        user = get_user_from_token(token)
        
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'kayla')
    
    def test_invalid_token_verification(self):
        """Test verification of invalid token"""
        user = get_user_from_token('invalid_token_123')
        
        self.assertIsNone(user)
    
    def test_wellbeing_officer_permissions(self):
        """Test that wellbeing officer has correct permissions"""
        user = AUTHORIZED_USERS['kayla']
        
        self.assertIn('view_stress', user['permissions'])
        self.assertIn('view_sleep', user['permissions'])
        self.assertIn('view_notifications', user['permissions'])
        self.assertNotIn('view_attendance', user['permissions'])
    
    def test_course_lead_permissions(self):
        """Test that course lead has correct permissions"""
        user = AUTHORIZED_USERS['courselead']
        
        self.assertIn('view_attendance', user['permissions'])
        self.assertIn('view_correlation', user['permissions'])
        self.assertNotIn('view_stress', user['permissions'])
    
    def test_admin_permissions(self):
        """Test that admin has all permissions"""
        user = AUTHORIZED_USERS['admin']
        
        self.assertIn('view_stress', user['permissions'])
        self.assertIn('view_attendance', user['permissions'])
        self.assertIn('manage_students', user['permissions'])
    
    def test_multiple_wellbeing_officers_exist(self):
        """Test that multiple wellbeing officers are configured"""
        wo_users = [u for u, data in AUTHORIZED_USERS.items() 
                   if data['role'] == 'wellbeing_officer']
        self.assertGreaterEqual(len(wo_users), 3)


class TestAnalytics(unittest.TestCase):
    """Test cases for analytics module"""
    
    @classmethod
    def setUpClass(cls):
        """Use the existing database for testing"""
        cls.db_path = 'Student_wellbeing.db'
    
    def test_correlation_returns_dict(self):
        """Test that correlation function returns a dictionary"""
        result = get_attendance_assignment_correlation(self.db_path)
        
        self.assertIsInstance(result, dict)
    
    def test_correlation_has_required_keys(self):
        """Test that correlation result has required keys"""
        result = get_attendance_assignment_correlation(self.db_path)
        
        self.assertIn('correlation', result)
        self.assertIn('student_data', result)
        self.assertIn('interpretation', result)
    
    def test_correlation_value_in_range(self):
        """Test that correlation value is between -1 and 1"""
        result = get_attendance_assignment_correlation(self.db_path)
        corr = result['correlation']['attendance_vs_assignment']
        
        self.assertGreaterEqual(corr, -1)
        self.assertLessEqual(corr, 1)
    
    def test_stress_data_returns_dict(self):
        """Test that stress data function returns a dictionary"""
        result = get_stress_over_time_data(self.db_path)
        
        self.assertIsInstance(result, dict)
    
    def test_stress_data_has_statistics(self):
        """Test that stress data has statistics"""
        result = get_stress_over_time_data(self.db_path)
        
        self.assertIn('statistics', result)
        self.assertIn('total_students', result['statistics'])
        self.assertIn('high_stress_count', result['statistics'])
    
    def test_stress_data_has_chart_data(self):
        """Test that stress data has chart data"""
        result = get_stress_over_time_data(self.db_path)
        
        self.assertIn('chart_data', result)
        self.assertIn('students', result['chart_data'])
        self.assertIn('stress_levels', result['chart_data'])
    
    def test_participation_overview_returns_dict(self):
        """Test that participation overview returns a dictionary"""
        result = get_participation_overview(self.db_path)
        
        self.assertIsInstance(result, dict)
    
    def test_participation_has_required_keys(self):
        """Test that participation overview has required keys"""
        result = get_participation_overview(self.db_path)
        
        # Participation has nested 'overall' key
        self.assertIn('overall', result)
        self.assertIn('total_students', result['overall'])
        self.assertIn('overall_attendance_rate', result['overall'])


class TestNotifications(unittest.TestCase):
    """Test cases for notifications module"""
    
    @classmethod
    def setUpClass(cls):
        """Use the existing database for testing"""
        cls.db_path = 'Student_wellbeing.db'
    
    def test_stress_alerts_returns_list(self):
        """Test that stress alerts function returns a list"""
        result = generate_stress_alerts(self.db_path)
        
        self.assertIsInstance(result, list)
    
    def test_stress_alert_has_required_fields(self):
        """Test that stress alerts have required fields"""
        result = generate_stress_alerts(self.db_path)
        
        if len(result) > 0:
            alert = result[0]
            self.assertIn('student_id', alert)
            self.assertIn('student_name', alert)
            self.assertIn('type', alert)
    
    def test_sleep_alerts_returns_list(self):
        """Test that sleep alerts function returns a list"""
        result = generate_sleep_alerts(self.db_path)
        
        self.assertIsInstance(result, list)
    
    def test_sleep_alert_threshold(self):
        """Test that sleep alerts are generated for students with <= 7 hours sleep"""
        result = generate_sleep_alerts(self.db_path)
        
        for alert in result:
            self.assertLessEqual(alert['value'], 7, 
                f"Sleep alert should only be for <= 7 hours, got {alert['value']}")
    
    def test_attendance_alerts_returns_list(self):
        """Test that attendance alerts function returns a list"""
        result = generate_attendance_alerts(self.db_path)
        
        self.assertIsInstance(result, list)
    
    def test_notification_summary_returns_dict(self):
        """Test that notification summary returns a dictionary"""
        result = get_notification_summary(self.db_path)
        
        self.assertIsInstance(result, dict)
    
    def test_notification_summary_has_total(self):
        """Test that notification summary has total count"""
        result = get_notification_summary(self.db_path)
        
        self.assertIn('total', result)
        self.assertGreaterEqual(result['total'], 0)
    
    def test_notification_summary_has_by_type(self):
        """Test that notification summary has by_type breakdown"""
        result = get_notification_summary(self.db_path)
        
        self.assertIn('by_type', result)
        self.assertIn('stress', result['by_type'])
        self.assertIn('sleep', result['by_type'])
    
    def test_absent_students_returns_dataframe(self):
        """Test that absent students function returns a DataFrame"""
        import pandas as pd
        result = get_absent_students(self.db_path)
        
        self.assertIsInstance(result, pd.DataFrame)
    
    def test_absent_students_has_required_columns(self):
        """Test that absent students DataFrame has required columns"""
        result = get_absent_students(self.db_path)
        
        self.assertIn('Student_ID', result.columns)
        self.assertIn('Student_Name', result.columns)
        self.assertIn('Absences', result.columns)


class TestChartGeneration(unittest.TestCase):
    """Test cases for chart generation (funcd.py)"""
    
    @classmethod
    def setUpClass(cls):
        """Use the existing database for testing"""
        cls.db_path = 'Student_wellbeing.db'
    
    def test_attendance_rate_calculate_returns_dataframe(self):
        """Test that attendance rate calculation returns a DataFrame"""
        import pandas as pd
        result = Attendance_rate_calculate(self.db_path)
        
        self.assertIsInstance(result, pd.DataFrame)
    
    def test_attendance_rate_has_required_columns(self):
        """Test that attendance rate DataFrame has required columns"""
        result = Attendance_rate_calculate(self.db_path)
        
        self.assertIn('Student_Name', result.columns)
        self.assertIn('Student_ID', result.columns)
        self.assertIn('Attendance_Rate', result.columns)
    
    def test_students_grades_returns_dataframe(self):
        """Test that students grades function returns a DataFrame"""
        import pandas as pd
        result = Students_grades(self.db_path)
        
        self.assertIsInstance(result, pd.DataFrame)
    
    def test_barchart_assi_grade_returns_image(self):
        """Test that assignment grade bar chart returns a valid image"""
        result = barchart_assi_grade(self.db_path)
        
        self.assertIsInstance(result, BytesIO)
        self.assertGreater(len(result.getvalue()), 0)
        # Check PNG signature
        result.seek(0)
        self.assertEqual(result.read(8), b'\x89PNG\r\n\x1a\n')
    
    def test_barchart_assi_subt_returns_image(self):
        """Test that assignment submission bar chart returns a valid image"""
        result = barchart_assi_subt(self.db_path)
        
        self.assertIsInstance(result, BytesIO)
        self.assertGreater(len(result.getvalue()), 0)
        # Check PNG signature
        result.seek(0)
        self.assertEqual(result.read(8), b'\x89PNG\r\n\x1a\n')
    
    def test_barchart_asse_grade_returns_image(self):
        """Test that assessment grade bar chart returns a valid image"""
        result = barchart_asse_grade(self.db_path)
        
        self.assertIsInstance(result, BytesIO)
        self.assertGreater(len(result.getvalue()), 0)
        # Check PNG signature
        result.seek(0)
        self.assertEqual(result.read(8), b'\x89PNG\r\n\x1a\n')
    
    def test_plot_asse_att_returns_image(self):
        """Test that attendance vs assessment scatter plot returns a valid image"""
        result = plot_asse_att(self.db_path)
        
        self.assertIsInstance(result, BytesIO)
        self.assertGreater(len(result.getvalue()), 0)
        # Check PNG signature
        result.seek(0)
        self.assertEqual(result.read(8), b'\x89PNG\r\n\x1a\n')
    
    def test_chart_image_sizes_reasonable(self):
        """Test that chart images are reasonably sized"""
        charts = [
            barchart_assi_grade(self.db_path),
            barchart_assi_subt(self.db_path),
            barchart_asse_grade(self.db_path),
            plot_asse_att(self.db_path)
        ]
        
        for chart in charts:
            size = len(chart.getvalue())
            # Chart should be between 5KB and 500KB
            self.assertGreater(size, 5000, "Chart too small")
            self.assertLess(size, 500000, "Chart too large")


class TestDataIntegrity(unittest.TestCase):
    """Test cases for data integrity and relationships"""
    
    @classmethod
    def setUpClass(cls):
        """Use the existing database for testing"""
        cls.db_path = 'Student_wellbeing.db'
    
    def test_all_attendance_records_have_valid_student(self):
        """Test that all attendance records reference valid students"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM Attendance a
            LEFT JOIN Students s ON a.Student_ID = s.Student_ID
            WHERE s.Student_ID IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(orphan_count, 0, "All attendance records should have valid students")
    
    def test_all_assignments_have_valid_student(self):
        """Test that all assignment records reference valid students"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM Assignment a
            LEFT JOIN Students s ON a.Student_ID = s.Student_ID
            WHERE s.Student_ID IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(orphan_count, 0, "All assignment records should have valid students")
    
    def test_all_assessments_have_valid_student(self):
        """Test that all assessment records reference valid students"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM Assessment a
            LEFT JOIN Students s ON a.Student_ID = s.Student_ID
            WHERE s.Student_ID IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(orphan_count, 0, "All assessment records should have valid students")
    
    def test_all_surveys_have_valid_student(self):
        """Test that all survey records reference valid students"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM Survey s
            LEFT JOIN Students st ON s.Student_ID = st.Student_ID
            WHERE st.Student_ID IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(orphan_count, 0, "All survey records should have valid students")
    
    def test_attendance_status_values_are_valid(self):
        """Test that attendance status values are 0, 1, or 2"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM Attendance
            WHERE Attendance_Status NOT IN (0, 1, 2)
        """)
        invalid_count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(invalid_count, 0, "Attendance status should be 0, 1, or 2")
    
    def test_grades_are_in_valid_range(self):
        """Test that all grades are between 0 and 100"""
        conn = sqlite3.connect(self.db_path)
        
        # Check assignment grades
        cursor = conn.execute("""
            SELECT COUNT(*) FROM Assignment
            WHERE Assignment_Grade < 0 OR Assignment_Grade > 100
        """)
        invalid_assignment = cursor.fetchone()[0]
        
        # Check assessment grades
        cursor = conn.execute("""
            SELECT COUNT(*) FROM Assessment
            WHERE Assessment_Grade < 0 OR Assessment_Grade > 100
        """)
        invalid_assessment = cursor.fetchone()[0]
        
        conn.close()
        
        self.assertEqual(invalid_assignment, 0, "Assignment grades should be between 0 and 100")
        self.assertEqual(invalid_assessment, 0, "Assessment grades should be between 0 and 100")
    
    def test_sleep_time_is_positive(self):
        """Test that sleep time values are positive"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM Survey
            WHERE Sleep_Time < 0
        """)
        negative_count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(negative_count, 0, "Sleep time should be positive")
    
    def test_student_count_matches_across_tables(self):
        """Test that student count is consistent across related tables"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute("SELECT COUNT(*) FROM Students")
        student_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(DISTINCT Student_ID) FROM Survey")
        survey_students = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(DISTINCT Student_ID) FROM Assessment")
        assessment_students = cursor.fetchone()[0]
        
        conn.close()
        
        # Survey and Assessment should have entries for all students
        self.assertEqual(student_count, survey_students)
        self.assertEqual(student_count, assessment_students)


class TestStressCalculation(unittest.TestCase):
    """Test cases for stress calculation logic"""
    
    @classmethod
    def setUpClass(cls):
        """Use the existing database for testing"""
        cls.db_path = 'Student_wellbeing.db'
    
    def test_stress_levels_are_calculated(self):
        """Test that stress levels are calculated for students"""
        result = get_stress_over_time_data(self.db_path)
        
        self.assertGreater(len(result['chart_data']['stress_levels']), 0)
    
    def test_high_stress_count_is_valid(self):
        """Test that high stress count is non-negative"""
        result = get_stress_over_time_data(self.db_path)
        
        self.assertGreaterEqual(result['statistics']['high_stress_count'], 0)
    
    def test_stress_levels_have_valid_values(self):
        """Test that stress levels are numeric"""
        result = get_stress_over_time_data(self.db_path)
        
        for level in result['chart_data']['stress_levels']:
            self.assertIsInstance(level, (int, float))
    
    def test_stress_statistics_has_average(self):
        """Test that statistics include average stress"""
        result = get_stress_over_time_data(self.db_path)
        
        # The key is 'average_stress' not 'avg_stress'
        self.assertIn('average_stress', result['statistics'])


class TestAPIEndpoints(unittest.TestCase):
    """Test cases for Flask API endpoints (integration tests)"""
    
    @classmethod
    def setUpClass(cls):
        """Set up Flask test client"""
        import app as flask_app
        flask_app.app.config['TESTING'] = True
        cls.client = flask_app.app.test_client()
        cls.db_path = 'Student_wellbeing.db'
    
    def test_login_endpoint_exists(self):
        """Test that login endpoint exists and responds"""
        response = self.client.post('/login', 
                                   json={'username': 'kayla', 'password': 'kayla123'},
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
    
    def test_login_returns_token(self):
        """Test that successful login returns a token"""
        response = self.client.post('/login',
                                   json={'username': 'kayla', 'password': 'kayla123'},
                                   content_type='application/json')
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertIn('token', data)
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials returns error"""
        response = self.client.post('/login',
                                   json={'username': 'invalid', 'password': 'invalid'},
                                   content_type='application/json')
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
    
    def test_home_page_loads(self):
        """Test that home page loads"""
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_stress_api_requires_token(self):
        """Test that stress API requires valid token"""
        response = self.client.get('/api/stress-levels')
        
        # Should return error without token
        self.assertIn(response.status_code, [401, 403, 500])
    
    def test_authenticated_stress_api(self):
        """Test stress API with valid token"""
        # Login first
        login_response = self.client.post('/login',
                                         json={'username': 'kayla', 'password': 'kayla123'},
                                         content_type='application/json')
        token = json.loads(login_response.data)['token']
        
        # Access API with token - correct endpoint is /api/stress-levels
        response = self.client.get(f'/api/stress-levels?token={token}')
        
        self.assertEqual(response.status_code, 200)
    
    def test_correlation_api(self):
        """Test correlation API with valid token"""
        login_response = self.client.post('/login',
                                         json={'username': 'courselead', 'password': 'lead123'},
                                         content_type='application/json')
        token = json.loads(login_response.data)['token']
        
        response = self.client.get(f'/api/correlation?token={token}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    def test_notifications_api(self):
        """Test notifications API with valid token"""
        login_response = self.client.post('/login',
                                         json={'username': 'kayla', 'password': 'kayla123'},
                                         content_type='application/json')
        token = json.loads(login_response.data)['token']
        
        response = self.client.get(f'/api/notifications?token={token}')
        
        self.assertEqual(response.status_code, 200)
    
    def test_chart_api_returns_image(self):
        """Test that chart APIs return valid images"""
        login_response = self.client.post('/login',
                                         json={'username': 'courselead', 'password': 'lead123'},
                                         content_type='application/json')
        token = json.loads(login_response.data)['token']
        
        response = self.client.get(f'/api/chart/assessment-grades?token={token}')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'image/png')


class TestDatabaseSchema(unittest.TestCase):
    """Test cases for database schema validation"""
    
    @classmethod
    def setUpClass(cls):
        cls.db_path = 'Student_wellbeing.db'
    
    def test_students_table_structure(self):
        """Test Students table has correct structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("PRAGMA table_info(Students)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        
        self.assertIn('Student_ID', columns)
        self.assertIn('Student_Name', columns)
        self.assertIn('Gender', columns)
    
    def test_attendance_table_structure(self):
        """Test Attendance table has correct structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("PRAGMA table_info(Attendance)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        
        self.assertIn('Attendance_ID', columns)
        self.assertIn('Student_ID', columns)
        self.assertIn('Weekly', columns)
        self.assertIn('Attendance_Status', columns)
    
    def test_survey_table_structure(self):
        """Test Survey table has correct structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("PRAGMA table_info(Survey)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        
        self.assertIn('Time_Usage_ID', columns)
        self.assertIn('Student_ID', columns)
        self.assertIn('Sleep_Time', columns)
        self.assertIn('Study_Time', columns)


def run_tests():
    """Run all tests and generate report"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalytics))
    suite.addTests(loader.loadTestsFromTestCase(TestNotifications))
    suite.addTests(loader.loadTestsFromTestCase(TestChartGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))
    suite.addTests(loader.loadTestsFromTestCase(TestStressCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseSchema))
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    success_count = result.testsRun - len(result.failures) - len(result.errors)
    print(f"Passed: {success_count}")
    print(f"Success Rate: {(success_count / result.testsRun * 100):.1f}%")
    
    return result


if __name__ == '__main__':
    run_tests()
