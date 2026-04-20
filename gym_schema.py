
import pymysql
import hashlib

DB_NAME = "gym_db"

conn = pymysql.connect(host="localhost", user="root", password="", database=DB_NAME, autocommit=True)
cursor = conn.cursor()


def h(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


print("Dropping all tables...")
cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
cursor.execute("DROP TABLE IF EXISTS ATTENDANCE")
cursor.execute("DROP TABLE IF EXISTS PAYMENT")
cursor.execute("DROP TABLE IF EXISTS SUBSCRIPTION")
cursor.execute("DROP TABLE IF EXISTS MEMBER")
cursor.execute("DROP TABLE IF EXISTS MEMBERSHIP")
cursor.execute("DROP TABLE IF EXISTS USER")
cursor.execute("DROP TABLE IF EXISTS ROLE")
cursor.execute("DROP TABLE IF EXISTS ACTIVITY_LOG")
cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
print("All tables dropped.")

# ── RECREATE TABLES ──────────────────────────────────────────────────────────

cursor.execute("""
    CREATE TABLE ROLE (
        Role_ID   INT AUTO_INCREMENT PRIMARY KEY,
        Role_Name VARCHAR(50) NOT NULL UNIQUE
    )
""")

cursor.execute("""
    CREATE TABLE USER (
        User_ID    INT AUTO_INCREMENT PRIMARY KEY,
        Role_ID    INT NOT NULL,
        Username   VARCHAR(100) NOT NULL UNIQUE,
        Password   VARCHAR(255) NOT NULL,
        Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (Role_ID) REFERENCES ROLE(Role_ID)
    )
""")

cursor.execute("""
    CREATE TABLE MEMBER (
        Member_ID      INT AUTO_INCREMENT PRIMARY KEY,
        User_ID        INT,
        First_Name     VARCHAR(100) NOT NULL,
        Last_Name      VARCHAR(100) NOT NULL,
        Contact_Number VARCHAR(20),
        Status         VARCHAR(20) DEFAULT 'Active',
        FOREIGN KEY (User_ID) REFERENCES USER(User_ID) ON DELETE CASCADE
    )
""")

cursor.execute("""
    CREATE TABLE MEMBERSHIP (
        Type_ID     INT AUTO_INCREMENT PRIMARY KEY,
        Type_Name   VARCHAR(100) NOT NULL,
        Description VARCHAR(255),
        Base_Price  DECIMAL(10,2) NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE SUBSCRIPTION (
        Subscription_ID INT AUTO_INCREMENT PRIMARY KEY,
        Type_ID         INT,
        Member_ID       INT,
        Start_Date      DATE NOT NULL,
        End_Date        DATE NOT NULL,
        Status          TINYINT(1) DEFAULT 1,
        CONSTRAINT CHK_Dates CHECK (End_Date > Start_Date),
        FOREIGN KEY (Type_ID)   REFERENCES MEMBERSHIP(Type_ID),
        FOREIGN KEY (Member_ID) REFERENCES MEMBER(Member_ID)
    )
""")

cursor.execute("""
    CREATE TABLE ATTENDANCE (
        Attendance_ID  INT AUTO_INCREMENT PRIMARY KEY,
        Member_ID      INT,
        Check_In_Time  VARCHAR(10),
        Check_Out_Time VARCHAR(10),
        Date           DATE,
        FOREIGN KEY (Member_ID) REFERENCES MEMBER(Member_ID)
    )
""")

cursor.execute("""
    CREATE TABLE PAYMENT (
        Payment_ID      INT AUTO_INCREMENT PRIMARY KEY,
        Subscription_ID INT,
        Amount          DECIMAL(10,2) NOT NULL CHECK (Amount > 0),
        Payment_Date    DATE NOT NULL,
        Method          VARCHAR(50),
        FOREIGN KEY (Subscription_ID) REFERENCES SUBSCRIPTION(Subscription_ID)
    )
""")

cursor.execute("""
    CREATE TABLE ACTIVITY_LOG (
        Log_ID   INT AUTO_INCREMENT PRIMARY KEY,
        Log_Msg  VARCHAR(255),
        Log_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

print("All tables recreated.")

# ── STORED PROCEDURE ─────────────────────────────────────────────────────────
cursor.execute("DROP PROCEDURE IF EXISTS AddMember")
cursor.execute("""
    CREATE PROCEDURE AddMember(
        IN p_user_id  INT,
        IN p_fname    VARCHAR(100),
        IN p_lname    VARCHAR(100),
        IN p_contact  VARCHAR(20)
    )
    BEGIN
        INSERT INTO MEMBER (User_ID, First_Name, Last_Name, Contact_Number)
        VALUES (p_user_id, p_fname, p_lname, p_contact);
    END
""")

# ── FUNCTION ─────────────────────────────────────────────────────────────────
cursor.execute("SET GLOBAL log_bin_trust_function_creators = 1")
cursor.execute("DROP FUNCTION IF EXISTS GetFullName")
cursor.execute("""
    CREATE FUNCTION GetFullName(f_name VARCHAR(100), l_name VARCHAR(100))
    RETURNS VARCHAR(201) DETERMINISTIC
    BEGIN
        RETURN CONCAT(f_name, ' ', l_name);
    END
""")

# ── TRIGGER ──────────────────────────────────────────────────────────────────
cursor.execute("DROP TRIGGER IF EXISTS AfterUserInsert")
cursor.execute("""
    CREATE TRIGGER AfterUserInsert
    AFTER INSERT ON USER
    FOR EACH ROW
    BEGIN
        INSERT INTO ACTIVITY_LOG (Log_Msg)
        VALUES (CONCAT('New user created: ', NEW.Username));
    END
""")

print("Procedure, function, trigger created.")

# ── SEED DATA ────────────────────────────────────────────────────────────────

cursor.executemany("INSERT INTO ROLE (Role_Name) VALUES (%s)", [
    ("Admin",), ("Owner",), ("Receptionist",)
])

cursor.executemany(
    "INSERT INTO MEMBERSHIP (Type_Name, Description, Base_Price) VALUES (%s, %s, %s)", [
        ("Daily Pass", "Single day access for walk-ins", 150.00),
        ("Monthly Standard", "Regular 30-day gym access", 1200.00),
        ("Student Monthly", "Discounted 30-day rate with valid ID", 900.00),
    ])

cursor.executemany(
    "INSERT INTO USER (Role_ID, Username, Password) VALUES (%s, %s, %s)", [
        (1, "Admin", h("password123")),
        (3, "Staff01", h("staffpass456")),
    ])

cursor.executemany("""
    INSERT INTO MEMBER (User_ID, First_Name, Last_Name, Contact_Number, Status)
    VALUES (%s, %s, %s, %s, %s)
""", [
    (1, "Juan", "Dela Cruz", "09171234567", "Active"),
    (1, "Maria", "Clara", "09187654321", "Active"),
    (1, "Ricardo", "Dalisay", "09223334455", "Active"),
    (1, "JP", "Tuzara", "09912127041", "Active"),
    (1, "Ana", "Reyes", "09351234567", "Active"),
    (1, "Carlo", "Mendoza", "09461234567", "Inactive"),
])

cursor.executemany("""
    INSERT INTO SUBSCRIPTION (Type_ID, Member_ID, Start_Date, End_Date, Status)
    VALUES (%s, %s, %s, %s, %s)
""", [
    (2, 1, "2026-04-01", "2026-05-01", 1),
    (3, 2, "2026-03-15", "2026-04-15", 1),
    (1, 3, "2026-04-09", "2026-04-10", 0),
    (3, 4, "2026-04-09", "2026-05-09", 1),
    (2, 5, "2026-04-01", "2026-05-01", 1),
    (1, 6, "2026-03-01", "2026-03-02", 0),
])

cursor.executemany("""
    INSERT INTO PAYMENT (Subscription_ID, Amount, Payment_Date, Method)
    VALUES (%s, %s, %s, %s)
""", [
    (1, 1200.00, "2026-04-01", "Cash"),
    (2, 900.00, "2026-03-15", "GCash"),
    (3, 150.00, "2026-04-09", "Cash"),
    (4, 900.00, "2026-04-09", "Paymaya"),
    (5, 1200.00, "2026-04-01", "Cash"),
    (6, 150.00, "2026-03-01", "E-Wallet"),
])

cursor.executemany("""
    INSERT INTO ATTENDANCE (Member_ID, Check_In_Time, Check_Out_Time, Date)
    VALUES (%s, %s, %s, %s)
""", [
    (1, "06:00", "08:00", "2026-04-05"),
    (2, "07:30", "09:30", "2026-04-05"),
    (3, "17:00", "19:00", "2026-04-06"),
    (4, "06:00", "07:30", "2026-04-07"),
    (5, "08:00", "10:00", "2026-04-08"),
    (1, "06:00", "08:00", "2026-04-10"),
    (2, "07:00", "09:00", "2026-04-12"),
    (3, "18:00", "20:00", "2026-04-15"),
])

conn.close()
print("Done — gym_db fully reset and seeded. Login with Admin / password123")