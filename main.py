import sys
import csv
import os

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QLineEdit, QPushButton,
                              QMessageBox, QTableWidget, QTableWidgetItem,
                              QHeaderView, QFileDialog, QFrame, QGridLayout,
                              QStackedWidget, QSizePolicy)
from PyQt6.QtGui import QPainter, QBrush, QColor, QPolygon, QPixmap, QIcon
from PyQt6.QtCore import Qt, QPoint

from model import DatabaseManager


class TriangleWidget(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor("#DA0037")))
        painter.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        points = QPolygon([QPoint(w // 2, 0), QPoint(0, h), QPoint(w, h)])
        painter.drawPolygon(points)


class LoginWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle("Gym — Login")
        self.setFixedSize(350, 450)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.logo = QLabel()
        self.logo.setFixedSize(180, 150)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path  = os.path.join(script_dir, "AURAGYM_LOGO.png")

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.logo.setPixmap(pixmap.scaled(
                180, 150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.logo.setText("GYM DATABASE")
            self.logo.setStyleSheet("font-size: 24px; color: #DA0037; font-weight: bold;")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)


        main_layout.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.username_input)
        main_layout.addWidget(self.password_input)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.login_btn)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.apply_styles()

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Login Error",
                                "Please enter both username and password.")
            return

        try:
            user_data = self.db.verify_login(username, password)
        except Exception as e:
            QMessageBox.critical(self, "Database Error",
                                 f"Could not reach the database.\n\n"
                                 f"Make sure XAMPP is running and MariaDB is active.\n\n"
                                 f"Details: {str(e)}")
            return

        if not user_data:
            QMessageBox.warning(self, "Login Failed",
                                "Incorrect username or password.")
            return

        user_id, role_id, role_name = user_data
        try:
            self.dashboard = DashboardWindow(self.db, user_id, role_name)
            self.dashboard.show()
            self.close()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Dashboard Error",
                                 f"Login succeeded but the dashboard failed to open.\n\n"
                                 f"{traceback.format_exc()}")

    def apply_styles(self):
        self.setStyleSheet("""
        QWidget {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #171717, stop:1 #444444
            );
            color: #EDEDED;
            font-family: Segoe UI;
            font-size: 14px;
        }
        QLineEdit {
            background-color: #444444;
            border: none;
            border-radius: 12px;
            padding: 10px;
            color: #EDEDED;
        }
        QLineEdit:focus { border: 2px solid #DA0037; }
        QPushButton {
            background-color: #DA0037;
            border-radius: 12px;
            padding: 10px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #ff1a4d; }
        """)


