import sqlite3
import pandas as pd
import struct

#Show all rows
pd.set_option('display.max_rows', None)
#Show all cols
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

# connect to database
database_path = 'Student_wellbeing.db'
conn = sqlite3.connect(database_path)

# select data from tables
query1 = "SELECT * FROM students"
df1 = pd.read_sql_query(query1, conn)

query2 = "SELECT * FROM attendance"
df2 = pd.read_sql_query(query2, conn)

query3 = "SELECT * FROM assignment"
df3 = pd.read_sql_query(query3, conn)

query4 = "SELECT * FROM assessment"
df4 = pd.read_sql_query(query4, conn)

query5 = "SELECT * FROM survey"
df5 = pd.read_sql_query(query5, conn)


# close database connect
conn.close()
print("\nStudents Table Visible：")
print(df1)

print("\nAttendance Table Visible：")
print(df2)

print("\nAssignment Table Visible：")
print(df3)

print("\nAssessment Table Visible：")
print(df4)

print("\nSurvey Table Visible：")
print(df5)

detabase_path = 'user_data.db'
conn = sqlite3.connect(detabase_path)

query6 = "SELECT * FROM users"
df6 = pd.read_sql_query(query6, conn)
print("\nUsers Table Visible：")
print(df6)