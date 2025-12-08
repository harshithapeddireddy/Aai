# UML Sequence Diagrams - Student Wellbeing Application

This document contains UML sequence diagrams for the Student Wellbeing Application.
You can render these using:
- **Mermaid**: GitHub, GitLab, VS Code with Mermaid extension
- **PlantUML**: Online at plantuml.com or VS Code with PlantUML extension

---

## 1. Authentication Flow (Login)

```mermaid
sequenceDiagram
    autonumber
    participant U as User (Browser)
    participant D as Dashboard (HTML/JS)
    participant F as Flask App
    participant A as Auth Module
    participant S as Session Store

    U->>D: Enter credentials
    D->>F: POST /login {username, password}
    F->>A: authenticate_user(username, password)
    A->>A: Hash password with SHA256
    A->>A: Compare with AUTHORIZED_USERS
    
    alt Valid Credentials
        A-->>F: Return user_info {name, role, permissions}
        F->>A: create_session(user_info)
        A->>S: Store token → user_info
        A-->>F: Return session token
        F-->>D: 200 OK {token, user}
        D->>D: Store token in memory
        D->>U: Show Dashboard
    else Invalid Credentials
        A-->>F: Return None
        F-->>D: 401 Unauthorized
        D->>U: Show error message
    end
```

---

## 2. Wellbeing Officer - View Stress Heatmap

```mermaid
sequenceDiagram
    autonumber
    participant U as Wellbeing Officer
    participant D as Dashboard
    participant F as Flask App
    participant A as Auth Module
    participant AN as Analytics Module
    participant DB as SQLite Database

    U->>D: Click "Stress Levels" tab
    D->>F: GET /api/stress-heatmap?token=xxx
    F->>A: @require_auth('view_stress')
    A->>A: get_user_from_token(token)
    
    alt Valid Token & Permission
        A-->>F: User authorized
        F->>AN: Stress_level_calculate(DATABASE_PATH)
        AN->>DB: SELECT Student_ID, Study_Time, Entertainment_Time, Sleep_Time FROM Survey
        DB-->>AN: Survey data
        AN->>DB: SELECT Student_ID, Student_Name FROM Students
        DB-->>AN: Student names
        AN->>AN: Calculate stress_level per student
        AN-->>F: stress_level_df
        F->>F: Normalize values for heatmap
        F-->>D: 200 OK {heatmap_data}
        D->>D: Render color-coded heatmap
        D->>U: Display Stress Heatmap
    else Unauthorized
        A-->>F: 401/403 Error
        F-->>D: Error response
        D->>U: Show access denied
    end
```

---

## 3. Course Lead - View Attendance Correlation

```mermaid
sequenceDiagram
    autonumber
    participant U as Course Lead
    participant D as Dashboard
    participant F as Flask App
    participant A as Auth Module
    participant AN as Analytics Module
    participant DB as SQLite Database

    U->>D: Click "Correlation" tab
    D->>F: GET /api/correlation?token=xxx
    F->>A: @require_auth('view_correlation')
    A->>A: Validate token & permission
    A-->>F: User authorized
    
    F->>AN: get_attendance_assignment_correlation()
    
    par Fetch Attendance Data
        AN->>DB: SELECT Student_ID, SUM(Attendance_Status), COUNT(*) FROM Attendance GROUP BY Student_ID
        DB-->>AN: Attendance rates
    and Fetch Assignment Data
        AN->>DB: SELECT Student_ID, AVG(Assignment_Grade) FROM Assignment GROUP BY Student_ID
        DB-->>AN: Assignment grades
    and Fetch Assessment Data
        AN->>DB: SELECT Student_ID, Assessment_Grade FROM Assessment
        DB-->>AN: Assessment grades
    end
    
    AN->>AN: Merge all dataframes
    AN->>AN: Calculate Pearson correlation
    AN->>AN: Categorize by attendance level
    AN-->>F: correlation_data
    
    F-->>D: 200 OK {correlation, interpretation, category_analysis}
    D->>D: Render correlation chart
    D->>U: Display correlation value & chart
```

---

## 4. Notification System Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant D as Dashboard
    participant F as Flask App
    participant A as Auth Module
    participant N as Notifications Module
    participant AN as Analytics Module
    participant DB as SQLite Database

    U->>D: Click "Notifications" tab
    D->>F: GET /api/notifications?token=xxx
    F->>A: Validate token
    A-->>F: User info with role
    
    alt Wellbeing Officer
        F->>N: get_all_notifications(category='wellbeing')
    else Course Lead
        F->>N: get_all_notifications(category='attendance')
    else Admin
        F->>N: get_all_notifications()
    end
    
    par Generate Stress Alerts
        N->>AN: Stress_level_calculate()
        AN->>DB: Query Survey + Students
        DB-->>AN: Data
        AN-->>N: stress_df
        N->>N: Filter stress_level > 3
        N->>N: Create HIGH_STRESS alerts
    and Generate Sleep Alerts
        N->>N: Filter Sleep_Time < 6
        N->>N: Create LOW_SLEEP alerts
    and Generate Attendance Alerts
        N->>DB: Query Attendance
        DB-->>N: Attendance data
        N->>N: Calculate attendance rates
        N->>N: Filter rate < 70%
        N->>N: Create LOW_ATTENDANCE alerts
    end
    
    N->>N: Sort by severity
    N-->>F: All alerts
    F-->>D: 200 OK {notifications}
    D->>D: Render alert list with badges
    D->>U: Display notifications
