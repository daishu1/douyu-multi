import sys
import os
import json
import pickle
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem, QTextEdit, QHBoxLayout, QFileDialog, QMessageBox, QCheckBox, QComboBox, QSpinBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl, QTimer, QDateTime
from PyQt5.QtNetwork import QNetworkCookie, QNetworkProxy

class BrowserWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("斗鱼多开")
        self.resize(800, 600)

        # 常规风格界面美化
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #333333;
                font-family: "Arial", "Helvetica", sans-serif;
                font-size: 13px;
            }

            QLineEdit, QSpinBox, QComboBox, QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 4px;
                color: #333333;
            }

            QPushButton {
                background-color: #007bff;
                color: #ffffff;
                border: 1px solid #0056b3;
                padding: 4px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #0056b3;
                color: #ffffff;
            }

            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                gridline-color: #e0e0e0;
            }

            QHeaderView::section {
                background-color: #f5f5f5;
                color: #333333;
                border: 1px solid #cccccc;
            }

            QCheckBox {
                padding-left: 5px;
            }
        """)

        self.browser_instances = []
        self.account_data = []
        self.categories = {
            "新秀区": "g_xingxiu",
            "颜值区": "g_yz",
            "才艺区": "g_caiyi"
        }
        self.current_category = None
        self.room_list = []
        self.current_room_index = 0
        self.is_auto_running = False
        self.main_layout = QVBoxLayout()
        self.control_layout = QHBoxLayout()
        self.room_number_label = QLabel("直播间:")
        self.room_number_input = QLineEdit()
        self.room_number_input.setPlaceholderText("请输入直播间号码")
        self.control_layout.addWidget(self.room_number_label)
        self.control_layout.addWidget(self.room_number_input)
        self.category_label = QLabel("分区:")
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.categories.keys())
        self.control_layout.addWidget(self.category_label)
        self.control_layout.addWidget(self.category_combo)
        self.dwell_time_label = QLabel("停留时间(秒):")
        self.dwell_time_input = QSpinBox()
        self.dwell_time_input.setRange(5, 300)
        self.dwell_time_input.setValue(30)
        self.control_layout.addWidget(self.dwell_time_label)
        self.control_layout.addWidget(self.dwell_time_input)
        self.add_browser_button = QPushButton("添加账户")
        self.add_browser_button.clicked.connect(self.add_new_browser)
        self.control_layout.addWidget(self.add_browser_button)
        self.change_room_button = QPushButton("切换直播间")
        self.change_room_button.clicked.connect(self.change_room)
        self.control_layout.addWidget(self.change_room_button)
        self.batch_import_button = QPushButton("导入Cookie")
        self.batch_import_button.clicked.connect(self.batch_import_cookies)
        self.control_layout.addWidget(self.batch_import_button)
        self.close_selected_button = QPushButton("关闭选中")
        self.close_selected_button.clicked.connect(self.close_selected_accounts)
        self.control_layout.addWidget(self.close_selected_button)
        self.stop_all_button = QPushButton("停止所有")
        self.stop_all_button.clicked.connect(self.stop_all_accounts)
        self.control_layout.addWidget(self.stop_all_button)
        self.batch_proxy_button = QPushButton("一键代理")
        self.batch_proxy_button.clicked.connect(self.batch_set_proxy)
        self.control_layout.addWidget(self.batch_proxy_button)
        self.auto_crawl_button = QPushButton("自动巡房")
        self.auto_crawl_button.clicked.connect(self.toggle_auto_crawl)
        self.control_layout.addWidget(self.auto_crawl_button)
        self.main_layout.addLayout(self.control_layout)
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(5)
        self.account_table.setHorizontalHeaderLabels(["选择", "账户", "直播间", "等级", "操作"])
        self.account_table.setRowCount(0)
        self.account_table.setColumnWidth(0, 30)
        self.account_table.setColumnWidth(1, 150)
        self.account_table.setColumnWidth(2, 100)
        self.account_table.setColumnWidth(3, 50)
        self.account_table.setColumnWidth(4, 100)
        self.main_layout.addWidget(self.account_table)
        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)
        self.load_saved_cookies()

    def save_cookies(self):
        cookie_data = []
        for account in self.account_data:
            if account["cookies"]:
                cookie_data.append({
                    "room": account["room"],
                    "cookies": account["cookies"]
                })
        try:
            with open(os.path.join(os.path.expanduser("~"), "douyu_cookies.pkl"), "wb") as f:
                pickle.dump(cookie_data, f)
        except:
            pass

    def load_saved_cookies(self):
        try:
            with open(os.path.join(os.path.expanduser("~"), "douyu_cookies.pkl"), "rb") as f:
                cookie_data = pickle.load(f)
            for data in cookie_data:
                self.room_number_input.setText(data["room"])
                self.add_new_browser()
                self.apply_cookie(len(self.account_data) - 1, "; ".join([f"{k}={v}" for k, v in data["cookies"].items()]), None)
        except:
            pass

    def add_new_browser(self):
        room_number = self.room_number_input.text().strip() or "default"
        save_directory = os.path.join(os.path.expanduser("~"), f"douyu_data_{room_number}_{len(self.browser_instances)}")
        try:
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)
        except:
            return
        browser = QWebEngineView()
        browser.setVisible(False)
        profile = QWebEngineProfile(save_directory, self)
        profile.setHttpCacheType(QWebEngineProfile.NoCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        page = QWebEnginePage(profile, browser)
        browser.setPage(page)
        url = QUrl("https://www.douyu.com/member/cp")
        browser.setUrl(url)
        self.browser_instances.append(browser)
        self.account_data.append({
            "browser": browser,
            "cookies": {},
            "room": room_number,
            "username": "未知",
            "level": "未知",
            "profile": profile,
            "fetched": False,
            "selected": False
        })
        self.update_table()
        browser.loadFinished.connect(lambda ok: self.fetch_account_info(browser) if ok else None)

    def fetch_account_info(self, browser):
        for account in self.account_data:
            if account["browser"] == browser and not account["fetched"]:
                js_script = """
                (function() {
                    let result = {username: '未知', level: '未知'};
                    const usernameElement = document.querySelector('.uname_con.clearfix h2');
                    if (usernameElement) result.username = usernameElement.textContent.trim();
                    const levelElement =

 document.querySelector('img[src*="userLevelIconV6"]');
                    if (levelElement) {
                        const src = levelElement.src;
                        const levelMatch = src.match(/newm3_lv(\\d+)/);
                        result.level = levelMatch ? `Lv${levelMatch[1]}` : '未知';
                    }
                    return result;
                })();
                """
                QTimer.singleShot(2000, lambda: browser.page().runJavaScript(js_script, lambda result: self.update_account_data(browser, result)))
                break

    def update_account_data(self, browser, result):
        for account in self.account_data:
            if account["browser"] == browser and not account["fetched"]:
                account["username"] = result.get("username", "未知")
                account["level"] = result.get("level", "未知")
                account["fetched"] = True
                self.save_cookies()
                break
        self.update_table()

    def update_table(self):
        self.account_table.setRowCount(len(self.account_data))
        for row, account in enumerate(self.account_data):
            checkbox = QCheckBox()
            checkbox.setChecked(account["selected"])
            checkbox.stateChanged.connect(lambda state, r=row: self.toggle_selection(r, state))
            self.account_table.setCellWidget(row, 0, checkbox)
            self.account_table.setItem(row, 1, QTableWidgetItem(account["username"]))
            self.account_table.setItem(row, 2, QTableWidgetItem(account["room"]))
            self.account_table.setItem(row, 3, QTableWidgetItem(account["level"]))
            operation_widget = QWidget()
            operation_layout = QHBoxLayout()
            operation_widget.setLayout(operation_layout)
            apply_cookie_button = QPushButton("Cookie")
            apply_cookie_button.clicked.connect(lambda _, r=row: self.open_cookie_dialog(r))
            operation_layout.addWidget(apply_cookie_button)
            apply_proxy_button = QPushButton("代理")
            apply_proxy_button.clicked.connect(lambda _, r=row: self.open_proxy_dialog(r))
            operation_layout.addWidget(apply_proxy_button)
            operation_layout.setContentsMargins(0, 0, 0, 0)
            self.account_table.setCellWidget(row, 4, operation_widget)

    def toggle_selection(self, row, state):
        self.account_data[row]["selected"] = state == 2

    def close_selected_accounts(self):
        for i in range(len(self.account_data) - 1, -1, -1):
            if self.account_data[i]["selected"]:
                browser = self.account_data[i]["browser"]
                browser.deleteLater()
                self.browser_instances.remove(browser)
                del self.account_data[i]
        self.save_cookies()
        self.update_table()

    def stop_all_accounts(self):
        self.is_auto_running = False
        self.auto_crawl_button.setText("自动巡房")
        for account in self.account_data:
            account["room"] = "无"
            browser = account["browser"]
            browser.setUrl(QUrl("https://www.douyu.com"))
        self.update_table()

    def open_cookie_dialog(self, row):
        dialog = QWidget()
        dialog.setWindowTitle("设置Cookie")
        layout = QVBoxLayout()
        cookie_input = QTextEdit()
        cookie_input.setPlaceholderText("格式：name1=value1; name2=value2")
        cookie_input.setFixedHeight(100)
        layout.addWidget(cookie_input)
        button_layout = QHBoxLayout()
        apply_button = QPushButton("应用")
        apply_button.clicked.connect(lambda: self.apply_cookie(row, cookie_input.toPlainText(), dialog))
        button_layout.addWidget(apply_button)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.close)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.resize(400, 200)
        dialog.show()

    def apply_cookie(self, row, cookie_string, dialog):
        cookie_string = cookie_string.strip()
        if not cookie_string:
            if dialog:
                QMessageBox.warning(self, "错误", "请输入有效Cookie")
            return
        cookies = {}
        try:
            for cookie in cookie_string.split(';'):
                cookie = cookie.strip()
                if not cookie or '=' not in cookie:
                    continue
                name, value = cookie.split('=', 1)
                cookies[name.strip()] = value.strip()
        except:
            if dialog:
                QMessageBox.warning(self, "错误", "Cookie格式错误")
            return
        account = self.account_data[row]
        account["cookies"] = cookies
        account["fetched"] = False
        browser = account["browser"]
        profile = account["profile"]
        cookie_store = profile.cookieStore()
        for name, value in cookies.items():
            cookie = QNetworkCookie(name.encode('utf-8'), value.encode('utf-8'))
            cookie.setDomain(".douyu.com")
            cookie.setPath("/")
            cookie.setExpirationDate(QDateTime.currentDateTime().addYears(1))
            cookie_store.setCookie(cookie, QUrl("https://www.douyu.com"))
        if dialog:
            dialog.close()
        QTimer.singleShot(2000, lambda: browser.setUrl(QUrl("https://www.douyu.com/member/cp")))
        browser.loadFinished.connect(lambda ok: self.fetch_account_info(browser) if ok else None)

    def open_proxy_dialog(self, row):
        dialog = QWidget()
        dialog.setWindowTitle("设置代理")
        layout = QVBoxLayout()
        proxy_input = QLineEdit()
        proxy_input.setPlaceholderText("代理 IP:端口（例：192.168.1.1:8080）")
        layout.addWidget(proxy_input)
        button_layout = QHBoxLayout()
        apply_button = QPushButton("应用")
        apply_button.clicked.connect(lambda: self.apply_proxy(row, proxy_input.text(), dialog))
        button_layout.addWidget(apply_button)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.close)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.resize(300, 150)
        dialog.show()

    def apply_proxy(self, row, proxy_info, dialog):
        account = self.account_data[row]
        browser = account["browser"]
        if proxy_info:
            try:
                ip, port = proxy_info.split(":")
                port = int(port)
                proxy = QNetworkProxy()
                proxy.setType(QNetworkProxy.HttpProxy)
                proxy.setHostName(ip)
                proxy.setPort(port)
                QNetworkProxy.setApplicationProxy(proxy)
            except ValueError:
                QMessageBox.warning(self, "错误", "请输入正确的 IP:端口 格式")
                return
        else:
            QNetworkProxy.setApplicationProxy(QNetworkProxy.NoProxy)
        dialog.close()
        QTimer.singleShot(2000, lambda: browser.setUrl(QUrl("https://www.douyu.com/member/cp")))
        browser.loadFinished.connect(lambda ok: self.fetch_account_info(browser) if ok else None)

    def batch_set_proxy(self):
        dialog = QWidget()
        dialog.setWindowTitle("一键设置代理")
        layout = QVBoxLayout()
        proxy_input = QLineEdit()
        proxy_input.setPlaceholderText("代理 IP:端口（例：192.168.1.1:8080）")
        layout.addWidget(proxy_input)
        button_layout = QHBoxLayout()
        apply_button = QPushButton("应用")
        apply_button.clicked.connect(lambda: self.apply_batch_proxy(proxy_input.text(), dialog))
        button_layout.addWidget(apply_button)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.close)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.resize(300, 150)
        dialog.show()

    def apply_batch_proxy(self, proxy_info, dialog):
        if proxy_info:
            try:
                ip, port = proxy_info.split(":")
                port = int(port)
                proxy = QNetworkProxy()
                proxy.setType(QNetworkProxy.HttpProxy)
                proxy.setHostName(ip)
                proxy.setPort(port)
                QNetworkProxy.setApplicationProxy(proxy)
            except ValueError:
                QMessageBox.warning(self, "错误", "请输入正确的 IP:端口 格式")
                return
        else:
            QNetworkProxy.setApplicationProxy(QNetworkProxy.NoProxy)
        for account in self.account_data:
            browser = account["browser"]
            QTimer.singleShot(2000, lambda: browser.setUrl(QUrl("https://www.douyu.com/member/cp")))
            browser.loadFinished.connect(lambda ok: self.fetch_account_info(browser) if ok else None)
        dialog.close()

    def batch_import_cookies(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择Cookie文件", "", "Text Files (*.txt);;JSON Files (*.json)")
        if not file_name:
            return
        cookies_list = []
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                if file_name.endswith('.json'):
                    cookies_list = json.load(f)
                else:
                    cookies_list = [line.strip() for line in f if line.strip()]
        except:
            QMessageBox.warning(self, "错误", "读取文件失败")
            return
        for cookie_string in cookies_list:
            if isinstance(cookie_string, dict):
                cookie_string = "; ".join([f"{k}={v}" for k, v in cookie_string.items()])
            self.add_new_browser()
            self.apply_cookie(len(self.account_data) - 1, cookie_string, None)

    def change_room(self):
        room_number = self.room_number_input.text().strip()
        if not room_number:
            QMessageBox.warning(self, "错误", "请输入直播间号码")
            return
        selected_accounts = [account for account in self.account_data if account["selected"]]
        if not selected_accounts:
            QMessageBox.warning(self, "错误", "请至少选择一个账户")
            return
        for account in selected_accounts:
            account["room"] = room_number
            browser = account["browser"]
            browser.setUrl(QUrl(f"https://www.douyu.com/{room_number}"))
        self.update_table()

    def toggle_auto_crawl(self):
        if self.is_auto_running:
            self.is_auto_running = False
            self.auto_crawl_button.setText("自动巡房")
        else:
            self.current_category = self.categories[self.category_combo.currentText()]
            selected_accounts = [account for account in self.account_data if account["selected"]]
            if not selected_accounts:
                QMessageBox.warning(self, "错误", "请至少选择一个账户")
                return
            self.is_auto_running = True
            self.auto_crawl_button.setText("停止巡房")
            self.fetch_room_list()

    def fetch_room_list(self):
        if not self.is_auto_running:
            return
        browser = self.account_data[0]["browser"]
        js_script = """
        (function() {
            let rooms = [];
            const roomElements = document.querySelectorAll('.layout-Cover-item a[href*="/"]');
            roomElements.forEach(el => {
                const href = el.getAttribute('href');
                const match = href.match(/\/(\\d+)/);
                if (match) rooms.push(match[1]);
            });
            return rooms;
        })();
        """
        browser.setUrl(QUrl(f"https://www.douyu.com/{self.current_category}"))
        browser.loadFinished.connect(lambda ok: self.handle_room_list(browser, js_script) if ok else None)

    def handle_room_list(self, browser, js_script):
        if not self.is_auto_running:
            return
        browser.page().runJavaScript(js_script, lambda result: self.start_auto_crawl(result))

    def start_auto_crawl(self, rooms):
        if not self.is_auto_running or not rooms:
            return
        self.room_list = rooms
        self.current_room_index = 0
        self.visit_next_room()

    def visit_next_room(self):
        if not self.is_auto_running:
            return
        if self.current_room_index >= len(self.room_list):
            self.current_room_index = 0
            self.fetch_room_list()
            return
        room_number = self.room_list[self.current_room_index]
        for account in self.account_data:
            if account["selected"]:
                account["room"] = room_number
                browser = account["browser"]
                browser.setUrl(QUrl(f"https://www.douyu.com/{room_number}"))
        self.update_table()
        self.current_room_index += 1
        dwell_time = self.dwell_time_input.value() * 1000
        QTimer.singleShot(dwell_time, self.visit_next_room)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())