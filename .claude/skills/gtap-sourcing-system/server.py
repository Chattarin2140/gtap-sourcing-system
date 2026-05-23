"""
G-TAP Sourcing Request System v2 — Backend
Flask + SQLite + Email Notification (smtplib)
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, json, smtplib, hashlib, os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, static_folder='.')
CORS(app)
DB_FILE = 'gtap.db'

# ── EMAIL CONFIG (แก้ค่าตามจริง) ─────────────────────────────
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', 'your-email@gmail.com')
SMTP_PASS = os.environ.get('SMTP_PASS', 'your-app-password')
SENDER    = os.environ.get('SENDER',    'gtap-noreply@tgt.co.th')

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name     TEXT,
                email    TEXT,
                role     TEXT DEFAULT 'viewer',
                dept     TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS requests (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_no       TEXT UNIQUE,
                issue_date   TEXT, request_date TEXT, factory TEXT,
                user_name    TEXT, dept TEXT, section TEXT, ext TEXT, email TEXT,
                purpose      TEXT, order_type TEXT, purpose_desc TEXT, product_type TEXT,
                remark TEXT, payment TEXT, status TEXT DEFAULT 'Pending',
                created_by   TEXT, updated_by TEXT,
                created_at   TEXT DEFAULT (datetime('now','localtime')),
                updated_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER REFERENCES requests(id) ON DELETE CASCADE,
                seq INTEGER, model TEXT, part_no TEXT, name TEXT,
                qty TEXT, unit TEXT, budget TEXT, gtap_code TEXT, gtap_name TEXT,
                new_old TEXT, sup_code TEXT, sup_name TEXT,
                lead_time TEXT, currency TEXT, price TEXT, moq TEXT, prod_remark TEXT
            );
            CREATE TABLE IF NOT EXISTS activity_log (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                msg     TEXT,
                type    TEXT DEFAULT 'ok',
                user    TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            INSERT OR IGNORE INTO users (username,password,name,email,role,dept)
            VALUES
              ('admin','admin123','Admin User','admin@tgt.co.th','admin','IT'),
              ('buyer','buyer123','Buyer สมชาย','buyer@tgt.co.th','buyer','PR30'),
              ('viewer','view123','Viewer ทดสอบ','viewer@tgt.co.th','viewer','QA');
        ''')
    print('✅ DB ready:', DB_FILE)

def log(msg, type='ok', user='system'):
    with get_db() as conn:
        conn.execute('INSERT INTO activity_log(msg,type,user) VALUES(?,?,?)', (msg,type,user))

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
        print(f'✉ Email sent to {to_list}')
        return True
    except Exception as e:
        print(f'✉ Email error: {e}')
        return False

def notify_new_request(r):
    with get_db() as conn:
        admins = conn.execute("SELECT email FROM users WHERE role='admin' AND email IS NOT NULL AND email!=''").fetchall()
    to = [row['email'] for row in admins]
    if not to: return
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <div style="background:#1a3a5c;color:#fff;padding:16px 20px;border-radius:8px 8px 0 0">
        <b>🔔 G-TAP: Sourcing Request ใหม่</b>
      </div>
      <div style="border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 8px 8px">
        <table style="font-size:13px;width:100%">
          <tr><td style="color:#64748b;padding:4px 0">Doc. No.:</td><td><b>{r['doc_no']}</b></td></tr>
          <tr><td style="color:#64748b">จากคุณ:</td><td>{r['user_name']} ({r['dept']})</td></tr>
          <tr><td style="color:#64748b">Factory:</td><td>{r['factory']}</td></tr>
          <tr><td style="color:#64748b">วันที่:</td><td>{r['issue_date']}</td></tr>
        </table>
        <p style="margin-top:16px"><a href="http://your-gtap-url.com" style="background:#2563eb;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none">เปิด G-TAP System</a></p>
      </div>
    </div>"""
    send_email(to, f'[G-TAP] New Request - {r["doc_no"]}', html)

def notify_status_change(r):
    to = [r['email']] if r.get('email') else []
    if not to: return
    color = '#10b981' if r['status']=='Approved' else '#ef4444'
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <div style="background:#1a3a5c;color:#fff;padding:16px 20px;border-radius:8px 8px 0 0">
        <b>📋 G-TAP: สถานะ Request เปลี่ยนแปลง</b>
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
    u, p = data.get('username',''), data.get('password','')
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE (username=? OR email=?) AND password=?', (u,u,p)).fetchone()
    if not row: return jsonify({'error':'Invalid credentials'}), 401
    user = dict(row)
    user.pop('password', None)
    log(f'{user["name"]} เข้าสู่ระบบ', 'ok', user['name'])
    return jsonify(user)

# ── USERS ─────────────────────────────────────────────────────
@app.route('/api/users')
def list_users():
    with get_db() as conn:
        rows = conn.execute('SELECT id,username,name,email,role,dept,created_at FROM users').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/users', methods=['POST'])
