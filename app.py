<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>會議室預約系統</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; padding: 20px; }
        label { display: inline-block; width: 120px; vertical-align: top; }
        input, select { margin-bottom: 8px; }
        .message { padding: 8px; margin: 8px 0; border-radius: 4px; }
        .success { background: #d4edda; color: #155724; }
        .error-message { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>會議室預約</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="message {{ 'success' if category == 'success' else 'error-message' }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form action="/book" method="POST">
        <label>會議室：</label>
        <select name="room">
            <option value="R樓">R樓</option>
            <option value="裕林">裕林</option>
        </select><br>

        <label>日期：</label>
        <input type="date" name="date" required><br>

        <label>起始時間：</label>
        <select name="start_time" required>
          {% for h in range(0, 24) %}
            {% for m in ['00', '30'] %}
              <option value="{{ '%02d' % h }}:{{ m }}" {% if h == 8 and m == '30' %}selected{% endif %}>{{ '%02d' % h }}:{{ m }}</option>
            {% endfor %}
          {% endfor %}
        </select><br>

        <label>結束時間：</label>
        <select name="end_time" required>
          {% for h in range(0, 24) %}
            {% for m in ['00', '30'] %}
              <option value="{{ '%02d' % h }}:{{ m }}" {% if h == 12 and m == '00' %}selected{% endif %}>{{ '%02d' % h }}:{{ m }}</option>
            {% endfor %}
          {% endfor %}
        </select><br>

        <label>預約人：</label>
        <input type="text" name="user" required><br>

        <label>取消密碼：</label>
        <input type="password" name="cancel_password" required><br>

        <label>重複週數：</label>
        <input type="number" name="repeat_weeks" min="0" max="12" placeholder="可選填，如 3 表示重複 3 週"><br><br>

        <button type="submit">✅ 預約</button>
    </form>

    <h2>📋 預約列表</h2>
    <ul>
        {% for b in bookings %}
            <li>
                🏠 <strong>{{ b[1] }}</strong> ｜ 📅 {{ b[2] }} ｜ 🕒 {{ b[3] }} ~ {{ b[4] }} ｜ 👤 {{ b[5] }}
                <form action="/cancel/{{ b[0] }}" method="POST" style="display:inline;">
                  <input type="password" name="cancel_password" placeholder="取消密碼" required>
                  <button type="submit">❌ 取消</button>
                </form>
            </li>
        {% endfor %}
    </ul>

    <h2>📜 預約紀錄（已結束）</h2>
    <ul>
        {% for h in history %}
            <li>✅ {{ h[1] }} ｜ {{ h[2] }} {{ h[3] }} ~ {{ h[4] }} ｜ 👤 {{ h[5] }}</li>
        {% endfor %}
    </ul>
</body>
</html>
