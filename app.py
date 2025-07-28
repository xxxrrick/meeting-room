from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key'

ADMIN_USER = 'admin'
ADMIN_PASS = '1234'

# 初始化資料庫
def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            room TEXT NOT NULL,
                            date TEXT NOT NULL,
                            start_time TEXT NOT NULL,
                            end_time TEXT NOT NULL,
                            user TEXT NOT NULL,
                            cancel_password TEXT NOT NULL
                        );''')
init_db()

@app.route('/')
def index():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect("database.db") as conn:
        all_bookings = conn.execute("SELECT * FROM bookings ORDER BY date, start_time").fetchall()

    bookings = []
    history = []
    for b in all_bookings:
        end_dt_str = f"{b[2]} {b[4]}"
        if end_dt_str >= now_str:
            bookings.append(b)
        else:
            history.append(b)
    return render_template("index.html", bookings=bookings, history=history)

@app.route('/book', methods=['POST'])
def book():
    room = request.form['room']
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    user = request.form['user']
    cancel_password = request.form['cancel_password']
    repeat_weeks = request.form.get('repeat_weeks')

    now = datetime.now()
    start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
    if start_dt < now:
        flash("無法預約過去時間。", "error")
        return redirect(url_for('index'))
    if start_time >= end_time:
        flash("起始時間必須早於結束時間。", "error")
        return redirect(url_for('index'))

    def insert_booking(d):
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            conflict = cursor.execute('''SELECT * FROM bookings WHERE room=? AND date=?
                                         AND ((start_time < ? AND end_time > ?) OR
                                              (start_time < ? AND end_time > ?) OR
                                              (start_time >= ? AND start_time < ?))''',
                                       (room, d, end_time, end_time, start_time, start_time, start_time, end_time)).fetchone()
            if conflict:
                return False
            cursor.execute("INSERT INTO bookings (room, date, start_time, end_time, user, cancel_password) VALUES (?, ?, ?, ?, ?, ?)",
                           (room, d, start_time, end_time, user, cancel_password))
            conn.commit()
            return True

    success = insert_booking(date)
    if not success:
        flash("此時段已被預約，請選擇其他時間。", "error")
        return redirect(url_for('index'))

    if repeat_weeks and repeat_weeks.isdigit():
        base_date = datetime.strptime(date, "%Y-%m-%d")
        for i in range(1, int(repeat_weeks)):
            next_date = (base_date + timedelta(weeks=i)).strftime("%Y-%m-%d")
            insert_booking(next_date)

    flash("預約成功！", "success")
    return redirect(url_for('index'))

@app.route('/cancel/<int:id>', methods=['POST'])
def cancel(id):
    password = request.form.get('cancel_password')
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT cancel_password FROM bookings WHERE id=?", (id,)).fetchone()
        if row and row[0] == password:
            cursor.execute("DELETE FROM bookings WHERE id=?", (id,))
            conn.commit()
            flash("已成功取消預約", "success")
        else:
            flash("密碼錯誤，無法取消預約", "error")
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        flash("登入失敗", "error")
    return '''<form method="POST">
        管理員帳號：<input name="username"><br>
        密碼：<input name="password" type="password"><br>
        <button type="submit">登入</button>
    </form>'''

@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    with sqlite3.connect("database.db") as conn:
        bookings = conn.execute("SELECT * FROM bookings ORDER BY date, start_time").fetchall()
    out = "<h2>管理員後台</h2><ul>"
    for b in bookings:
        out += f"<li>{b[1]} | {b[2]} {b[3]}~{b[4]} by {b[5]} <a href='/force_cancel/{b[0]}'>[強制取消]</a></li>"
    out += "</ul>"
    return out

@app.route('/force_cancel/<int:id>')
def force_cancel(id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    with sqlite3.connect("database.db") as conn:
        conn.execute("DELETE FROM bookings WHERE id=?", (id,))
        conn.commit()
    flash("管理員已取消預約", "success")
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)