def create_user():
    d = request.json or {}
    if not d.get('username') or not d.get('password') or not d.get('name'):
        return jsonify({'error':'Missing required fields'}), 400
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO users(username,password,name,email,role,dept) VALUES(?,?,?,?,?,?)',
                (d['username'],d['password'],d['name'],d.get('email',''),d.get('role','viewer'),d.get('dept','')))
        return jsonify({'message':'Created'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error':'Username already exists'}), 400

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    with get_db() as conn:
        conn.execute('DELETE FROM users WHERE id=?', (uid,))
    return jsonify({'message':'Deleted'})

# ── REQUESTS ──────────────────────────────────────────────────
@app.route('/api/requests')
def list_requests():
    q,st,fc = request.args.get('q','').lower(), request.args.get('status',''), request.args.get('factory','')
    sql = 'SELECT * FROM requests WHERE 1=1'
    params = []
    if q: sql+=' AND (LOWER(doc_no) LIKE ? OR LOWER(user_name) LIKE ? OR LOWER(dept) LIKE ?)'; params+=[f'%{q}%']*3
    if st: sql+=' AND status=?'; params.append(st)
    if fc: sql+=' AND factory=?'; params.append(fc)
    sql+=' ORDER BY id DESC'
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            r = dict(row)
            prods = conn.execute('SELECT * FROM products WHERE request_id=? ORDER BY seq',(r['id'],)).fetchall()
            r['products'] = [dict(p) for p in prods]
            result.append(r)
    return jsonify(result)

@app.route('/api/requests', methods=['POST'])
def create_request():
    d = request.json or {}
    y = datetime.now().year
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM requests WHERE doc_no LIKE ?",(f'PSB-{y}-%',)).fetchone()[0]
        doc_no = f'PSB-{y}-{str(cnt+1).zfill(3)}'
        cur = conn.execute('''INSERT INTO requests
            (doc_no,issue_date,request_date,factory,user_name,dept,section,ext,email,
             purpose,order_type,purpose_desc,product_type,remark,payment,status,created_by)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (doc_no,d.get('issueDate'),d.get('requestDate'),d.get('factory'),
             d.get('userName'),d.get('dept'),d.get('section'),d.get('ext'),d.get('email'),
             d.get('purpose'),d.get('orderType'),d.get('purposeDesc'),d.get('productType'),
             d.get('remark'),d.get('payment'),d.get('status','Pending'),d.get('createdBy','')))
        req_id = cur.lastrowid
        for i,p in enumerate(d.get('products',[])):
            conn.execute('''INSERT INTO products
                (request_id,seq,model,part_no,name,qty,unit,budget,gtap_code,gtap_name,
                 new_old,sup_code,sup_name,lead_time,currency,price,moq,prod_remark)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (req_id,i+1,p.get('model'),p.get('partNo'),p.get('name'),p.get('qty'),
                 p.get('unit'),p.get('budget'),p.get('gtapCode'),p.get('gtapName'),p.get('newOld'),
                 p.get('supCode'),p.get('supName'),p.get('leadTime'),p.get('currency'),
                 p.get('price'),p.get('moq'),p.get('remark')))
        r = dict(conn.execute('SELECT * FROM requests WHERE id=?',(req_id,)).fetchone())
    log(f'สร้าง Request {doc_no}','ok', d.get('createdBy',''))
    notify_new_request(r)
    return jsonify({'id':req_id,'docNo':doc_no,'message':'Created'}), 201

@app.route('/api/requests/<int:rid>/status', methods=['PATCH'])
def update_status(rid):
    d = request.json or {}
    status = d.get('status')
    if status not in ('Pending','Approved','Rejected'):
        return jsonify({'error':'Invalid status'}), 400
    with get_db() as conn:
        conn.execute("UPDATE requests SET status=?,updated_by=?,updated_at=datetime('now','localtime') WHERE id=?",
                     (status, d.get('updatedBy',''), rid))
        r = dict(conn.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone())
    log(f'{d.get("updatedBy","")} {status} Request {r["doc_no"]}','ok' if status=='Approved' else 'err')
    notify_status_change(r)
    return jsonify({'message':'Updated'})

@app.route('/api/requests/<int:rid>', methods=['DELETE'])
def delete_request(rid):
    with get_db() as conn:
        r = conn.execute('SELECT doc_no FROM requests WHERE id=?',(rid,)).fetchone()
        conn.execute('DELETE FROM requests WHERE id=?',(rid,))
    log(f'ลบ Request {r["doc_no"] if r else rid}','err')
    return jsonify({'message':'Deleted'})

@app.route('/api/stats')
def stats():
    with get_db() as conn:
        t = conn.execute('SELECT COUNT(*) FROM requests').fetchone()[0]
        p = conn.execute("SELECT COUNT(*) FROM requests WHERE status='Pending'").fetchone()[0]
        a = conn.execute("SELECT COUNT(*) FROM requests WHERE status='Approved'").fetchone()[0]
        i = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    return jsonify({'total':t,'pending':p,'approved':a,'items':i})

@app.route('/api/logs')
def get_logs():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM activity_log ORDER BY id DESC LIMIT 50').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/')
def index():
    return send_from_directory('.','index.html')

if __name__=='__main__':
    init_db()
    print('🚀 G-TAP v2 running at http://localhost:5000')
    app.run(debug=True, port=5000)
