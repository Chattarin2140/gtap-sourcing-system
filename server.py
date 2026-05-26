"""
G-TAP Sourcing Request System v2 — Backend
Flask + PostgreSQL (production) / SQLite (local dev) + Email Notification
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse, unquote

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return jsonify({'error': str(e), 'trace': traceback.format_exc()[-500:]}), 500

# ── DATABASE BACKEND ──────────────────────────────────────────
# Supabase pooler (IPv4, transaction mode) — works from Vercel Lambda
# Username must be postgres.<project-ref> for pooler
_SUPABASE_POOL = 'postgresql://postgres.ppixmnxrnykaieenyaxh:0947659808Rin%40@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres'

POSTGRES_URL = (
    os.environ.get('POSTGRES_URL') or
    os.environ.get('DATABASE_URL') or
    (_SUPABASE_POOL if os.environ.get('VERCEL') else None)
)
USE_SQLITE = not bool(POSTGRES_URL)

if USE_SQLITE:
    import sqlite3
    SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gtap_local.db')
    PH = '?'
    print('Local dev: using SQLite →', SQLITE_PATH)
else:
    import pg8000.dbapi as pgdb
    PH = '%s'
    print('Production: using PostgreSQL (pg8000) →', POSTGRES_URL[:40], '...')

    class _DictCursor:
        """Wraps pg8000 cursor to return dicts instead of tuples."""
        def __init__(self, c):
            self._c = c
        def execute(self, sql, params=None):
            self._c.execute(sql, list(params) if params is not None else None)
        def fetchone(self):
            row = self._c.fetchone()
            if row is None: return None
            return dict(zip([d[0] for d in self._c.description], row))
        def fetchall(self):
            if not self._c.description: return []
            cols = [d[0] for d in self._c.description]
            return [dict(zip(cols, r)) for r in self._c.fetchall()]

# ── EMAIL CONFIG ──────────────────────────────────────────────
SMTP_HOST  = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT  = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER  = os.environ.get('SMTP_USER', 'rinti256@gmail.com')
SMTP_PASS  = os.environ.get('SMTP_PASS', 'umqv uhyx dtyw pdnz')
SENDER     = os.environ.get('SENDER',    'rinti256@gmail.com')
NOTIFY_CC  = os.environ.get('NOTIFY_CC', 'rinti256@gmail.com')

def get_db():
    if USE_SQLITE:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    u = urlparse(POSTGRES_URL)
    return pgdb.connect(
        host=u.hostname,
        port=u.port or 5432,
        database=u.path.lstrip('/'),
        user=unquote(u.username),
        password=unquote(u.password),
        ssl_context=True,
        timeout=10,
    )

def cur(conn):
    if USE_SQLITE:
        return conn.cursor()
    return _DictCursor(conn.cursor())

def to_dict(row):
    return dict(row) if row else None

def to_list(rows):
    return [dict(r) for r in rows]

def insert_get_id(c, sql, params):
    if USE_SQLITE:
        c.execute(sql, params)
        return c.lastrowid
    c.execute(sql + ' RETURNING id', params)
    return c.fetchone()['id']

def init_db():
    conn = get_db()
    c = conn.cursor()
    if USE_SQLITE:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                name       TEXT,
                email      TEXT,
                role       TEXT DEFAULT 'viewer',
                dept       TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS requests (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_no       TEXT UNIQUE,
                issue_date   TEXT, request_date TEXT, factory TEXT,
                user_name    TEXT, dept TEXT, section TEXT, ext TEXT, email TEXT,
                purpose      TEXT, order_type TEXT, purpose_desc TEXT, product_type TEXT,
                remark TEXT, payment TEXT, status TEXT DEFAULT 'Pending',
                created_by   TEXT, updated_by TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at   TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER REFERENCES requests(id) ON DELETE CASCADE,
                seq INTEGER, model TEXT, part_no TEXT, name TEXT,
                qty TEXT, unit TEXT, budget TEXT, gtap_code TEXT, gtap_name TEXT,
                new_old TEXT, sup_code TEXT, sup_name TEXT,
                lead_time TEXT, currency TEXT, price TEXT, moq TEXT, prod_remark TEXT
            );
            CREATE TABLE IF NOT EXISTS activity_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                msg        TEXT,
                type       TEXT DEFAULT 'ok',
                "user"     TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO users (username,password,name,email,role,dept) VALUES
              ('admin',  'admin123', 'Admin User',       'admin@tgt.co.th',  'admin',      'IT'),
              ('acct',   'acct123',  'บัญชี สมหญิง',    'acct@tgt.co.th',   'accounting', 'ACC'),
              ('buyer',  'buyer123', 'Buyer สมชาย',     'buyer@tgt.co.th',  'buyer',      'PR30'),
              ('mkt',    'mkt123',   'Marketing สมศรี', 'mkt@tgt.co.th',    'marketing',  'MKT'),
              ('viewer', 'view123',  'Viewer ทดสอบ',    'viewer@tgt.co.th', 'viewer',     'QA');
        ''')
    else:
        stmts = [
            '''CREATE TABLE IF NOT EXISTS users (
                id         SERIAL PRIMARY KEY,
                username   TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                name       TEXT,
                email      TEXT,
                role       TEXT DEFAULT 'viewer',
                dept       TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )''',
            '''CREATE TABLE IF NOT EXISTS requests (
                id           SERIAL PRIMARY KEY,
                doc_no       TEXT UNIQUE,
                issue_date   TEXT, request_date TEXT, factory TEXT,
                user_name    TEXT, dept TEXT, section TEXT, ext TEXT, email TEXT,
                purpose      TEXT, order_type TEXT, purpose_desc TEXT, product_type TEXT,
                remark TEXT, payment TEXT, status TEXT DEFAULT 'Pending',
                created_by   TEXT, updated_by TEXT,
                created_at   TIMESTAMP DEFAULT NOW(),
                updated_at   TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS products (
                id         SERIAL PRIMARY KEY,
                request_id INTEGER REFERENCES requests(id) ON DELETE CASCADE,
                seq INTEGER, model TEXT, part_no TEXT, name TEXT,
                qty TEXT, unit TEXT, budget TEXT, gtap_code TEXT, gtap_name TEXT,
                new_old TEXT, sup_code TEXT, sup_name TEXT,
                lead_time TEXT, currency TEXT, price TEXT, moq TEXT, prod_remark TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS activity_log (
                id         SERIAL PRIMARY KEY,
                msg        TEXT,
                type       TEXT DEFAULT 'ok',
                "user"     TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )''',
            '''INSERT INTO users (username,password,name,email,role,dept) VALUES
              ('admin',  'admin123', 'Admin User',       'admin@tgt.co.th',  'admin',      'IT'),
              ('acct',   'acct123',  'บัญชี สมหญิง',    'acct@tgt.co.th',   'accounting', 'ACC'),
              ('buyer',  'buyer123', 'Buyer สมชาย',     'buyer@tgt.co.th',  'buyer',      'PR30'),
              ('mkt',    'mkt123',   'Marketing สมศรี', 'mkt@tgt.co.th',    'marketing',  'MKT'),
              ('viewer', 'view123',  'Viewer ทดสอบ',    'viewer@tgt.co.th', 'viewer',     'QA')
            ON CONFLICT (username) DO NOTHING''',
        ]
        for stmt in stmts:
            c.execute(stmt)
    conn.commit()
    conn.close()
    print('DB ready')

def log(msg, type='ok', user='system'):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(f'INSERT INTO activity_log(msg,type,"user") VALUES({PH},{PH},{PH})', (msg, type, user))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'Log error: {e}')

# ── EMAIL ─────────────────────────────────────────────────────
def send_email(to_list, subject, body_html):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = SENDER
        msg['To']      = ', '.join(to_list)
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SENDER, to_list, msg.as_string())
        return True
    except Exception as e:
        print(f'Email error: {e}')
        return False

def notify_new_request(r):
    conn = get_db()
    c = cur(conn)
    c.execute(f"SELECT email FROM users WHERE role={PH} AND email IS NOT NULL AND email!={PH}", ('admin', ''))
    admins = to_list(c.fetchall())
    conn.close()
    to = list({row['email'] for row in admins} | {NOTIFY_CC} - {''})
    if not to: return
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <div style="background:#1a3a5c;color:#fff;padding:16px 20px;border-radius:8px 8px 0 0">
        <b>G-TAP: Sourcing Request ใหม่</b>
      </div>
      <div style="border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 8px 8px">
        <table style="font-size:13px;width:100%">
          <tr><td style="color:#64748b;padding:4px 0">Doc. No.:</td><td><b>{r['doc_no']}</b></td></tr>
          <tr><td style="color:#64748b">จากคุณ:</td><td>{r['user_name']} ({r['dept']})</td></tr>
          <tr><td style="color:#64748b">Factory:</td><td>{r['factory']}</td></tr>
          <tr><td style="color:#64748b">วันที่:</td><td>{r['issue_date']}</td></tr>
        </table>
      </div>
    </div>"""
    send_email(to, f'[G-TAP] New Request - {r["doc_no"]}', html)

