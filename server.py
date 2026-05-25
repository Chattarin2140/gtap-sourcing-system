"""
G-TAP Sourcing Request System v2 — Backend
Flask + PostgreSQL + Email Notification (smtplib)
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2, psycopg2.extras, smtplib, os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)

DATABASE_URL = (
    os.environ.get('POSTGRES_URL') or
    os.environ.get('DATABASE_URL', 'postgresql://postgres:0947659808Rin%40@db.ppixmnxrnykaieenyaxh.supabase.co:5432/postgres?sslmode=require')
)

# ── EMAIL CONFIG ──────────────────────────────────────────────
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', 'rinti256@gmail.com')
SMTP_PASS = os.environ.get('SMTP_PASS', 'umqv uhyx dtyw pdnz')
SENDER    = os.environ.get('SENDER', 'rinti256@gmail.com')
NOTIFY_CC = os.environ.get('NOTIFY_CC', 'rinti256@gmail.com')  # always CC this address

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id         SERIAL PRIMARY KEY,
                    username   TEXT UNIQUE NOT NULL,
                    password   TEXT NOT NULL,
                    name       TEXT,
                    email      TEXT,
                    role       TEXT DEFAULT 'viewer',
                    dept       TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS requests (
                    id           SERIAL PRIMARY KEY,
                    doc_no       TEXT UNIQUE,
                    issue_date   TEXT, request_date TEXT, factory TEXT,
                    user_name    TEXT, dept TEXT, section TEXT, ext TEXT, email TEXT,
                    purpose      TEXT, order_type TEXT, purpose_desc TEXT, product_type TEXT,
                    remark TEXT, payment TEXT, status TEXT DEFAULT 'Pending',
                    created_by   TEXT, updated_by TEXT,
                    created_at   TIMESTAMP DEFAULT NOW(),
                    updated_at   TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS products (
                    id         SERIAL PRIMARY KEY,
                    request_id INTEGER REFERENCES requests(id) ON DELETE CASCADE,
                    seq INTEGER, model TEXT, part_no TEXT, name TEXT,
                    qty TEXT, unit TEXT, budget TEXT, gtap_code TEXT, gtap_name TEXT,
                    new_old TEXT, sup_code TEXT, sup_name TEXT,
                    lead_time TEXT, currency TEXT, price TEXT, moq TEXT, prod_remark TEXT
                );
                CREATE TABLE IF NOT EXISTS activity_log (
                    id         SERIAL PRIMARY KEY,
                    msg        TEXT,
                    type       TEXT DEFAULT 'ok',
                    "user"     TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                INSERT INTO users (username,password,name,email,role,dept) VALUES
                  ('admin',  'admin123', 'Admin User',       'admin@tgt.co.th',  'admin',      'IT'),
                  ('acct',   'acct123',  'บัญชี สมหญิง',    'acct@tgt.co.th',   'accounting', 'ACC'),
                  ('buyer',  'buyer123', 'Buyer สมชาย',     'buyer@tgt.co.th',  'buyer',      'PR30'),
                  ('mkt',    'mkt123',   'Marketing สมศรี', 'mkt@tgt.co.th',    'marketing',  'MKT'),
                  ('viewer', 'view123',  'Viewer ทดสอบ',    'viewer@tgt.co.th', 'viewer',     'QA')
                ON CONFLICT (username) DO NOTHING;
            ''')
        conn.commit()
    print('DB ready')

def log(msg, type='ok', user='system'):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO activity_log(msg,type,"user") VALUES(%s,%s,%s)', (msg, type, user))
            conn.commit()
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
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT email FROM users WHERE role='admin' AND email IS NOT NULL AND email!=''")
            admins = cur.fetchall()
    to = [row['email'] for row in admins]
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
    to = [r['email']] if r.get('email') else []
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
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM users WHERE (username=%s OR email=%s) AND password=%s', (u, u, p))
            row = cur.fetchone()
    if not row:
        return jsonify({'error': 'Invalid credentials'}), 401
    user = dict(row)
    user.pop('password', None)
    log(f'{user["name"]} เข้าสู่ระบบ', 'ok', user['name'])
    return jsonify(user)

# ── USERS ─────────────────────────────────────────────────────
@app.route('/api/users')
def list_users():
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT id,username,name,email,role,dept,created_at FROM users ORDER BY id')
            rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/users', methods=['POST'])
def create_user():
    d = request.json or {}
    if not d.get('username') or not d.get('password') or not d.get('name'):
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO users(username,password,name,email,role,dept) VALUES(%s,%s,%s,%s,%s,%s)',
                    (d['username'], d['password'], d['name'], d.get('email', ''), d.get('role', 'viewer'), d.get('dept', ''))
                )
            conn.commit()
        return jsonify({'message': 'Created'}), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({'error': 'Username already exists'}), 400

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM users WHERE id=%s', (uid,))
        conn.commit()
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
        sql += ' AND (LOWER(doc_no) ILIKE %s OR LOWER(user_name) ILIKE %s OR LOWER(dept) ILIKE %s)'
        params += [f'%{q}%'] * 3
    if st:
        sql += ' AND status=%s'; params.append(st)
    if fc:
        sql += ' AND factory=%s'; params.append(fc)
    sql += ' ORDER BY id DESC'
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            result = []
            for row in rows:
                r = dict(row)
                cur.execute('SELECT * FROM products WHERE request_id=%s ORDER BY seq', (r['id'],))
                r['products'] = [dict(p) for p in cur.fetchall()]
                result.append(r)
    return jsonify(result)

@app.route('/api/requests', methods=['POST'])
def create_request():
    d = request.json or {}
    y = datetime.now().year
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as count FROM requests WHERE doc_no LIKE %s", (f'PSB-{y}-%',))
            cnt = cur.fetchone()['count']
            doc_no = f'PSB-{y}-{str(cnt + 1).zfill(3)}'
            cur.execute('''
                INSERT INTO requests
                (doc_no,issue_date,request_date,factory,user_name,dept,section,ext,email,
                 purpose,order_type,purpose_desc,product_type,remark,payment,status,created_by)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id''',
                (doc_no, d.get('issueDate'), d.get('requestDate'), d.get('factory'),
                 d.get('userName'), d.get('dept'), d.get('section'), d.get('ext'), d.get('email'),
                 d.get('purpose'), d.get('orderType'), d.get('purposeDesc'), d.get('productType'),
                 d.get('remark'), d.get('payment'), d.get('status', 'Pending'), d.get('createdBy', ''))
            )
            req_id = cur.fetchone()['id']
            for i, p in enumerate(d.get('products', [])):
                cur.execute('''
                    INSERT INTO products
                    (request_id,seq,model,part_no,name,qty,unit,budget,gtap_code,gtap_name,
                     new_old,sup_code,sup_name,lead_time,currency,price,moq,prod_remark)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (req_id, i+1, p.get('model'), p.get('partNo'), p.get('name'), p.get('qty'),
                     p.get('unit'), p.get('budget'), p.get('gtapCode'), p.get('gtapName'), p.get('newOld'),
                     p.get('supCode'), p.get('supName'), p.get('leadTime'), p.get('currency'),
                     p.get('price'), p.get('moq'), p.get('remark'))
                )
            cur.execute('SELECT * FROM requests WHERE id=%s', (req_id,))
            r = dict(cur.fetchone())
        conn.commit()
    log(f'สร้าง Request {doc_no}', 'ok', d.get('createdBy', ''))
    notify_new_request(r)
    return jsonify({'id': req_id, 'docNo': doc_no, 'message': 'Created'}), 201

@app.route('/api/requests/<int:rid>/status', methods=['PATCH'])
VALID_STATUSES = ['Pending','Acct_Approved','Buyer_Approved','Rejected','Mkt_Approved','Mkt_Returned','Done']

def get_role_emails(role):
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT email FROM users WHERE role=%s AND email IS NOT NULL AND email!=''", (role,))
                rows = cur.fetchall()
        return [row['email'] for row in rows]
    except:
        return []

NOTIFY_CONFIG = {
    'new':           {'roles':['accounting','admin'], 'subj':'Request ใหม่รอตรวจงบ',           'msg':'มี Sourcing Request ใหม่รอการตรวจสอบงบประมาณ'},
    'Acct_Approved': {'roles':['buyer'],              'subj':'ผ่านบัญชีแล้ว รอ Buyer',          'msg':'Request ผ่านการตรวจงบแล้ว กรุณาตรวจสอบการจัดซื้อ'},
    'Buyer_Approved':{'roles':['marketing'],          'subj':'รอ Marketing อนุมัติ',            'msg':'Buyer ยืนยันแล้ว รอ Marketing อนุมัติ'},
    'Rejected':      {'roles':['requester'],          'subj':'Request ถูกปฏิเสธ',               'msg':'Request ของคุณถูกปฏิเสธโดย Buyer'},
    'Mkt_Approved':  {'roles':['buyer'],              'subj':'Marketing อนุมัติแล้ว รอสรุป PO', 'msg':'Marketing อนุมัติแล้ว กรุณาสรุป PO'},
    'Mkt_Returned':  {'roles':['buyer'],              'subj':'Marketing ส่งคืน Buyer',          'msg':'Marketing ส่งคืนให้ Buyer แก้ไข'},
    'Done':          {'roles':['admin','requester'],  'subj':'Done — PO สรุปแล้ว',             'msg':'Request เสร็จสิ้น PO ถูกสรุปโดย Buyer'},
}

@app.route('/api/notify', methods=['POST'])
def api_notify():
    d = request.json or {}
    event = d.get('event', d.get('status', ''))
    cfg = NOTIFY_CONFIG.get(event)
    if not cfg:
        return jsonify({'message': 'no config'}), 200
    to = []
    for role in cfg['roles']:
        if role == 'requester':
            if d.get('email'): to.append(d['email'])
        else:
            to.extend(get_role_emails(role))
    # Always include NOTIFY_CC so admin receives every notification
    if NOTIFY_CC:
        to.append(NOTIFY_CC)
    to = list(set(filter(None, to)))
    if not to:
        return jsonify({'message': 'no recipients'}), 200
    status_label = {'Pending':'รอบัญชีตรวจ','Acct_Approved':'รอ Buyer','Buyer_Approved':'รอ Marketing',
                    'Rejected':'Rejected','Mkt_Approved':'รอสรุป PO','Mkt_Returned':'ส่งคืน Buyer','Done':'Done ✅'}
    html = f"""<div style="font-family:sans-serif;max-width:560px;margin:auto">
      <div style="background:#1a3a5c;color:#fff;padding:16px 20px;border-radius:8px 8px 0 0"><b>G-TAP: {cfg['subj']}</b></div>
      <div style="border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 8px 8px">
        <p style="font-size:13px">{cfg['msg']}</p>
        <table style="font-size:13px;width:100%;margin-top:12px">
          <tr><td style="color:#64748b;padding:4px 0">Doc. No.:</td><td><b>{d.get('docNo','')}</b></td></tr>
          <tr><td style="color:#64748b">จากคุณ:</td><td>{d.get('userName','')} ({d.get('dept','')})</td></tr>
          <tr><td style="color:#64748b">สถานะ:</td><td><b style="color:#2563eb">{status_label.get(d.get('status',''), d.get('status',''))}</b></td></tr>
        </table>
      </div></div>"""
    ok = send_email(to, f'[G-TAP] {cfg["subj"]} - {d.get("docNo","")}', html)
    log(f'Email notify: {event} {d.get("docNo","")}', 'ok' if ok else 'warn')
    return jsonify({'message': 'sent' if ok else 'smtp_error', 'to': to}), 200

@app.route('/api/requests/<int:rid>/status', methods=['PATCH'])
def update_status(rid):
    d = request.json or {}
    status = d.get('status')
    if status not in VALID_STATUSES:
        return jsonify({'error': 'Invalid status'}), 400
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'UPDATE requests SET status=%s, updated_by=%s, updated_at=NOW() WHERE id=%s',
                (status, d.get('updatedBy', ''), rid)
            )
            cur.execute('SELECT * FROM requests WHERE id=%s', (rid,))
            r = dict(cur.fetchone())
        conn.commit()
    log(f'{d.get("updatedBy","")} → {status} ({r["doc_no"]})', 'ok' if status not in ('Rejected',) else 'err')
    return jsonify({'message': 'Updated'})

@app.route('/api/requests/<int:rid>', methods=['DELETE'])
def delete_request(rid):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT doc_no FROM requests WHERE id=%s', (rid,))
            r = cur.fetchone()
            cur.execute('DELETE FROM requests WHERE id=%s', (rid,))
        conn.commit()
    log(f'ลบ Request {r["doc_no"] if r else rid}', 'err')
    return jsonify({'message': 'Deleted'})

@app.route('/api/stats')
def stats():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM requests'); t = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM requests WHERE status='Pending'"); p = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM requests WHERE status='Approved'"); a = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM products'); i = cur.fetchone()[0]
    return jsonify({'total': t, 'pending': p, 'approved': a, 'items': i})

@app.route('/api/logs')
def get_logs():
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM activity_log ORDER BY id DESC LIMIT 50')
            rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

try:
    init_db()
except Exception as e:
    print(f'init_db error: {e}')

if __name__ == '__main__':
    print('G-TAP v2 running at http://localhost:5000')
    app.run(debug=True, port=5000)
