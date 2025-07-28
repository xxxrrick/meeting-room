from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# 初始化資料庫
def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            room TEXT NOT NULL,
                            date TEXT NOT NULL,
                            start_time TEXT NOT NULL,
                            end_time TEXT NOT NULL,
                            user TEXT NOT NULL
                        );''')
init_db()

@app.route('/')
def index():
    with sqlite3.connect("database.db") as conn:
        bookings = conn.execute("SELECT * FROM bookings ORDER BY date, start_time").fetchall()
    return render_template("index.html", bookings=bookings)

@app.route('/book', methods=['POST'])
def book():
    room = request.form['room']
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    user = request.form['user']
    repeat_weeks = request.form.get('repeat_weeks')

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
            cursor.execute("INSERT INTO bookings (room, date, start_time, end_time, user) VALUES (?, ?, ?, ?, ?)",
                           (room, d, start_time, end_time, user))
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

@app.route('/cancel/<int:id>')
def cancel(id):
    with sqlite3.connect("database.db") as conn:
        conn.execute("DELETE FROM bookings WHERE id=?", (id,))
        conn.commit()
    flash("已取消預約。", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