```

---

## 5. Role-Based Access Control Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant F as Flask App
    participant A as Auth Module
    participant S as Session Store

    U->>F: Request to protected endpoint
    F->>A: @require_auth(permission)
    
    A->>A: Extract token from header/query
    A->>S: get_user_from_token(token)
    
    alt Token Not Found
        S-->>A: None
        A-->>F: 401 Unauthorized
        F-->>U: "Please login first"
    else Token Valid
        S-->>A: user_info
        A->>A: Check if permission in user.permissions
        
        alt Permission Granted
            A->>F: Set request.current_user = user
            F->>F: Execute endpoint function
            F-->>U: Return data
        else Permission Denied
            A-->>F: 403 Forbidden
            F-->>U: "Access denied"
        end
    end
```

---

## 6. Complete User Session Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant B as Browser
    participant F as Flask App
    participant A as Auth
    participant N as Notifications
    participant AN as Analytics
    participant DB as Database

    rect rgb(240, 248, 255)
        Note over U,DB: Login Phase
        U->>B: Navigate to app
        B->>F: GET /
        F-->>B: Dashboard HTML
        U->>B: Enter credentials
        B->>F: POST /login
        F->>A: authenticate_user()
        A-->>F: user_info + token
        F-->>B: Success + token
    end

    rect rgb(255, 248, 240)
        Note over U,DB: Dashboard Loading
        B->>F: GET /api/notification-summary
        F->>N: get_notification_summary()
        N->>DB: Query all data
        DB-->>N: Results
        N-->>F: Summary counts
        F-->>B: {total, by_type, by_category}
    end

    rect rgb(240, 255, 240)
        Note over U,DB: View Stress Data (Wellbeing Officer)
        U->>B: Click Stress tab
        B->>F: GET /api/stress-visualization
        F->>AN: get_stress_over_time_data()
        AN->>DB: Query Survey, Students
        DB-->>AN: Raw data
        AN-->>F: chart_data, statistics
        F-->>B: Visualization data
        B->>B: Render Chart.js graphs
    end

    rect rgb(255, 240, 245)
        Note over U,DB: View Attendance (Course Lead)
        U->>B: Click Attendance tab
        B->>F: GET /api/participation
        F->>AN: get_participation_overview()
        AN->>DB: Query Attendance, Assignment
        DB-->>AN: Raw data
        AN-->>F: weekly_trend, assignments
        F-->>B: Participation data
        B->>B: Render attendance chart
    end

    rect rgb(245, 245, 255)
        Note over U,DB: Logout
        U->>B: Click Logout
        B->>F: POST /logout
        F->>A: logout_user(token)
        A->>A: Delete session
        A-->>F: Success
        F-->>B: Logged out
        B->>B: Show login screen
    end
```

---

## Component Overview Diagram

```mermaid
graph TB
    subgraph "Frontend"
        UI[Dashboard UI<br/>HTML/CSS/JS]
        Charts[Chart.js<br/>Visualizations]
    end
    
    subgraph "Flask Application"
        App[app.py<br/>Main Routes]
        Auth[auth.py<br/>Authentication]
        Notif[notifications.py<br/>Alert System]
        Analytics[analytics.py<br/>Data Analysis]
        Funcs[funcsw.py<br/>Stress Calculations]
    end
    
    subgraph "Data Layer"
        DB1[(Student_wellbeing.db<br/>Students, Survey,<br/>Attendance, Assignments)]
        DB2[(user_data.db<br/>User Credentials)]
    end
    
    UI --> App
    Charts --> UI
    App --> Auth
    App --> Notif
    App --> Analytics
    App --> Funcs
    Auth --> DB2
    Notif --> DB1
    Analytics --> DB1
    Funcs --> DB1
```

---

## How to Render These Diagrams

### Option 1: VS Code
1. Install "Markdown Preview Mermaid Support" extension
2. Open this file and press `Ctrl+Shift+V` to preview

### Option 2: GitHub/GitLab
- Just commit this file - diagrams render automatically

### Option 3: Online
- Copy Mermaid code to [mermaid.live](https://mermaid.live)

### Option 4: PlantUML
Convert Mermaid to PlantUML syntax and use [plantuml.com](https://www.plantuml.com/plantuml/uml/)
