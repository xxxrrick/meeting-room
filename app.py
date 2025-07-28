from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            room TEXT NOT NULL,
                            date TEXT NOT NULL,
                            time TEXT NOT NULL,
                            user TEXT NOT NULL
                        );''')
init_db()

@app.route('/')
def index():
    with sqlite3.connect("database.db") as conn:
        bookings = conn.execute("SELECT * FROM bookings ORDER BY date, time").fetchall()
    return render_template("index.html", bookings=bookings)

@app.route('/book', methods=['POST'])
def book():
    room = request.form['room']
    date = request.form['date']
    time = request.form['time']
    user = request.form['user']

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE room=? AND date=? AND time=?", (room, date, time))
        if cursor.fetchone():
            return "這個時段已被預約，請選擇其他時間。"
        cursor.execute("INSERT INTO bookings (room, date, time, user) VALUES (?, ?, ?, ?)",
                       (room, date, time, user))
        conn.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
