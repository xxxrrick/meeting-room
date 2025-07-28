from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os, time, shutil
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'
ADMIN_PASSWORD = '0000'

# 資料庫位置
DB_PATH = 'data/database.db'
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 初始化資料庫
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                user TEXT NOT NULL
            );
        ''')

init_db()

@app.route('/')
def index():
    with sqlite3.connect(DB_PATH) as conn:
        bookings = conn.execute("SELECT * FROM bookings ORDER BY date, start_time").fetchall()
    return render_template("index.html", bookings=bookings, admin=session.get('admin'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            flash("✅ 管理員登入成功", "success")
            return redirect(url_for('index'))
        else:
            flash("❌ 密碼錯誤", "error")
    return '''
        <h2>管理員登入</h2>
        <form method="POST">
            密碼：<input type="password" name="password">
            <button type="submit">登入</button>
        </form>
        <br><a href="/">⬅ 返回主頁</a>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash("🚪 已登出管理員", "success")
    return redirect(url_for('index'))

@app.route('/backup_db')
def backup_db():
    if not session.get('admin'):
        flash("❌ 僅限管理員操作", "error")
        return redirect(url_for('index'))

    os.makedirs("backups", exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = f"backups/backup_{timestamp}.db"

    try:
        shutil.copyfile(DB_PATH, backup_path)
        flash("✅ 資料庫備份成功", "success")
        return send_file(backup_path, as_attachment=True)
    except Exception as e:
        flash(f"❌ 備份失敗: {e}", "error")
        return redirect(url_for('index'))

@app.route('/restore_db', methods=['GET', 'POST'])
def restore_db():
    if not session.get('admin'):
        flash("❌ 僅限管理員操作", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith(".db"):
            file.save(DB_PATH)
            flash("✅ 備份已還原並覆蓋目前資料庫", "success")
            return redirect(url_for('index'))
        else:
            flash("請上傳副檔名為 .db 的 SQLite 檔案", "error")
            return redirect(url_for('restore_db'))

    return '''
        <h2>還原資料庫</h2>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" accept=".db" required>
            <button type="submit">還原</button>
        </form>
        <br><a href="/">⬅ 返回主頁</a>
    '''

if __name__ == '__main__':
    app.run(debug=True)