def notify_status_change(r):
    to = list({r['email']} | {NOTIFY_CC} - {''}) if r.get('email') else [NOTIFY_CC]
    if not to: return
    color = '#10b981' if r['status'] == 'Approved' else '#ef4444'
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <div style="background:#1a3a5c;color:#fff;padding:16px 20px;border-radius:8px 8px 0 0">
        <b>G-TAP: สถานะ Request เปลี่ยนแปลง</b>
      </div>
      <div style="border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 8px 8px">
        <p style="font-size:13px">Request <b>{r['doc_no']}</b> ของคุณได้รับการอัปเดต:</p>
        <p style="font-size:20px;font-weight:700;color:{color}">{r['status']}</p>
        <p style="font-size:12px;color:#64748b">อัปเดตโดย: {r.get('updated_by','')}</p>
      </div>
    </div>"""
    send_email(to, f'[G-TAP] Request {r["doc_no"]} - {r["status"]}', html)

# ── AUTH ──────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    u, p = data.get('username', ''), data.get('password', '')
    conn = get_db()
    c = cur(conn)
    c.execute(f'SELECT * FROM users WHERE (username={PH} OR email={PH}) AND password={PH}', (u, u, p))
    row = to_dict(c.fetchone())
    conn.close()
    if not row:
        return jsonify({'error': 'Invalid credentials'}), 401
    row.pop('password', None)
    log(f'{row["name"]} เข้าสู่ระบบ', 'ok', row['name'])
    return jsonify(row)

# ── USERS ─────────────────────────────────────────────────────
@app.route('/api/users')
def list_users():
    conn = get_db()
    c = cur(conn)
    c.execute('SELECT id,username,name,email,role,dept,created_at FROM users ORDER BY id')
    rows = to_list(c.fetchall())
    conn.close()
    return jsonify(rows)

@app.route('/api/users', methods=['POST'])
def create_user():
    d = request.json or {}
    if not d.get('username') or not d.get('password') or not d.get('name'):
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            f'INSERT INTO users(username,password,name,email,role,dept) VALUES({PH},{PH},{PH},{PH},{PH},{PH})',
            (d['username'], d['password'], d['name'], d.get('email', ''), d.get('role', 'viewer'), d.get('dept', ''))
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Created'}), 201
    except Exception as e:
        if 'unique' in str(e).lower() or 'UNIQUE' in str(e):
            return jsonify({'error': 'Username already exists'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:uid>', methods=['PUT'])
def update_user(uid):
    d = request.json or {}
    if not d.get('name'):
        return jsonify({'error': 'Missing name'}), 400
    conn = get_db()
    c = conn.cursor()
    fields = f'name={PH}, email={PH}, role={PH}, dept={PH}'
    params = [d['name'], d.get('email',''), d.get('role','viewer'), d.get('dept','')]
    if d.get('password'):
        fields += f', password={PH}'
        params.append(d['password'])
    params.append(uid)
    c.execute(f'UPDATE users SET {fields} WHERE id={PH}', params)
    conn.commit()
    conn.close()
    return jsonify({'message': 'Updated'})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute(f'DELETE FROM users WHERE id={PH}', (uid,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted'})

# ── REQUESTS ──────────────────────────────────────────────────
@app.route('/api/requests')
def list_requests():
    q  = request.args.get('q', '').lower()
    st = request.args.get('status', '')
    fc = request.args.get('factory', '')
    sql    = 'SELECT * FROM requests WHERE 1=1'
    params = []
    if q:
        sql += f' AND (LOWER(doc_no) LIKE {PH} OR LOWER(user_name) LIKE {PH} OR LOWER(dept) LIKE {PH})'
        params += [f'%{q}%'] * 3
    if st:
        sql += f' AND status={PH}'; params.append(st)
    if fc:
        sql += f' AND factory={PH}'; params.append(fc)
    sql += ' ORDER BY id DESC'
    conn = get_db()
    c = cur(conn)
    c.execute(sql, params)
    rows = to_list(c.fetchall())
    result = []
    for row in rows:
        c.execute(f'SELECT * FROM products WHERE request_id={PH} ORDER BY seq', (row['id'],))
        row['products'] = to_list(c.fetchall())
        result.append(row)
    conn.close()
    return jsonify(result)

@app.route('/api/requests', methods=['POST'])
def create_request():
    d = request.json or {}
    y = datetime.now().year
    conn = get_db()
    c = cur(conn)
    c.execute(f"SELECT COUNT(*) as count FROM requests WHERE doc_no LIKE {PH}", (f'PSB-{y}-%',))
    cnt = to_dict(c.fetchone())['count']
    doc_no = f'PSB-{y}-{str(cnt + 1).zfill(3)}'
    req_id = insert_get_id(
        c,
        f'''INSERT INTO requests
            (doc_no,issue_date,request_date,factory,user_name,dept,section,ext,email,
             purpose,order_type,purpose_desc,product_type,remark,payment,status,created_by)
            VALUES({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})''',
        (doc_no, d.get('issueDate'), d.get('requestDate'), d.get('factory'),
         d.get('userName'), d.get('dept'), d.get('section'), d.get('ext'), d.get('email'),
         d.get('purpose'), d.get('orderType'), d.get('purposeDesc'), d.get('productType'),
         d.get('remark'), d.get('payment'), d.get('status', 'Pending'), d.get('createdBy', ''))
    )
    for i, p in enumerate(d.get('products', [])):
        c.execute(
            f'''INSERT INTO products
                (request_id,seq,model,part_no,name,qty,unit,budget,gtap_code,gtap_name,
                 new_old,sup_code,sup_name,lead_time,currency,price,moq,prod_remark)
                VALUES({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})''',
            (req_id, i+1, p.get('model'), p.get('partNo'), p.get('name'), p.get('qty'),
             p.get('unit'), p.get('budget'), p.get('gtapCode'), p.get('gtapName'), p.get('newOld'),
             p.get('supCode'), p.get('supName'), p.get('leadTime'), p.get('currency'),
             p.get('price'), p.get('moq'), p.get('remark'))
        )
    c.execute(f'SELECT * FROM requests WHERE id={PH}', (req_id,))
    r = to_dict(c.fetchone())
    conn.commit()
    conn.close()
    log(f'สร้าง Request {doc_no}', 'ok', d.get('createdBy', ''))
    notify_new_request(r)
    return jsonify({'id': req_id, 'docNo': doc_no, 'message': 'Created'}), 201

@app.route('/api/requests/<int:rid>/status', methods=['PATCH'])
def update_status(rid):
    d = request.json or {}
    status = d.get('status')
    VALID = {'Pending','Acct_Approved','Buyer_Approved','Rejected','Mkt_Approved','Mkt_Returned','Done'}
    if status not in VALID:
        return jsonify({'error': 'Invalid status'}), 400
    conn = get_db()
    c = cur(conn)
    now_fn = 'CURRENT_TIMESTAMP' if USE_SQLITE else 'NOW()'
    c.execute(
        f'UPDATE requests SET status={PH}, updated_by={PH}, updated_at={now_fn} WHERE id={PH}',
        (status, d.get('updatedBy', ''), rid)
    )
    c.execute(f'SELECT * FROM requests WHERE id={PH}', (rid,))
    r = to_dict(c.fetchone())
    conn.commit()
    conn.close()
    log(f'{d.get("updatedBy","")} → {status} ({r["doc_no"]})', 'ok' if status != 'Rejected' else 'err')
    notify_status_change(r)
    return jsonify({'message': 'Updated'})

@app.route('/api/requests/<int:rid>', methods=['DELETE'])
def delete_request(rid):
    conn = get_db()
    c = cur(conn)
    c.execute(f'SELECT doc_no FROM requests WHERE id={PH}', (rid,))
    r = to_dict(c.fetchone())
    c.execute(f'DELETE FROM requests WHERE id={PH}', (rid,))
    conn.commit()
    conn.close()
    log(f'ลบ Request {r["doc_no"] if r else rid}', 'err')
    return jsonify({'message': 'Deleted'})

@app.route('/api/stats')
def stats():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM requests'); t = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM requests WHERE status={PH}", ('Pending',)); p = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM requests WHERE status={PH}", ('Approved',)); a = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM products'); i = c.fetchone()[0]
    conn.close()
    return jsonify({'total': t, 'pending': p, 'approved': a, 'items': i})

@app.route('/api/logs')
def get_logs():
    conn = get_db()
    c = cur(conn)
    c.execute('SELECT * FROM activity_log ORDER BY id DESC LIMIT 50')
    rows = to_list(c.fetchall())
    conn.close()
    return jsonify(rows)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

_db_ready = False

def ensure_db():
    global _db_ready
    if not _db_ready:
        try:
            init_db()
            _db_ready = True
        except Exception as e:
            print(f'ensure_db error: {e}')

if USE_SQLITE:
    ensure_db()

if __name__ == '__main__':
    ensure_db()
    print('G-TAP v2 running at http://localhost:5000')
    app.run(debug=True, port=5000)
