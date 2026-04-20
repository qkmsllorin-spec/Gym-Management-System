import pymysql
import hashlib

DB_HOST     = "localhost"
DB_USER     = "root"
DB_PASSWORD = ""
DB_NAME     = "gym_db"

ALLOWED_TABLES = {
    "USER", "MEMBER", "MEMBERSHIP", "SUBSCRIPTION",
    "ATTENDANCE", "PAYMENT", "ROLE", "ACTIVITY_LOG"
}


class DatabaseManager:
    def __init__(self):
        self.config = {
            "host":     DB_HOST,
            "user":     DB_USER,
            "password": DB_PASSWORD,
            "database": DB_NAME,
        }

    def _get_conn(self):
        return pymysql.connect(**self.config)

    def _execute_query(self, query, params=(), fetch=False):
        """
        Central query runner. Catches ALL exceptions (not just MySQLError)
        and always closes the connection — no leaks.
        Returns: list of tuples if fetch=True, lastrowid if fetch=False, None on any error.
        """
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if fetch:
                    result = cursor.fetchall()
                    conn.commit()
                    return result
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            # Catches pymysql.MySQLError, OperationalError, TypeError, AttributeError — everything
            print(f"Database Error: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return None
        finally:
            # Always close — pymysql's context manager does NOT do this automatically
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # ── PASSWORD HASHING ────────────────────────────────────────────────────

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def migrate_plain_passwords(self):
        """
        Finds users with un-hashed passwords (under 64 chars) and hashes them.
        Safe to call every startup — skips already-hashed passwords.
        Never raises — prints and returns silently on any error.
        """
        try:
            users = self._execute_query("SELECT User_ID, Password FROM USER", fetch=True)
            if not users:
                print("No users found to migrate.")
                return
            migrated = 0
            for user_id, password in users:
                if len(str(password)) < 64:
                    hashed = self.hash_password(password)
                    self._execute_query(
                        "UPDATE USER SET Password = %s WHERE User_ID = %s",
                        (hashed, user_id)
                    )
                    migrated += 1
            if migrated:
                print(f"Password migration complete — {migrated} password(s) hashed.")
            else:
                print("All passwords already hashed — no migration needed.")
        except Exception as e:
            print(f"Migration skipped: {e}")

    # ── AUTH ────────────────────────────────────────────────────────────────

    def verify_login(self, username, password):
        """
        Returns (User_ID, Role_ID, Role_Name) on success, None on failure.
        Never raises — all errors return None.
        """
        try:
            hashed = self.hash_password(password)
            query  = """
                SELECT U.User_ID, U.Role_ID, R.Role_Name
                FROM USER U
                JOIN ROLE R ON U.Role_ID = R.Role_ID
                WHERE U.Username = %s AND U.Password = %s
            """
            result = self._execute_query(query, (username, hashed), fetch=True)
            if result and len(result) > 0:
                return result[0]
            return None
        except Exception as e:
            print(f"Login error: {e}")
            return None

    # ── USER MANAGEMENT ─────────────────────────────────────────────────────

    def add_user(self, username, password, role_id):
        hashed = self.hash_password(password)
        self._execute_query(
            "INSERT INTO USER (Username, Password, Role_ID) VALUES (%s, %s, %s)",
            (username, hashed, role_id)
        )

    def get_role_id_by_name(self, role_name):
        try:
            result = self._execute_query(
                "SELECT Role_ID FROM ROLE WHERE Role_Name = %s",
                (role_name,), fetch=True
            )
            return result[0][0] if result else None
        except Exception:
            return None

    # ── MEMBER MANAGEMENT ───────────────────────────────────────────────────

    def get_all_members(self):
        try:
            result = self._execute_query(
                "SELECT Member_ID, First_Name, Last_Name, Contact_Number FROM MEMBER",
                fetch=True
            )
            return result or []
        except Exception:
            return []

    def add_member(self, user_id, first_name, last_name, contact):
        """Uses the AddMember stored procedure."""
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                cursor.callproc("AddMember", (user_id, first_name, last_name, contact))
            conn.commit()
        except Exception as e:
            print(f"Add Member Error: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def search_members(self, keyword):
        try:
            keyword_like = f"%{keyword}%"
            query = """
                SELECT Member_ID, First_Name, Last_Name, Contact_Number
                FROM MEMBER
                WHERE CAST(Member_ID AS CHAR) = %s
                   OR First_Name LIKE %s
                   OR Last_Name  LIKE %s
            """
            result = self._execute_query(query, (keyword, keyword_like, keyword_like), fetch=True)
            return result or []
        except Exception:
            return []

    # ── GENERIC TABLE VIEWER ────────────────────────────────────────────────

    def get_table_columns(self, table_name):
        try:
            if table_name not in ALLOWED_TABLES:
                return []
            result = self._execute_query("""
                SELECT COLUMN_NAME FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (DB_NAME, table_name), fetch=True)
            return [row[0] for row in result] if result else []
        except Exception:
            return []

    def get_table_data(self, table_name):
        try:
            if table_name not in ALLOWED_TABLES:
                return []
            result = self._execute_query(f"SELECT * FROM {table_name}", fetch=True)
            return result or []
        except Exception:
            return []

    # ── OPERATIONS ──────────────────────────────────────────────────────────

    def add_subscription(self, type_id, member_id, start_date, end_date, status):
        self._execute_query("""
            INSERT INTO SUBSCRIPTION (Type_ID, Member_ID, Start_Date, End_Date, Status)
            VALUES (%s, %s, %s, %s, %s)
        """, (type_id, member_id, start_date, end_date, status))

    def add_payment(self, sub_id, amount, payment_date, method):
        self._execute_query("""
            INSERT INTO PAYMENT (Subscription_ID, Amount, Payment_Date, Method)
            VALUES (%s, %s, %s, %s)
        """, (sub_id, amount, payment_date, method))

    def add_subscription_with_payment(self, type_id, member_id, start_date,
                                       end_date, status, amount, method):
        """Atomic: subscription + payment together. Rolls back both if either fails."""
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO SUBSCRIPTION (Type_ID, Member_ID, Start_Date, End_Date, Status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (type_id, member_id, start_date, end_date, status))
                sub_id = cursor.lastrowid
                cursor.execute("""
                    INSERT INTO PAYMENT (Subscription_ID, Amount, Payment_Date, Method)
                    VALUES (%s, %s, CURDATE(), %s)
                """, (sub_id, amount, method))
            conn.commit()
            return True
        except Exception as e:
            print(f"Transaction failed, rolled back: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def add_attendance(self, member_id, check_in, check_out, date):
        self._execute_query("""
            INSERT INTO ATTENDANCE (Member_ID, Check_In_Time, Check_Out_Time, Date)
            VALUES (%s, %s, %s, %s)
        """, (member_id, check_in, check_out, date))

    # ── REPORTS ─────────────────────────────────────────────────────────────

    def get_payment_report(self):
        try:
            query = """
                SELECT
                    P.Payment_ID,
                    CONCAT(M.First_Name, ' ', M.Last_Name) AS Full_Name,
                    S.Start_Date,
                    S.End_Date,
                    P.Amount,
                    P.Payment_Date,
                    P.Method
                FROM PAYMENT P
                JOIN SUBSCRIPTION S ON P.Subscription_ID = S.Subscription_ID
                JOIN MEMBER M       ON S.Member_ID = M.Member_ID
                ORDER BY P.Payment_Date DESC
            """
            result = self._execute_query(query, fetch=True)
            return result or []
        except Exception:
            return []

    def get_revenue_stats(self):
        """Always returns (week_total, month_total) — never raises."""
        try:
            weekly_q  = "SELECT COALESCE(SUM(Amount), 0) FROM PAYMENT WHERE Payment_Date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
            monthly_q = "SELECT COALESCE(SUM(Amount), 0) FROM PAYMENT WHERE Payment_Date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"

            w = self._execute_query(weekly_q,  fetch=True)
            m = self._execute_query(monthly_q, fetch=True)

            # COALESCE in SQL handles NULL, but we double-check here too
            week_total  = float(w[0][0]) if w and w[0][0] is not None else 0.0
            month_total = float(m[0][0]) if m and m[0][0] is not None else 0.0
            return week_total, month_total
        except Exception:
            return 0.0, 0.0