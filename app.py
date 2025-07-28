from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os, time, shutil
import sqlite3
from datetime import datetime, timedelta

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
    return redirect(url_for('index'))

@app.route('/cancel/<int:id>', methods=['GET', 'POST'])
def cancel(id):
    if session.get('admin'):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM bookings WHERE id=?", (id,))
            flash("✅ 管理員已取消預約", "success")
    elif request.method == 'POST':
        code = request.form.get('code')
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT cancel_code FROM bookings WHERE id=?", (id,)).fetchone()
            if row and row[0] == code:
                conn.execute("DELETE FROM bookings WHERE id=?", (id,))
                flash("✅ 預約已取消", "success")
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
    app.run(debug=True)
