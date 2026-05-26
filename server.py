"""
G-TAP Sourcing Request System v2 — Backend
Flask + Supabase REST API (production) / SQLite (local dev) + Email Notification
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return jsonify({'error': str(e), 'trace': traceback.format_exc()[-800:]}), 500

# ── DATABASE BACKEND ──────────────────────────────────────────
_SB_URL = 'https://ppixmnxrnykaieenyaxh.supabase.co'
_SB_KEY = (
    os.environ.get('SUPABASE_SERVICE_KEY') or
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6'
    'InBwaXhtbnhybnlrYWllZW55YXhoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6'
    'MTc3ODgyNTg4OCwiZXhwIjoyMDk0NDAxODg4fQ.xWjiTT87CPt4AVb366Oraeuv-13Db7K3d5BVVuE5x_Y'
)

USE_SQLITE = not bool(os.environ.get('VERCEL'))

if USE_SQLITE:
    import sqlite3
    SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gtap_local.db')
    PH = '?'
    print('Local dev: using SQLite →', SQLITE_PATH)
else:
    from supabase import create_client
    sb = create_client(_SB_URL, _SB_KEY)
    print('Production: using Supabase REST API')

# ── EMAIL CONFIG ──────────────────────────────────────────────
SMTP_HOST  = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT  = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER  = os.environ.get('SMTP_USER', 'rinti256@gmail.com')
SMTP_PASS  = os.environ.get('SMTP_PASS', 'umqv uhyx dtyw pdnz')
SENDER     = os.environ.get('SENDER',    'rinti256@gmail.com')
NOTIFY_CC  = os.environ.get('NOTIFY_CC', 'rinti256@gmail.com')

# ── SQLite helpers (local dev only) ──────────────────────────
def get_db():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def to_dict(row):
    return dict(row) if row else None

def to_list(rows):
    return [dict(r) for r in rows]

def init_db():
    conn = get_db()
    c = conn.cursor()
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
    conn.commit()
    conn.close()
    print('SQLite DB ready')

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
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT email FROM users WHERE role='admin' AND email IS NOT NULL AND email!=''")
        admins = to_list(c.fetchall())
        conn.close()
    else:
        res = sb.table('users').select('email').eq('role', 'admin').neq('email', '').execute()
        admins = res.data or []
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

def log(msg, type='ok', user='system'):
    try:
        if USE_SQLITE:
            conn = get_db()
            c = conn.cursor()
            c.execute('INSERT INTO activity_log(msg,type,"user") VALUES(?,?,?)', (msg, type, user))
            conn.commit()
            conn.close()
        else:
            sb.table('activity_log').insert({'msg': msg, 'type': type, 'user': user}).execute()
    except Exception as e:
        print(f'Log error: {e}')

# ── AUTH ──────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    u, p = data.get('username', ''), data.get('password', '')
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE (username=? OR email=?) AND password=?', (u, u, p))
        row = to_dict(c.fetchone())
        conn.close()
    else:
        res = sb.table('users').select('*').eq('username', u).eq('password', p).execute()
        if not res.data:
            res = sb.table('users').select('*').eq('email', u).eq('password', p).execute()
        row = res.data[0] if res.data else None
    if not row:
        return jsonify({'error': 'Invalid credentials'}), 401
    row.pop('password', None)
    log(f'{row["name"]} เข้าสู่ระบบ', 'ok', row['name'])
    return jsonify(row)

# ── USERS ─────────────────────────────────────────────────────
@app.route('/api/users')
def list_users():
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id,username,name,email,role,dept,created_at FROM users ORDER BY id')
        rows = to_list(c.fetchall())
        conn.close()
    else:
        res = sb.table('users').select('id,username,name,email,role,dept,created_at').order('id').execute()
        rows = res.data or []
    return jsonify(rows)

@app.route('/api/users', methods=['POST'])
def create_user():
    d = request.json or {}
    if not d.get('username') or not d.get('password') or not d.get('name'):
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        if USE_SQLITE:
            conn = get_db()
            c = conn.cursor()
            c.execute(
                'INSERT INTO users(username,password,name,email,role,dept) VALUES(?,?,?,?,?,?)',
                (d['username'], d['password'], d['name'], d.get('email',''), d.get('role','viewer'), d.get('dept',''))
            )
            conn.commit()
            conn.close()
        else:
            sb.table('users').insert({
                'username': d['username'], 'password': d['password'],
                'name': d['name'], 'email': d.get('email',''),
                'role': d.get('role','viewer'), 'dept': d.get('dept',''),
            }).execute()
        return jsonify({'message': 'Created'}), 201
    except Exception as e:
        if 'unique' in str(e).lower() or '23505' in str(e):
            return jsonify({'error': 'Username already exists'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:uid>', methods=['PUT'])
def update_user(uid):
    d = request.json or {}
    if not d.get('name'):
        return jsonify({'error': 'Missing name'}), 400
    payload = {'name': d['name'], 'email': d.get('email',''), 'role': d.get('role','viewer'), 'dept': d.get('dept','')}
    if d.get('password'):
        payload['password'] = d['password']
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        fields = ', '.join(f'{k}=?' for k in payload)
        c.execute(f'UPDATE users SET {fields} WHERE id=?', list(payload.values()) + [uid])
        conn.commit()
        conn.close()
    else:
        sb.table('users').update(payload).eq('id', uid).execute()
    return jsonify({'message': 'Updated'})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE id=?', (uid,))
        conn.commit()
        conn.close()
    else:
        sb.table('users').delete().eq('id', uid).execute()
    return jsonify({'message': 'Deleted'})

# ── REQUESTS ──────────────────────────────────────────────────
@app.route('/api/requests')
def list_requests():
    q  = request.args.get('q', '').lower()
    st = request.args.get('status', '')
    fc = request.args.get('factory', '')
    if USE_SQLITE:
        sql = 'SELECT * FROM requests WHERE 1=1'
        params = []
        if q:
            sql += ' AND (LOWER(doc_no) LIKE ? OR LOWER(user_name) LIKE ? OR LOWER(dept) LIKE ?)'
            params += [f'%{q}%'] * 3
        if st:
            sql += ' AND status=?'; params.append(st)
        if fc:
            sql += ' AND factory=?'; params.append(fc)
        sql += ' ORDER BY id DESC'
        conn = get_db()
        c = conn.cursor()
        c.execute(sql, params)
        rows = to_list(c.fetchall())
        result = []
        for row in rows:
            c.execute('SELECT * FROM products WHERE request_id=? ORDER BY seq', (row['id'],))
            row['products'] = to_list(c.fetchall())
            result.append(row)
        conn.close()
    else:
        query = sb.table('requests').select('*, products(*)')
        if q:
            query = query.or_(f'doc_no.ilike.%{q}%,user_name.ilike.%{q}%,dept.ilike.%{q}%')
        if st:
            query = query.eq('status', st)
        if fc:
            query = query.eq('factory', fc)
        res = query.order('id', desc=True).execute()
        result = res.data or []
    return jsonify(result)

@app.route('/api/requests', methods=['POST'])
def create_request():
    d = request.json or {}
    y = datetime.now().year
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM requests WHERE doc_no LIKE ?", (f'PSB-{y}-%',))
        cnt = c.fetchone()[0]
        doc_no = f'PSB-{y}-{str(cnt + 1).zfill(3)}'
        c.execute(
            '''INSERT INTO requests
               (doc_no,issue_date,request_date,factory,user_name,dept,section,ext,email,
                purpose,order_type,purpose_desc,product_type,remark,payment,status,created_by)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (doc_no, d.get('issueDate'), d.get('requestDate'), d.get('factory'),
             d.get('userName'), d.get('dept'), d.get('section'), d.get('ext'), d.get('email'),
             d.get('purpose'), d.get('orderType'), d.get('purposeDesc'), d.get('productType'),
             d.get('remark'), d.get('payment'), d.get('status','Pending'), d.get('createdBy',''))
        )
        req_id = c.lastrowid
        for i, p in enumerate(d.get('products', [])):
            c.execute(
                '''INSERT INTO products
                   (request_id,seq,model,part_no,name,qty,unit,budget,gtap_code,gtap_name,
                    new_old,sup_code,sup_name,lead_time,currency,price,moq,prod_remark)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (req_id, i+1, p.get('model'), p.get('partNo'), p.get('name'), p.get('qty'),
                 p.get('unit'), p.get('budget'), p.get('gtapCode'), p.get('gtapName'), p.get('newOld'),
                 p.get('supCode'), p.get('supName'), p.get('leadTime'), p.get('currency'),
                 p.get('price'), p.get('moq'), p.get('remark'))
            )
        c.execute('SELECT * FROM requests WHERE id=?', (req_id,))
        r = to_dict(c.fetchone())
        conn.commit()
        conn.close()
    else:
        cnt_res = sb.table('requests').select('id', count='exact').like('doc_no', f'PSB-{y}-%').execute()
        cnt = cnt_res.count or 0
        doc_no = f'PSB-{y}-{str(cnt + 1).zfill(3)}'
        req_res = sb.table('requests').insert({
            'doc_no': doc_no,
            'issue_date': d.get('issueDate'), 'request_date': d.get('requestDate'),
            'factory': d.get('factory'), 'user_name': d.get('userName'),
            'dept': d.get('dept'), 'section': d.get('section'),
            'ext': d.get('ext'), 'email': d.get('email'),
            'purpose': d.get('purpose'), 'order_type': d.get('orderType'),
            'purpose_desc': d.get('purposeDesc'), 'product_type': d.get('productType'),
            'remark': d.get('remark'), 'payment': d.get('payment'),
            'status': d.get('status', 'Pending'), 'created_by': d.get('createdBy', ''),
        }).execute()
        req_id = req_res.data[0]['id']
        r = req_res.data[0]
        if d.get('products'):
            sb.table('products').insert([{
                'request_id': req_id, 'seq': i+1,
                'model': p.get('model'), 'part_no': p.get('partNo'), 'name': p.get('name'),
                'qty': p.get('qty'), 'unit': p.get('unit'), 'budget': p.get('budget'),
                'gtap_code': p.get('gtapCode'), 'gtap_name': p.get('gtapName'),
                'new_old': p.get('newOld'), 'sup_code': p.get('supCode'),
                'sup_name': p.get('supName'), 'lead_time': p.get('leadTime'),
                'currency': p.get('currency'), 'price': p.get('price'),
                'moq': p.get('moq'), 'prod_remark': p.get('remark'),
            } for i, p in enumerate(d.get('products', []))]).execute()
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
    updater = d.get('updatedBy', '')
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            'UPDATE requests SET status=?, updated_by=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (status, updater, rid)
        )
        c.execute('SELECT * FROM requests WHERE id=?', (rid,))
        r = to_dict(c.fetchone())
        conn.commit()
        conn.close()
    else:
        sb.table('requests').update({
            'status': status, 'updated_by': updater,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', rid).execute()
        res = sb.table('requests').select('*').eq('id', rid).execute()
        r = res.data[0] if res.data else {'doc_no': rid}
    log(f'{updater} → {status} ({r.get("doc_no",rid)})', 'ok' if status != 'Rejected' else 'err')
    notify_status_change(r)
    return jsonify({'message': 'Updated'})

@app.route('/api/requests/<int:rid>', methods=['DELETE'])
def delete_request(rid):
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT doc_no FROM requests WHERE id=?', (rid,))
        row = to_dict(c.fetchone())
        c.execute('DELETE FROM requests WHERE id=?', (rid,))
        conn.commit()
        conn.close()
        doc_no = row['doc_no'] if row else rid
    else:
        res = sb.table('requests').select('doc_no').eq('id', rid).execute()
        doc_no = res.data[0]['doc_no'] if res.data else rid
        sb.table('requests').delete().eq('id', rid).execute()
    log(f'ลบ Request {doc_no}', 'err')
    return jsonify({'message': 'Deleted'})

@app.route('/api/stats')
def stats():
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM requests'); t = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM requests WHERE status='Pending'"); p = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM requests WHERE status='Approved'"); a = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM products'); i = c.fetchone()[0]
        conn.close()
    else:
        t = (sb.table('requests').select('id', count='exact').execute()).count or 0
        p = (sb.table('requests').select('id', count='exact').eq('status', 'Pending').execute()).count or 0
        a = (sb.table('requests').select('id', count='exact').eq('status', 'Approved').execute()).count or 0
        i = (sb.table('products').select('id', count='exact').execute()).count or 0
    return jsonify({'total': t, 'pending': p, 'approved': a, 'items': i})

@app.route('/api/logs')
def get_logs():
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM activity_log ORDER BY id DESC LIMIT 50')
        rows = to_list(c.fetchall())
        conn.close()
    else:
        res = sb.table('activity_log').select('*').order('id', desc=True).limit(50).execute()
        rows = res.data or []
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
