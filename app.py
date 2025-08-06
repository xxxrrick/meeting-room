import os
import shutil
import time
import sqlite3
import requests
from datetime import datetime
from threading import Thread
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os

def backup_to_gofile(filepath):
    try:
        # Step 1: 取得伺服器清單
        server_res = requests.get("https://api.gofile.io/servers")
        server_res.raise_for_status()
        servers = server_res.json()["data"]["servers"]
        server = servers[0]["name"]  # 正確取得伺服器名稱

        # Step 2: 上傳檔案
        with open(filepath, 'rb') as f:
            upload_url = f"https://{server}.gofile.io/uploadFile"
            res = requests.post(upload_url, files={'file': f})
            res.raise_for_status()
            result = res.json()

        if result["status"] == "ok":
            link = result["data"]["downloadPage"]
            print("✅ 備份成功，下載連結：", link)
            return link
        else:
            print("❌ 上傳失敗：", result)
            return None

    except Exception as e:
        print("❌ 上傳過程出錯：", str(e))
        return None

app = Flask(__name__)
app.secret_key = 'your-secret-key'
GOFILE_TOKEN = "RjLjWdXaDBBw4uhiOKQhDeOevHyyYvm2"  # ← 請替換為你的 GoFile API token
GOFILE_PARENT_FOLDER = None  # 如果你有特定上傳目錄ID可以填入，否則保持 None

