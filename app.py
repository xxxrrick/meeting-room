from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key'

ADMIN_PASS = '0000'

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
    return render_template("index.html", bookings=bookings, history=history, admin=session.get('admin'))

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
    if session.get('admin'):
        with sqlite3.connect("database.db") as conn:
            conn.execute("DELETE FROM bookings WHERE id=?", (id,))
            conn.commit()
        flash("已由管理員取消預約", "success")
        return redirect(url_for('index'))

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
    global ADMIN_PASS
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASS:
            session['admin'] = True
            flash("登入成功", "success")
            return redirect(url_for('index'))
        flash("登入失敗", "error")
    return '''<form method="POST">
        密碼：<input name="password" type="password"><br>
        <button type="submit">登入</button>
    </form><br><a href='/'>返回首頁</a>'''

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
    out += "<br><a href='/admin/change_password'>🔒 更改管理員密碼</a>"
    out += "<br><a href='/'>返回首頁</a>"
    return out

@app.route('/admin/change_password', methods=['GET', 'POST'])
def change_admin_password():
    global ADMIN_PASS
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        current = request.form['current_password']
        new1 = request.form['new_password']
        new2 = request.form['confirm_password']

        if current != ADMIN_PASS:
            flash("目前密碼錯誤", "error")
        elif new1 != new2:
            flash("兩次輸入的新密碼不一致", "error")
        elif not new1:
            flash("新密碼不能為空", "error")
        else:
            ADMIN_PASS = new1
            flash("密碼已成功更新！", "success")
            return redirect(url_for('index'))

    return '''<form method="POST">
        目前密碼：<input type="password" name="current_password"><br>
        新密碼：<input type="password" name="new_password"><br>
        確認新密碼：<input type="password" name="confirm_password"><br>
        <button type="submit">更改密碼</button>
    </form><br><a href='/'>返回首頁</a>'''

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