class DashboardWindow(QMainWindow):
    def __init__(self, db_manager, current_user_id, current_role):
        super().__init__()
        self.db              = db_manager
        self.current_user_id = current_user_id
        self.current_role    = current_role
        self.pages           = {}
        self.ADMIN_ROLES     = {"Admin", "Owner"}

        self.setWindowTitle(f"Gym Dashboard — {self.current_role}")
        self.resize(1350, 780)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.content_stack = QStackedWidget()
        right_wrapper      = QWidget()
        right_layout       = QVBoxLayout(right_wrapper)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(16)

        self.header = self.create_header()
        right_layout.addWidget(self.header)
        right_layout.addWidget(self.content_stack)

        root.addWidget(self.create_sidebar())
        root.addWidget(right_wrapper)

        self.build_pages()
        self.apply_dashboard_styles()
        self.show_page("Members")

    # ── HELPERS ─────────────────────────────────────────────────────────────

    def make_input(self, placeholder):
        w = QLineEdit()
        w.setPlaceholderText(placeholder)
        return w

    def clear_fields(self, *fields):
        for field in fields:
            field.clear()

    def create_page_wrapper(self):
        page   = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        return page, layout

    def create_card(self, title):
        card   = QFrame()
        card.setObjectName("contentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        label  = QLabel(title)
        label.setObjectName("cardTitle")
        layout.addWidget(label)
        return card, layout

    def style_table(self, table):
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        return table

    def create_table_card(self, title, columns=None):
        card, layout = self.create_card(title)
        table        = self.style_table(QTableWidget())
        if columns:
            table.setColumnCount(len(columns))
            table.setHorizontalHeaderLabels(columns)
        layout.addWidget(table)
        return card, table

    def add_page(self, name, widget):
        self.pages[name] = widget
        self.content_stack.addWidget(widget)

    def fill_table(self, table, data, columns=None):
        """Safe fill — never crashes on None or empty data."""
        try:
            table.setRowCount(0)
            if columns:
                table.setColumnCount(len(columns))
                table.setHorizontalHeaderLabels(columns)
                table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            if data:
                for row_num, row_data in enumerate(data):
                    table.insertRow(row_num)
                    for col_num, cell_data in enumerate(row_data):
                        table.setItem(row_num, col_num, QTableWidgetItem(str(cell_data) if cell_data is not None else ""))
        except Exception as e:
            print(f"Table fill error: {e}")

    # ── SIDEBAR ─────────────────────────────────────────────────────────────

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(270)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(14)

        brand = QLabel("Gym")
        brand.setObjectName("brandLabel")
        layout.addWidget(brand)
        layout.addSpacing(10)

        groups = [("Management", ["Members"])]
        if self.current_role in self.ADMIN_ROLES:
            groups[0][1].append("Staff")
            groups += [
                ("Operations", ["Attendance", "Payments", "Subscriptions"]),
                ("Reports",    ["Financial Reports"]),
                ("Database",   ["Role Table", "Membership Table"]),
            ]

        for i, (section, buttons) in enumerate(groups):
            if i:
                layout.addSpacing(8)
            layout.addWidget(self.make_sidebar_section(section))
            for name in buttons:
                layout.addWidget(self.make_nav_button(name))

        layout.addStretch()

        footer        = QFrame()
        footer.setObjectName("sidebarCard")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(14, 14, 14, 14)

        title = QLabel("Gym System")
        title.setObjectName("sidebarCardTitle")
        text  = QLabel("Manage gym records, operations, and reports in one place.")
        text.setWordWrap(True)
        text.setObjectName("sidebarCardText")

        footer_layout.addWidget(title)
        footer_layout.addWidget(text)
        layout.addWidget(footer)
        return sidebar

    def make_sidebar_section(self, text):
        label = QLabel(text)
        label.setObjectName("sidebarSection")
        return label

    def make_nav_button(self, name):
        btn = QPushButton(name)
        btn.setObjectName("navButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked=False, page=name: self.show_page(page))
        return btn

    # ── HEADER ──────────────────────────────────────────────────────────────

    def create_header(self):
        header = QFrame()
        header.setObjectName("headerCard")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 16, 20, 16)

        left = QVBoxLayout()
        self.page_title    = QLabel("Dashboard")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("Welcome to the Gym Management System")
        self.page_subtitle.setObjectName("pageSubtitle")
        left.addWidget(self.page_title)
        left.addWidget(self.page_subtitle)

        badge = QLabel(f"User ID: {self.current_user_id} | {self.current_role}")
        badge.setObjectName("userBadge")

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setObjectName("logoutButton")
        self.logout_btn.setFixedWidth(110)
        self.logout_btn.clicked.connect(self.handle_logout)

        layout.addLayout(left)
        layout.addStretch()
        layout.addWidget(badge)
        layout.addSpacing(10)
        layout.addWidget(self.logout_btn)
        return header

    def show_page(self, page_name):
        if page_name in self.pages:
            self.content_stack.setCurrentWidget(self.pages[page_name])
            self.page_title.setText(page_name)
            self.page_subtitle.setText(f"Manage {page_name.lower()} here.")

    # ── PAGE BUILDING ────────────────────────────────────────────────────────

    def build_pages(self):
        self.add_page("Members", self.create_member_page())

        if self.current_role in self.ADMIN_ROLES:
            pages = {
                "Staff":             self.create_user_page(),
                "Attendance":        self.create_attendance_page(),
                "Payments":          self.create_payment_page(),
                "Subscriptions":     self.create_subscription_page(),
                "Financial Reports": self.create_reports_page(),
                "Role Table":        self.create_admin_table_page("ROLE"),
                "Membership Table":  self.create_admin_table_page("MEMBERSHIP"),
            }
            for name, widget in pages.items():
                self.add_page(name, widget)

    def make_form_page(self, form_title, table_title, fields, button_text,
                       button_handler, table_attr, table_columns=None, refresh_callback=None):
        page, root = self.create_page_wrapper()

        form_card, form_layout = self.create_card(form_title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        for i, (attr, placeholder) in enumerate(fields):
            widget = self.make_input(placeholder)
            setattr(self, attr, widget)
            grid.addWidget(widget, i // 2, i % 2)

        btn = QPushButton(button_text)
        btn.clicked.connect(button_handler)

        row = (len(fields) + 1) // 2
        if len(fields) % 2 == 1:
            grid.addWidget(btn, row - 1, 1)
        else:
            grid.addWidget(btn, row, 0, 1, 2)

        form_layout.addLayout(grid)

        table_card, table = self.create_table_card(table_title, table_columns)
        setattr(self, table_attr, table)

        root.addWidget(form_card)
        root.addWidget(table_card)

        if refresh_callback:
            try:
                refresh_callback()
            except Exception as e:
                print(f"Refresh error on page build: {e}")

        return page

    # ── PAGES ────────────────────────────────────────────────────────────────

    def create_member_page(self):
        page, root = self.create_page_wrapper()

        search_card, search_layout = self.create_card("Search Members")
        search_row = QHBoxLayout()
        self.search_input = self.make_input("Search by Name or Member ID...")
        search_btn        = QPushButton("Search")
        clear_btn         = QPushButton("Clear")
        search_btn.clicked.connect(self.handle_search)
        clear_btn.clicked.connect(self.handle_clear_search)
        search_row.addWidget(self.search_input)
        search_row.addWidget(search_btn)
        search_row.addWidget(clear_btn)
        search_layout.addLayout(search_row)

        form_page = self.make_form_page(
            "Member Registration", "Member Records",
            [
                ("fname_input",   "First Name"),
                ("lname_input",   "Last Name"),
                ("contact_input", "Contact Number"),
            ],
            "Register Member",
            self.handle_add_member,
            "member_table",
            ["ID", "First Name", "Last Name", "Contact"],
            self.refresh_member_table
        )

        root.addWidget(search_card)
        root.addWidget(form_page)
        return page

    def create_user_page(self):
        return self.make_form_page(
            "Create Staff Account", "Staff Accounts",
            [
                ("u_name", "New Username"),
                ("u_pass", "New Password"),
                ("u_role", "Role Name (Admin / Owner / Receptionist)"),
            ],
            "Create Account",
            self.handle_add_user,
            "user_table",
            refresh_callback=lambda: self.refresh_generic_table("USER", self.user_table)
        )

    def create_attendance_page(self):
        return self.make_form_page(
            "Attendance Entry", "Attendance Records",
            [
                ("att_member_id", "Member ID"),
                ("att_check_in",  "Check In (HH:MM)"),
                ("att_check_out", "Check Out (HH:MM)"),
                ("att_date",      "Date (YYYY-MM-DD)"),
            ],
            "Log Attendance",
            self.handle_add_attendance,
            "attendance_table",
            refresh_callback=lambda: self.refresh_generic_table("ATTENDANCE", self.attendance_table)
        )

    def create_payment_page(self):
        return self.make_form_page(
            "Payment Entry", "Payment Records",
            [
                ("pay_sub_id", "Subscription ID"),
                ("pay_amount", "Amount"),
                ("pay_date",   "Date (YYYY-MM-DD)"),
                ("pay_method", "Method (Cash/E-Wallet)"),
            ],
            "Log Payment",
            self.handle_add_payment,
            "payment_table",
            refresh_callback=lambda: self.refresh_generic_table("PAYMENT", self.payment_table)
        )

    def create_subscription_page(self):
        return self.make_form_page(
            "Subscription Entry", "Subscription Records",
            [
                ("sub_type_id",   "Type ID (1-3)"),
                ("sub_member_id", "Member ID"),
                ("sub_start",     "Start (YYYY-MM-DD)"),
                ("sub_end",       "End (YYYY-MM-DD)"),
                ("sub_status",    "Status (1=Active)"),
            ],
            "Add Subscription",
            self.handle_add_subscription,
            "subscription_table",
            refresh_callback=lambda: self.refresh_generic_table("SUBSCRIPTION", self.subscription_table)
        )

    def create_reports_page(self):
        page, root = self.create_page_wrapper()

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        def make_stat_card(title_text):
            card   = QFrame()
            card.setObjectName("statCard")
            layout = QVBoxLayout(card)
            title  = QLabel(title_text)
            title.setObjectName("statTitle")
            value  = QLabel("₱0.00")
            value.setObjectName("statValue")
            layout.addWidget(title)
            layout.addWidget(value)
            return card, value

        monthly_card, self.monthly_label = make_stat_card("Monthly Revenue")
        total_card,   self.total_label   = make_stat_card("Total Revenue")
        stats_row.addWidget(monthly_card)
        stats_row.addWidget(total_card)

        table_card, self.report_table = self.create_table_card(
            "Transaction History",
            ["Pay ID", "Member Name", "Sub Start", "Sub End", "Amount", "Pay Date", "Method"]
        )

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        refresh_btn = QPushButton("Update Reports")
        refresh_btn.clicked.connect(self.refresh_reports)
        export_btn  = QPushButton("Export CSV")
        export_btn.clicked.connect(self.handle_export_csv)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(export_btn)

        root.addLayout(stats_row)
        root.addWidget(table_card)
        root.addLayout(btn_row)

        # Safe call — model.get_revenue_stats() never raises
        try:
            self.refresh_reports()
        except Exception as e:
            print(f"Reports page initial load error: {e}")

        return page

    def create_admin_table_page(self, table_name):
        page, root = self.create_page_wrapper()
        card, layout = self.create_card(f"{table_name} Database View")
        table        = self.style_table(QTableWidget())

        try:
            columns = self.db.get_table_columns(table_name)
            data    = self.db.get_table_data(table_name)
            self.fill_table(table, data, columns)
        except Exception as e:
            print(f"Admin table load error for {table_name}: {e}")

        layout.addWidget(table)
        root.addWidget(card)
        return page

    # ── DATA REFRESH ─────────────────────────────────────────────────────────

    def refresh_generic_table(self, table_name, table_widget):
        try:
            self.fill_table(
                table_widget,
                self.db.get_table_data(table_name),
                self.db.get_table_columns(table_name)
            )
        except Exception as e:
            print(f"Refresh error ({table_name}): {e}")

    def refresh_member_table(self):
        try:
            self.fill_table(self.member_table, self.db.get_all_members())
        except Exception as e:
            print(f"Member table refresh error: {e}")

    def refresh_reports(self):
        try:
            month, total = self.db.get_revenue_stats()
            self.monthly_label.setText(f"₱{month:,.2f}")
            self.total_label.setText(f"₱{total:,.2f}")
            self.fill_table(self.report_table, self.db.get_payment_report())
        except Exception as e:
            print(f"Reports refresh error: {e}")
            self.weekly_label.setText("₱0.00")
            self.monthly_label.setText("₱0.00")

    # ── HANDLERS ─────────────────────────────────────────────────────────────

    def handle_search(self):
        try:
            keyword = self.search_input.text().strip()
            if not keyword:
                self.refresh_member_table()
                return
            results = self.db.search_members(keyword)
            self.fill_table(self.member_table, results)
            if not results:
                QMessageBox.information(self, "No Results",
                                        f"No members found for '{keyword}'.")
        except Exception as e:
            QMessageBox.warning(self, "Search Error", str(e))

    def handle_clear_search(self):
        self.search_input.clear()
        self.refresh_member_table()

    def handle_add_member(self):
        try:
            fname   = self.fname_input.text().strip()
            lname   = self.lname_input.text().strip()
            contact = self.contact_input.text().strip()

            if not fname or not lname:
                QMessageBox.warning(self, "Error", "First and Last name are required.")
                return

            self.db.add_member(self.current_user_id, fname, lname, contact)
            self.refresh_member_table()
            self.fname_input.clear()
            self.lname_input.clear()
            self.contact_input.clear()
            self.clear_fields(self.fname_input, self.lname_input, self.contact_input)
        except Exception as e:
            QMessageBox.warning(self, "Add Member Error", str(e))

    def handle_add_user(self):
        try:
            role_name = self.u_role.text().strip()
            role_id   = self.db.get_role_id_by_name(role_name)

            if not role_id:
                QMessageBox.warning(self, "Invalid Role",
                                    f"'{role_name}' is not a valid role.\n"
                                    f"Valid roles: Admin, Owner, Receptionist")
                return

            self.db.add_user(self.u_name.text().strip(), self.u_pass.text(), role_id)
            self.refresh_generic_table("USER", self.user_table)
            self.clear_fields(self.u_name, self.u_pass, self.u_role)
        except Exception as e:
            QMessageBox.warning(self, "Add User Error", str(e))

    def handle_add_attendance(self):
        try:
            self.db.add_attendance(
                self.att_member_id.text(), self.att_check_in.text(),
                self.att_check_out.text(), self.att_date.text()
            )
            self.refresh_generic_table("ATTENDANCE", self.attendance_table)
            self.clear_fields(self.att_member_id, self.att_check_in,
                              self.att_check_out, self.att_date)
        except Exception as e:
            QMessageBox.warning(self, "Attendance Error", str(e))

    def handle_add_payment(self):
        try:
            self.db.add_payment(
                self.pay_sub_id.text(),
                self.pay_amount.text(),
                self.pay_date.text(),
                self.pay_method.text()
            )
            self.refresh_generic_table("PAYMENT", self.payment_table)
            self.clear_fields(self.pay_sub_id, self.pay_amount,
                              self.pay_date, self.pay_method)
        except Exception as e:
            QMessageBox.warning(self, "Payment Error", str(e))

    def handle_add_subscription(self):
        try:
            self.db.add_subscription(
                self.sub_type_id.text(), self.sub_member_id.text(),
                self.sub_start.text(), self.sub_end.text(), self.sub_status.text()
            )
            self.refresh_generic_table("SUBSCRIPTION", self.subscription_table)
            self.clear_fields(self.sub_type_id, self.sub_member_id,
                              self.sub_start, self.sub_end, self.sub_status)
        except Exception as e:
            QMessageBox.warning(self, "Subscription Error", str(e))

    def handle_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Report", "Gym_Report.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                with open(path, mode='w', newline='') as file:
                    writer  = csv.writer(file)
                    headers = [
                        self.report_table.horizontalHeaderItem(col).text()
                        for col in range(self.report_table.columnCount())
                    ]
                    writer.writerow(headers)
                    for row in range(self.report_table.rowCount()):
                        writer.writerow([
                            self.report_table.item(row, col).text()
                            if self.report_table.item(row, col) else ""
                            for col in range(self.report_table.columnCount())
                        ])
                QMessageBox.information(self, "Success", f"Report exported to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Could not save file: {str(e)}")

    def handle_logout(self):
        self.login_window = LoginWindow(self.db)
        self.login_window.show()
        self.close()

    # ── STYLES ───────────────────────────────────────────────────────────────

    def apply_dashboard_styles(self):
        self.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #171717;
            color: #EDEDED;
            font-family: Segoe UI;
            font-size: 14px;
        }
        QLabel {
            background-color: transparent;
            border: none;
        }
        QFrame#sidebar {
            background-color: #111111;
            border-top-right-radius: 24px;
            border-bottom-right-radius: 24px;
            border-right: 1px solid #444444;
        }
        QLabel#brandLabel { color: #EDEDED; font-size: 28px; font-weight: 800; padding: 8px 4px; }
        QLabel#sidebarSection { color: #DA0037; font-size: 12px; font-weight: 700; padding-top: 8px; padding-left: 6px; }
        QPushButton#navButton {
            background-color: transparent; color: #EDEDED;
            border: none; border-radius: 12px;
            text-align: left; padding: 12px 14px; font-weight: 600;
        }
        QPushButton#navButton:hover { background-color: #444444; }
        QFrame#sidebarCard { background-color: #1E1E1E; border: 1px solid #444444; border-radius: 16px; }
        QLabel#sidebarCardTitle { color: #EDEDED; font-size: 16px; font-weight: 700; }
        QLabel#sidebarCardText  { color: #CFCFCF; font-size: 12px; }
        QFrame#headerCard {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #444444, stop:1 #171717);
            border: 1px solid #444444; border-radius: 20px;
        }
        QLabel#pageTitle    { color: #EDEDED; font-size: 24px; font-weight: 800; }
        QLabel#pageSubtitle { color: #BFBFBF; font-size: 13px; font-weight: 500; }
        QLabel#userBadge {
            background-color: #444444; color: #EDEDED;
            border: 1px solid #5A5A5A; border-radius: 12px;
            padding: 8px 12px; font-weight: 700;
        }
        QPushButton#logoutButton {
            background-color: #DA0037; color: #EDEDED;
            border: none; border-radius: 12px; padding: 10px 14px; font-weight: bold;
        }
        QPushButton#logoutButton:hover { background-color: #F20A45; }
        QFrame#contentCard, QFrame#statCard {
            background-color: #222222; border: 1px solid #444444; border-radius: 20px;
        }
        QLabel#cardTitle { color: #EDEDED; font-size: 18px; font-weight: 800; }
        QLabel#statTitle { color: #BFBFBF; font-size: 13px; font-weight: 600; }
        QLabel#statValue { color: #DA0037; font-size: 28px; font-weight: 800; }
        QLineEdit {
            background-color: #171717; border: 1px solid #444444;
            border-radius: 12px; padding: 10px 12px; color: #EDEDED;
        }
        QLineEdit:focus { border: 2px solid #DA0037; background-color: #1E1E1E; }
        QPushButton {
            background-color: #DA0037; color: #EDEDED;
            border: none; border-radius: 12px; padding: 10px 16px; font-weight: 700;
        }
        QPushButton:hover   { background-color: #F20A45; }
        QPushButton:pressed { background-color: #B8002E; }
        QTableWidget {
            background-color: #171717; color: #EDEDED;
            border: 1px solid #444444; border-radius: 14px;
            alternate-background-color: #202020;
            selection-background-color: #DA0037;
            selection-color: #FFFFFF; gridline-color: transparent;
        }
        QHeaderView::section {
            background-color: #444444; color: #EDEDED;
            padding: 12px; border: none; font-weight: 800;
        }
        QScrollBar:vertical { background: #171717; width: 10px; margin: 0px; border-radius: 5px; }
        QScrollBar::handle:vertical { background: #444444; min-height: 20px; border-radius: 5px; }
        QScrollBar::handle:vertical:hover { background: #DA0037; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path  = os.path.join(script_dir, "AURAGYM_LOGO.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    try:
        database = DatabaseManager()
        database.migrate_plain_passwords()
    except Exception as e:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Startup Error")
        msg.setText("Could not connect to the database.")
        msg.setInformativeText("Make sure XAMPP is running and MariaDB is active.")
        msg.setDetailedText(str(e))
        msg.exec()
        sys.exit(1)

    login_window = LoginWindow(database)
    login_window.show()
    sys.exit(app.exec())