def restore_latest_from_gofile():
    try:
        # Step 1: 取得帳戶檔案清單
        payload = {"token": GOFILE_TOKEN}
        if GOFILE_PARENT_FOLDER:
            payload["folderId"] = GOFILE_PARENT_FOLDER

        res = requests.get("https://api.gofile.io/getContent", params=payload)
        files = res.json()["data"]["contents"]

        # Step 2: 篩選所有 .db 檔案，取最新
        db_files = []
        for file_id, info in files.items():
            if info["name"].endswith(".db"):
                db_files.append((info["name"], info["directLink"]))

        if not db_files:
            print("❌ GoFile 中沒有找到 .db 備份檔")
            return

        # Step 3: 根據檔名排序（假設檔名含 timestamp），選擇最新
        db_files.sort(reverse=True)
        latest_name, latest_url = db_files[0]
        print(f"🕓 正在還原 GoFile 最新備份：{latest_name}")

        # Step 4: 下載還原
        response = requests.get(latest_url, stream=True)
        if response.status_code == 200:
            with open(DB_PATH, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            print("✅ 成功還原 GoFile 備份：", latest_name)
        else:
            print("❌ 無法下載備份檔案：", response.status_code)
    except Exception as e:
        print("❌ 自動還原 GoFile 備份錯誤：", str(e))
# === 常數設定 ===
RENDER_URL = "https://your-app.onrender.com"
DB_PATH = "data/database.db"
BACKUP_FOLDER = "backups"
DRIVE_API_TRIGGER_URL = "https://your-api-endpoint/upload"

os.makedirs("data", exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)
def restore_from_gofile(download_url):
    try:
        # 從 GoFile 下載最新的 .db 檔案
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            with open(DB_PATH, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            print("✅ 已成功從 GoFile 還原資料庫")
        else:
            print("❌ 無法下載 GoFile 備份，狀態碼：", response.status_code)
    except Exception as e:
        print("❌ 錯誤發生於 GoFile 還原：", str(e))

def backup_and_upload_overwrite():
    os.makedirs(BACKUP_FOLDER, exist_ok=True)

    # 刪除所有舊備份，只保留這次
    for f in os.listdir(BACKUP_FOLDER):
        if f.endswith(".db"):
            os.remove(os.path.join(BACKUP_FOLDER, f))

    # 建立新備份
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = os.path.join(BACKUP_FOLDER, f"backup_{timestamp}.db")
    shutil.copyfile(DB_PATH, backup_path)

    # 傳送 API（GoFile 或其他雲端）
    try:
        requests.post(DRIVE_API_TRIGGER_URL, json={"filename": backup_path})
    except Exception as e:
        print("❌ 上傳失敗：", str(e))  # 加上 str(e)

    return backup_path



def ping_render():
    try:
        requests.get(RENDER_URL, timeout=5)
    except:
        pass

def restore_if_needed():
    def is_empty(db_file):
        try:
            with sqlite3.connect(db_file) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cur.fetchall()
                for table in tables:
                    if cur.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0] > 0:
                        return False
                return True
        except:
            return True

    if not os.path.exists(DB_PATH) or is_empty(DB_PATH):
        backups = sorted([f for f in os.listdir(BACKUP_FOLDER) if f.endswith(".db")], reverse=True)
        if backups:
            latest = os.path.join(BACKUP_FOLDER, backups[0])
            shutil.copyfile(latest, DB_PATH)


def initialize_system():
    Thread(target=ping_render).start()

    # 自動從 GoFile 還原（如果 DB 不存在）
    if not os.path.exists(DB_PATH):
        restore_latest_from_gofile()
    else:
        restore_if_needed()


def on_user_action():
    def backup_and_upload_to_gofile():
        # 移除舊備份
        for f in os.listdir(BACKUP_FOLDER):
            if f.endswith(".db"):
                os.remove(os.path.join(BACKUP_FOLDER, f))

        # 建立新備份
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = os.path.join(BACKUP_FOLDER, f"backup_{timestamp}.db")
        shutil.copyfile(DB_PATH, backup_path)

        # 上傳到 GoFile
        backup_to_gofile(backup_path)

    Thread(target=backup_and_upload_to_gofile).start()


app = Flask(__name__)
app.secret_key = 'your-secret-key'
ADMIN_PASSWORD = '0000'

DB_PATH = 'data/database.db'
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            user TEXT NOT NULL,
            cancel_code TEXT
        );''')
init_db()

@app.route('/')
def index():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    with sqlite3.connect(DB_PATH) as conn:
        bookings = conn.execute("SELECT * FROM bookings ORDER BY date, start_time").fetchall()
    future = [b for b in bookings if f"{b[2]} {b[4]}" >= now]
    past = [b for b in bookings if f"{b[2]} {b[4]}" < now]
    return render_template("index.html", bookings=future, history=past, admin=session.get('admin'))

@app.route('/book', methods=['POST'])
def book():
    room = request.form['room']
    date = request.form['date']
    start = request.form['start_time']
    end = request.form['end_time']
    user = request.form['user']
    code = request.form['cancel_code']
    repeat_weeks = int(request.form.get('repeat_weeks', '0') or 0)
    now = datetime.now()

    if not date or not start or not end or not user or not code:
        flash("所有欄位皆為必填", "error")
        return redirect(url_for('index'))
    if start >= end:
        flash("起始時間不得晚於結束時間", "error")
        return redirect(url_for('index'))
    start_dt = datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M")
    if start_dt < now:
        flash("無法預約過去時間", "error")
        return redirect(url_for('index'))

    def is_conflict(d):
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute('''SELECT * FROM bookings WHERE room=? AND date=?
                AND ((start_time < ? AND end_time > ?) OR
                     (start_time < ? AND end_time > ?) OR
                     (start_time >= ? AND start_time < ?))''',
                (room, d, end, end, start, start, start, end)).fetchone()
            return bool(row)

    def insert(d):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO bookings (room, date, start_time, end_time, user, cancel_code) VALUES (?, ?, ?, ?, ?, ?)",
                         (room, d, start, end, user, code))
            conn.commit()

    for i in range(repeat_weeks + 1):
        new_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(weeks=i)).strftime("%Y-%m-%d")
        if is_conflict(new_date):
            flash(f"{new_date} 預約時段衝突", "error")
            return redirect(url_for('index'))
        insert(new_date)

    flash("✅ 預約成功", "success")
    on_user_action()
    return redirect(url_for('index'))

@app.route('/cancel/<int:id>', methods=['GET', 'POST'])
def cancel(id):
    if session.get('admin'):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM bookings WHERE id=?", (id,))
            flash("✅ 管理員已取消預約", "success")
            on_user_action()
    elif request.method == 'POST':
        code = request.form.get('code')
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT cancel_code FROM bookings WHERE id=?", (id,)).fetchone()
            if row and row[0] == code:
                conn.execute("DELETE FROM bookings WHERE id=?", (id,))
                flash("✅ 預約已取消", "success")
                on_user_action()
            else:
                flash("❌ 密碼錯誤", "error")
        return redirect(url_for('index'))
    else:
        return f'''
            <h3>輸入取消密碼：</h3>
            <form method="POST">
                <input type="password" name="code" required>
                <button type="submit">確定取消</button>
            </form>
        '''
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            flash("✅ 管理員登入成功", "success")
            return redirect(url_for('index'))
        flash("❌ 密碼錯誤", "error")
    return '''
        <h2>管理員登入</h2>
        <form method="POST">
            密碼：<input type="password" name="password">
            <button type="submit">登入</button>
        </form><br><a href="/">⬅ 回主頁</a>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash("🚪 已登出", "success")
    return redirect(url_for('index'))

@app.route('/backup_db')
def backup_db():
    if not session.get('admin'):
        flash("僅限管理員操作", "error")
        return redirect(url_for('index'))
    os.makedirs("backups", exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = f"backups/backup_{timestamp}.db"
    shutil.copyfile(DB_PATH, path)
    flash("✅ 資料庫備份成功", "success")
    return send_file(path, as_attachment=True)

@app.route('/restore_db', methods=['GET', 'POST'])
def restore_db():
    if not session.get('admin'):
        flash("僅限管理員操作", "error")
        return redirect(url_for('index'))
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith(".db"):
            file.save(DB_PATH)
            flash("✅ 已還原資料庫", "success")
            return redirect(url_for('index'))
        flash("請上傳 .db 檔案", "error")
    return '''
        <h3>還原資料庫</h3>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" accept=".db" required>
            <button type="submit">還原</button>
        </form><br><a href="/">⬅ 回主頁</a>
    '''

if __name__ == '__main__':
    initialize_system()
    app.run(debug=True)
