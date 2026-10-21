import os
import sqlite3
import socket
from datetime import datetime
from functools import wraps
from flask import (
    Flask, request, redirect, url_for,
    session, render_template_string, send_from_directory, flash
)

# =====================================
# إعدادات النظام
# =====================================

app = Flask(__name__)
app.secret_key = "electricity-system-change-this-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "electricity.db")
LOGO_FILE = os.path.join(BASE_DIR, "logo.png")
PASSWORD = "2001"


# =====================================
# قاعدة البيانات - لا تحذف ملف electricity.db
# =====================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                address TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                debt REAL NOT NULL DEFAULT 0,
                paid REAL NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                notes TEXT DEFAULT '',
                paid_at TEXT NOT NULL,
                FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
            )
        """)


init_db()


# =====================================
# تصميم البرنامج
# =====================================

STYLE = """
* { box-sizing: border-box; }

body {
    margin: 0;
    font-family: Tahoma, Arial, sans-serif;
    background: #f1f5f4;
    color: #24312d;
    line-height: 1.7;
}

header {
    background: linear-gradient(135deg, #064e3b, #07845d);
    color: white;
    text-align: center;
    padding: 22px 12px;
}

.logo {
    width: 88px;
    height: 88px;
    object-fit: contain;
    border-radius: 50%;
    background: white;
    padding: 5px;
}

header h1 { font-size: 25px; margin: 8px 0; }
header h2 { font-size: 19px; margin: 5px 0; }
header h3 { font-size: 16px; font-weight: normal; margin: 4px 0; }
header p { margin: 10px 0 0; }

.container {
    max-width: 1150px;
    width: 100%;
    padding: 15px;
    margin: auto;
}

.card {
    background: white;
    border-radius: 13px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 3px 12px #0000000c;
}

.section-title { color: #07543d; margin-top: 0; }

input, textarea, button, select { font: inherit; }

input, textarea, select {
    display: block;
    width: 100%;
    padding: 12px;
    margin: 5px 0 14px;
    border: 1px solid #cbd5d1;
    border-radius: 8px;
    background: white;
    min-height: 46px;
}

textarea { min-height: 80px; resize: vertical; }
label { font-weight: bold; }

button, .btn {
    display: inline-block;
    border: none;
    border-radius: 8px;
    padding: 11px 15px;
    min-height: 44px;
    cursor: pointer;
    text-decoration: none;
    text-align: center;
    color: white;
    background: #087f5b;
}

button:active, .btn:active { opacity: 0.75; }
.blue { background: #1769aa; }
.gray { background: #566273; }
.red { background: #bd3328; }

.nav {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 15px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}

.stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
}

.stat {
    background: white;
    border-radius: 10px;
    padding: 14px;
    text-align: center;
    border-top: 4px solid #07845d;
    overflow-wrap: anywhere;
}

.stat strong {
    display: block;
    font-size: 21px;
    color: #07543d;
}

.table-wrap {
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 760px;
}

th, td {
    padding: 10px;
    text-align: right;
    border: 1px solid #e0e7e3;
}

th { color: white; background: #07543d; }
tr:nth-child(even) { background: #f7faf8; }

.notice {
    background: #dcfce7;
    color: #166534;
    padding: 12px;
    margin-bottom: 12px;
    border-radius: 8px;
}

.error { background: #fee2e2; color: #991b1b; }
.login { max-width: 450px; margin: 30px auto; }

.actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

footer {
    text-align: center;
    color: #65716b;
    padding: 20px;
}

@media (max-width: 650px) {
    header { padding: 17px 9px; }
    header h1 { font-size: 21px; }
    header h2 { font-size: 17px; }
    header h3 { font-size: 14px; }
    header p { font-size: 14px; }
    .logo { width: 72px; height: 72px; }
    .container { padding: 10px; }
    .card { padding: 14px; border-radius: 10px; }
    .grid, .stats { grid-template-columns: 1fr; }

    .stat {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        text-align: right;
    }

    .stat strong { font-size: 18px; }

    .nav {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .nav .btn { width: 100%; }
    .actions .btn { flex: 1 1 auto; }
    button, .btn { font-size: 14px; }
}

@media print {
    .no-print { display: none !important; }
    body { background: white; }
    .container { max-width: none; }
    .card { box-shadow: none; }

    @page {
        size: A4;
        margin: 12mm;
    }
}
"""


# =====================================
# التحقق من الدخول
# =====================================

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("index"))
        return func(*args, **kwargs)
    return wrapper


# =====================================
# الصفحة الرئيسية
# =====================================

PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#064e3b">
<title>نظام أرشفة مشتركي الكهرباء</title>
<style>""" + STYLE + """</style>
</head>
<body>

<header>
    {% if logo_exists %}
        <img class="logo" src="{{ url_for('logo') }}" alt="شعار الوزارة">
    {% else %}
        <div style="font-size:48px">⚡</div>
    {% endif %}

    <h1>وزارة الكهرباء</h1>
    <h3>الشركة العامة لتوزيع كهرباء الوسط</h3>
    <h3>فرع توزيع كهرباء مركز الأنبار</h3>
    <h3>قطاع توزيع كهرباء غرب الرمادي</h3>
    <h2>مركز صيانة التأميم</h2>
    <p>نظام أرشفة وتدقيق المشتركين والديون المستحقة</p>
</header>

<main class="container">

{% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
        <div class="notice {% if category == 'error' %}error{% endif %}">
            {{ message }}
        </div>
    {% endfor %}
{% endwith %}

{% if not logged_in %}

    <section class="card login">
        <h2 class="section-title">تسجيل الدخول</h2>
        <form method="post" action="{{ url_for('login') }}">
            <label>رمز الدخول</label>
            <input type="password" name="password"
                   placeholder="أدخل رمز الدخول 2001"
                   autocomplete="current-password" required>
            <button style="width:100%" type="submit">دخول إلى النظام</button>
        </form>
    </section>

{% else %}

    <nav class="nav no-print">
        <a class="btn" href="{{ url_for('index') }}">الرئيسية</a>
        <a class="btn blue" href="{{ url_for('payments_page') }}">التسديدات</a>
        <a class="btn gray" href="{{ url_for('index') }}#add">إضافة مشترك</a>
        <a class="btn red" href="{{ url_for('logout') }}">خروج</a>
    </nav>

    <section class="stats">
        <div class="stat">
            <span>عدد المشتركين</span>
            <strong>{{ total_subscribers }}</strong>
        </div>
        <div class="stat">
            <span>مجموع الديون</span>
            <strong>{{ "{:,.0f}".format(total_debt) }}</strong>
        </div>
        <div class="stat">
            <span>المتبقي الكلي</span>
            <strong>{{ "{:,.0f}".format(total_remaining) }}</strong>
        </div>
    </section>

    <section class="card no-print" id="add">
        <h2 class="section-title">إضافة مشترك جديد</h2>
        <form method="post" action="{{ url_for('add_subscriber') }}">
            <div class="grid">
                <div>
                    <label>رقم الحساب *</label>
                    <input name="account_no" required>
                </div>
                <div>
                    <label>اسم المشترك *</label>
                    <input name="name" required>
                </div>
                <div>
                    <label>العنوان</label>
                    <input name="address">
                </div>
                <div>
                    <label>رقم الهاتف</label>
                    <input name="phone" inputmode="tel">
                </div>
                <div>
                    <label>الدين الكلي بالدينار</label>
                    <input type="number" name="debt"
                           min="0" step="0.01" value="0" required>
                </div>
            </div>
            <label>ملاحظات</label>
            <textarea name="notes"></textarea>
            <button type="submit" style="width:100%">حفظ المشترك</button>
        </form>
    </section>

    <section class="card no-print">
        <h2 class="section-title">البحث عن مشترك</h2>
        <form method="get" action="{{ url_for('index') }}">
            <input name="q" value="{{ query }}"
                   placeholder="رقم الحساب أو الاسم أو العنوان أو الهاتف">
            <button type="submit">بحث</button>
            <a class="btn gray" href="{{ url_for('index') }}">عرض الكل</a>
        </form>
    </section>

    <section class="card">
        <h2 class="section-title">سجل المشتركين</h2>
        <p>على الموبايل، اسحب الجدول يميناً ويساراً لعرض بقية الأعمدة.</p>
        <div class="table-wrap">
            <table>
                <thead>
                <tr>
                    <th>ت</th>
                    <th>رقم الحساب</th>
                    <th>الاسم</th>
                    <th>العنوان</th>
                    <th>الهاتف</th>
                    <th>الدين</th>
                    <th>المسدّد</th>
                    <th>المتبقي</th>
                    <th class="no-print">الإجراءات</th>
                </tr>
                </thead>
                <tbody>
                {% for s in subscribers %}
                <tr>
                    <td>{{ s.id }}</td>
                    <td>{{ s.account_no }}</td>
                    <td>{{ s.name }}</td>
                    <td>{{ s.address or '' }}</td>
                    <td>{{ s.phone or '' }}</td>
                    <td>{{ "{:,.0f}".format(s.debt) }}</td>
                    <td>{{ "{:,.0f}".format(s.paid) }}</td>
                    <td>{{ "{:,.0f}".format(s.debt - s.paid) }}</td>
                    <td class="no-print">
                        <div class="actions">
                            <a class="btn blue"
                               href="{{ url_for('subscriber_details', subscriber_id=s.id) }}">
                               التفاصيل والتسديد
                            </a>
                            <a class="btn gray"
                               href="{{ url_for('print_subscriber', subscriber_id=s.id) }}">
                               كشف
                            </a>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="9">لا توجد سجلات مطابقة.</td></tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </section>

{% endif %}
</main>

<footer>وزارة الكهرباء — مركز صيانة التأميم</footer>
</body>
</html>
"""


@app.route("/")
def index():
    if not session.get("logged_in"):
        return render_template_string(
            PAGE,
            logged_in=False,
            logo_exists=os.path.isfile(LOGO_FILE)
        )

    query = request.args.get("q", "").strip()

    with get_db() as db:
        if query:
            subscribers = db.execute("""
                SELECT * FROM subscribers
                WHERE account_no LIKE ?
                   OR name LIKE ?
                   OR address LIKE ?
                   OR phone LIKE ?
                ORDER BY id DESC
            """, (f"%{query}%",) * 4).fetchall()
        else:
            subscribers = db.execute("""
                SELECT * FROM subscribers ORDER BY id DESC
            """).fetchall()

        stats = db.execute("""
            SELECT COUNT(*) AS count,
                   COALESCE(SUM(debt),0) AS debt,
                   COALESCE(SUM(debt-paid),0) AS remaining
            FROM subscribers
        """).fetchone()

    return render_template_string(
        PAGE,
        logged_in=True,
        logo_exists=os.path.isfile(LOGO_FILE),
        subscribers=subscribers,
        total_subscribers=stats["count"],
        total_debt=stats["debt"],
        total_remaining=stats["remaining"],
        query=query
    )


# =====================================
# الدخول والخروج
# =====================================

@app.route("/login", methods=["POST"])
def login():
    if request.form.get("password", "") == PASSWORD:
        session["logged_in"] = True
        session.permanent = False
        flash("تم تسجيل الدخول.")
    else:
        flash("رمز الدخول غير صحيح.", "error")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# =====================================
# إضافة مشترك
# =====================================

@app.route("/add", methods=["POST"])
@login_required
def add_subscriber():
    account_no = request.form.get("account_no", "").strip()
    name = request.form.get("name", "").strip()
    address = request.form.get("address", "").strip()
    phone = request.form.get("phone", "").strip()
    notes = request.form.get("notes", "").strip()

    try:
        debt = float(request.form.get("debt", "0"))
        if debt < 0:
            raise ValueError
    except ValueError:
        flash("مبلغ الدين غير صحيح.", "error")
        return redirect(url_for("index"))

    if not account_no or not name:
        flash("رقم الحساب والاسم مطلوبان.", "error")
        return redirect(url_for("index"))

    try:
        with get_db() as db:
            db.execute("""
                INSERT INTO subscribers
                (account_no,name,address,phone,debt,paid,notes,created_at)
                VALUES (?,?,?,?,?,0,?,?)
            """, (
                account_no, name, address, phone, debt, notes,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
        flash("تم حفظ المشترك بنجاح.")
    except sqlite3.IntegrityError:
        flash("رقم الحساب مسجل مسبقاً.", "error")

    return redirect(url_for("index"))


# =====================================
# تفاصيل المشترك والتسديد
# =====================================

@app.route("/subscriber/<int:subscriber_id>", methods=["GET", "POST"])
@login_required
def subscriber_details(subscriber_id):
    with get_db() as db:
        s = db.execute(
            "SELECT * FROM subscribers WHERE id=?",
            (subscriber_id,)
        ).fetchone()

        if s is None:
            flash("المشترك غير موجود.", "error")
            return redirect(url_for("index"))

        if request.method == "POST":
            try:
                amount = float(request.form.get("amount", "0"))
                if amount <= 0:
                    raise ValueError
            except ValueError:
                flash("أدخل مبلغاً صحيحاً أكبر من صفر.", "error")
                return redirect(url_for(
                    "subscriber_details", subscriber_id=subscriber_id
                ))

            remaining = s["debt"] - s["paid"]
            if amount > remaining:
                flash("المبلغ أكبر من الدين المتبقي.", "error")
                return redirect(url_for(
                    "subscriber_details", subscriber_id=subscriber_id
                ))

            notes = request.form.get("payment_notes", "").strip()

            db.execute("""
                INSERT INTO payments (subscriber_id,amount,notes,paid_at)
                VALUES (?,?,?,?)
            """, (
                subscriber_id, amount, notes,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

            db.execute("""
                UPDATE subscribers SET paid=paid+? WHERE id=?
            """, (amount, subscriber_id))

            flash("تم تسجيل التسديد.")
            return redirect(url_for(
                "subscriber_details", subscriber_id=subscriber_id
            ))

        payments = db.execute("""
            SELECT * FROM payments
            WHERE subscriber_id=? ORDER BY id DESC
        """, (subscriber_id,)).fetchall()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>تفاصيل المشترك</title>
    <style>""" + STYLE + """</style>
    </head>
    <body>
    <header>
        <h1>وزارة الكهرباء</h1>
        <h3>الشركة العامة لتوزيع كهرباء الوسط</h3>
        <h3>فرع توزيع كهرباء مركز الأنبار</h3>
        <h3>قطاع توزيع كهرباء غرب الرمادي</h3>
        <h2>مركز صيانة التأميم</h2>
        <p>تفاصيل المشترك والتسديدات</p>
    </header>

    <main class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="notice {% if category == 'error' %}error{% endif %}">
                    {{ message }}
                </div>
            {% endfor %}
        {% endwith %}

        <section class="card">
            <h2 class="section-title">بيانات المشترك</h2>
            <p><b>رقم الحساب:</b> {{ s.account_no }}</p>
            <p><b>الاسم:</b> {{ s.name }}</p>
            <p><b>العنوان:</b> {{ s.address or '' }}</p>
            <p><b>الهاتف:</b> {{ s.phone or '' }}</p>
            <p><b>الدين الكلي:</b> {{ "{:,.0f}".format(s.debt) }} دينار</p>
            <p><b>المسدّد:</b> {{ "{:,.0f}".format(s.paid) }} دينار</p>
            <p><b>المتبقي:</b> {{ "{:,.0f}".format(s.debt-s.paid) }} دينار</p>
            <p><b>ملاحظات:</b> {{ s.notes or '' }}</p>
            <a class="btn gray" href="{{ url_for('index') }}">رجوع</a>
            <a class="btn blue" href="{{ url_for('print_subscriber', subscriber_id=s.id) }}">طباعة</a>
        </section>

        <section class="card">
            <h2 class="section-title">تسجيل تسديد</h2>
            <form method="post">
                <label>مبلغ التسديد بالدينار</label>
                <input type="number" name="amount" min="0.01"
                       step="0.01" required>
                <label>ملاحظات</label>
                <textarea name="payment_notes"></textarea>
                <button type="submit" style="width:100%">حفظ التسديد</button>
            </form>
        </section>

        <section class="card">
            <h2 class="section-title">سجل التسديدات</h2>
            <div class="table-wrap">
                <table>
                    <tr><th>التاريخ</th><th>المبلغ</th><th>الملاحظات</th></tr>
                    {% for p in payments %}
                    <tr>
                        <td>{{ p.paid_at }}</td>
                        <td>{{ "{:,.0f}".format(p.amount) }}</td>
                        <td>{{ p.notes or '' }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="3">لا توجد تسديدات.</td></tr>
                    {% endfor %}
                </table>
            </div>
        </section>
    </main>
    </body>
    </html>
    """, s=s, payments=payments)


# =====================================
# جميع التسديدات
# =====================================

@app.route("/payments")
@login_required
def payments_page():
    with get_db() as db:
        payments = db.execute("""
            SELECT payments.*, subscribers.name, subscribers.account_no
            FROM payments
            JOIN subscribers ON subscribers.id=payments.subscriber_id
            ORDER BY payments.id DESC
        """).fetchall()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>سجل التسديدات</title>
    <style>""" + STYLE + """</style>
    </head>
    <body>
    <header><h1>سجل تسديدات المشتركين</h1></header>
    <main class="container">
        <section class="card">
            <a class="btn" href="{{ url_for('index') }}">الرئيسية</a>
            <div class="table-wrap" style="margin-top:15px">
                <table>
                    <tr>
                        <th>رقم الحساب</th><th>الاسم</th>
                        <th>المبلغ</th><th>التاريخ</th><th>الملاحظات</th>
                    </tr>
                    {% for p in payments %}
                    <tr>
                        <td>{{ p.account_no }}</td>
                        <td>{{ p.name }}</td>
                        <td>{{ "{:,.0f}".format(p.amount) }}</td>
                        <td>{{ p.paid_at }}</td>
                        <td>{{ p.notes or '' }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="5">لا توجد تسديدات.</td></tr>
                    {% endfor %}
                </table>
            </div>
        </section>
    </main>
    </body>
    </html>
    """, payments=payments)


# =====================================
# طباعة كشف المشترك A4 - مضاف إلى البرنامج
# =====================================

@app.route("/print/<int:subscriber_id>")
@login_required
def print_subscriber(subscriber_id):
    with get_db() as db:
        s = db.execute(
            "SELECT * FROM subscribers WHERE id=?",
            (subscriber_id,)
        ).fetchone()

        if s is None:
            flash("المشترك غير موجود.", "error")
            return redirect(url_for("index"))

        payments = db.execute("""
            SELECT * FROM payments
            WHERE subscriber_id=?
            ORDER BY id DESC
        """, (subscriber_id,)).fetchall()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>كشف حساب مشترك A4</title>

        <style>
            * { box-sizing: border-box; }

            body {
                font-family: Tahoma, Arial, sans-serif;
                color: #172b25;
                background: #eef2f0;
                margin: 0;
                padding: 18px;
                line-height: 1.6;
            }

            .toolbar {
                max-width: 210mm;
                margin: 0 auto 12px;
                display: flex;
                gap: 8px;
            }

            button, .back-button {
                font-family: inherit;
                font-size: 14px;
                padding: 10px 18px;
                border: 0;
                border-radius: 6px;
                background: #087f5b;
                color: white;
                cursor: pointer;
                text-decoration: none;
            }

            .back-button { background: #566273; }

            .sheet {
                width: 100%;
                max-width: 210mm;
                margin: auto;
                padding: 8mm;
                background: white;
                border: 1px solid #d1d5db;
            }

            .heading {
                text-align: center;
                border: 2px solid #07543d;
                padding: 8px;
                margin-bottom: 10px;
            }

            .logo {
                width: 68px;
                height: 68px;
                object-fit: contain;
                margin-bottom: 3px;
            }

            .heading h2, .heading h3, .heading p {
                margin: 2px 0;
            }

            .heading h2 { font-size: 17px; }
            .heading h3 { font-size: 13px; }

            .report-title {
                margin-top: 7px !important;
                padding-top: 6px;
                border-top: 1px solid #a7b8af;
                font-size: 17px;
                font-weight: bold;
                color: #07543d;
            }

            .section-title {
                background: #e8f2ed;
                border-right: 5px solid #087f5b;
                padding: 5px 8px;
                margin: 10px 0 6px;
                font-size: 14px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
            }

            th, td {
                border: 1px solid #65756d;
                padding: 6px;
                text-align: right;
                overflow-wrap: anywhere;
                font-size: 11px;
            }

            th {
                background: #edf3ef;
                font-weight: bold;
            }

            .info-table th { width: 22%; }

            .payments-table th,
            .payments-table td {
                padding: 4px;
                font-size: 10px;
            }

            .time-row {
                display: flex;
                justify-content: space-between;
                gap: 8px;
                flex-wrap: wrap;
                margin-top: 9px;
                padding: 6px;
                border: 1px solid #9aa9a1;
                font-size: 11px;
            }

            .signature {
                margin-top: 22px;
                text-align: center;
                page-break-inside: avoid;
            }

            .position { font-weight: bold; font-size: 14px; }
            .engineer { font-size: 11px; margin-top: 4px; }
            .name { font-size: 11px; }
            .sign-line { font-size: 11px; margin-top: 12px; }

            @page {
                size: A4 portrait;
                margin: 10mm;
            }

            @media print {
                body {
                    background: white;
                    padding: 0;
                    margin: 0;
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }

                .toolbar { display: none !important; }

                .sheet {
                    max-width: none;
                    width: 100%;
                    margin: 0;
                    padding: 0;
                    border: none;
                }

                tr { page-break-inside: avoid; }

                .heading, .section-title, th, .time-row {
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }
            }
        </style>
    </head>

    <body>
        <div class="toolbar">
            <button onclick="window.print()">طباعة كشف A4</button>
            <a class="back-button" href="{{ url_for('subscriber_details', subscriber_id=s.id) }}">رجوع</a>
        </div>

        <main class="sheet">
            <header class="heading">
                {% if logo_exists %}
                    <img class="logo" src="{{ url_for('logo') }}"
                         alt="شعار وزارة الكهرباء">
                {% else %}
                    <div style="font-size:36px">⚡</div>
                {% endif %}

                <h2>وزارة الكهرباء</h2>
                <h3>الشركة العامة لتوزيع كهرباء الوسط</h3>
                <h3>فرع توزيع كهرباء مركز الأنبار</h3>
                <h3>قطاع توزيع كهرباء غرب الرمادي</h3>
                <h3>مركز صيانة التأميم</h3>

                <p class="report-title">
                    استمارة معلومات المشترك والديون المستحقة
                </p>
            </header>

            <h3 class="section-title">أولاً: معلومات المشترك</h3>

            <table class="info-table">
                <tr>
                    <th>رقم الحساب</th>
                    <td>{{ s.account_no }}</td>
                    <th>اسم المشترك</th>
                    <td>{{ s.name }}</td>
                </tr>
                <tr>
                    <th>العنوان</th>
                    <td colspan="3">{{ s.address or '—' }}</td>
                </tr>
                <tr>
                    <th>رقم الهاتف</th>
                    <td>{{ s.phone or '—' }}</td>
                    <th>تاريخ التسجيل</th>
                    <td>{{ s.created_at or '—' }}</td>
                </tr>
            </table>

            <h3 class="section-title">ثانياً: الحسابات المالية</h3>

            <table class="info-table">
                <tr>
                    <th>الدين الكلي</th>
                    <td>{{ "{:,.0f}".format(s.debt) }} دينار</td>
                    <th>المبلغ المسدّد</th>
                    <td>{{ "{:,.0f}".format(s.paid) }} دينار</td>
                </tr>
                <tr>
                    <th>المبلغ المتبقي</th>
                    <td colspan="3">
                        <strong>{{ "{:,.0f}".format(s.debt-s.paid) }} دينار</strong>
                    </td>
                </tr>
                <tr>
                    <th>ملاحظات المشترك</th>
                    <td colspan="3">{{ s.notes or 'لا توجد ملاحظات' }}</td>
                </tr>
            </table>

            <h3 class="section-title">ثالثاً: سجل التسديدات</h3>

            <table class="payments-table">
                <thead>
                    <tr>
                        <th style="width:9%">ت</th>
                        <th style="width:28%">التاريخ والوقت</th>
                        <th style="width:25%">المبلغ بالدينار</th>
                        <th>الملاحظات</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in payments %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ p.paid_at }}</td>
                        <td>{{ "{:,.0f}".format(p.amount) }}</td>
                        <td>{{ p.notes or '—' }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="4">لا توجد تسديدات مسجلة.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <div class="time-row">
                <span>تاريخ الطباعة: <strong id="print-date"></strong></span>
                <span>وقت الطباعة: <strong id="print-time"></strong></span>
            </div>

            <div class="signature">
                <div class="position">مسؤول مركز صيانة التأميم</div>
                <div class="engineer">المهندس</div>
                <div class="name">مصطفى خميس محمود</div>
                <div class="sign-line">التوقيع: ................................</div>
            </div>
        </main>

        <script>
            function updatePrintTime() {
                const d = new Date();

                document.getElementById("print-date").textContent =
                    d.toLocaleDateString("en-GB");

                document.getElementById("print-time").textContent =
                    d.toLocaleTimeString("en-GB", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                        hour12: true
                    });
            }

            updatePrintTime();
            window.addEventListener("beforeprint", updatePrintTime);
        </script>
    </body>
    </html>
    """,
        s=s,
        payments=payments,
        logo_exists=os.path.isfile(LOGO_FILE)
    )


# =====================================
# صورة الشعار
# =====================================

@app.route("/logo")
def logo():
    if not os.path.isfile(LOGO_FILE):
        return "ملف الشعار غير موجود", 404
    return send_from_directory(BASE_DIR, "logo.png")


# =====================================
# عنوان اللابتوب على الشبكة
# =====================================

def get_local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "عنوان غير معروف"
    finally:
        sock.close()


# =====================================
# تشغيل النظام
# =====================================

if __name__ == "__main__":
    local_ip = get_local_ip()

    print("\n" + "=" * 50)
    print("نظام أرشفة وتدقيق المشتركين والديون")
    print("رمز الدخول: 2001")
    print("على اللابتوب: http://127.0.0.1:5000")
    print(f"على الموبايل: http://{local_ip}:5000")
    print("يجب أن يكون الجهازان على نفس شبكة Wi-Fi")
    print("=" * 50 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)