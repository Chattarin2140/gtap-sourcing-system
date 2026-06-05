
"""
G-TAP Sourcing Request System v2 — Backend
Flask + Supabase REST API (production) / SQLite (local dev) + Email Notification
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from functools import wraps
import os, smtplib, hmac as _hmac, hashlib, base64, json, time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt as _bcrypt

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    if app.debug:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()[-800:]}), 500
    return jsonify({'error': 'Internal server error'}), 500

# ── SECURITY ──────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'gtap-dev-secret-change-in-prod')
TOKEN_TTL  = 7 * 86400  # 7 days

def hash_pw(raw: str) -> str:
    return _bcrypt.hashpw(raw.encode(), _bcrypt.gensalt(10)).decode()

def check_pw(raw: str, stored: str) -> bool:
    if stored.startswith('$2'):
        return _bcrypt.checkpw(raw.encode(), stored.encode())
    return raw == stored  # legacy plain-text — migrated on next successful login

def _make_token(uid: int, role: str, name: str) -> str:
    payload = json.dumps({'uid': uid, 'role': role, 'name': name, 'iat': int(time.time())})
    b64     = base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')
    sig     = _hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f'{b64}.{sig}'

def _decode_token(token: str):
    try:
        b64, sig = token.rsplit('.', 1)
        expected = _hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(sig, expected):
            return None
        padded = b64 + '=' * (-len(b64) % 4)
        data   = json.loads(base64.urlsafe_b64decode(padded))
        if time.time() - data.get('iat', 0) > TOKEN_TTL:
            return None
        return data
    except Exception:
        return None

def require_auth(roles=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            raw   = request.headers.get('Authorization', '')
            token = raw[7:] if raw.startswith('Bearer ') else raw
            user  = _decode_token(token.strip())
            if not user:
                return jsonify({'error': 'Unauthorized'}), 401
            if roles and user.get('role') not in roles:
                return jsonify({'error': 'Forbidden'}), 403
            request.cu = user
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ── DATABASE BACKEND ──────────────────────────────────────────
# Secrets come from environment variables only. Set these in Vercel:
#   SUPABASE_SERVICE_KEY, SECRET_KEY, SMTP_USER, SMTP_PASS, SENDER, NOTIFY_CC
_SB_URL = os.environ.get('SUPABASE_URL', 'https://ppixmnxrnykaieenyaxh.supabase.co')
_SB_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

USE_SQLITE = not bool(os.environ.get('VERCEL'))

if USE_SQLITE:
    import sqlite3
    SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gtap_local.db')
    PH = '?'
    print('Local dev: using SQLite ->', SQLITE_PATH)
else:
    if not _SB_KEY:
        raise RuntimeError('SUPABASE_SERVICE_KEY env var is required in production')
    from supabase import create_client
    sb = create_client(_SB_URL, _SB_KEY)
    print('Production: using Supabase REST API')

# ── EMAIL CONFIG ──────────────────────────────────────────────
SMTP_HOST  = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT  = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER  = os.environ.get('SMTP_USER', '')
SMTP_PASS  = os.environ.get('SMTP_PASS', '')
SENDER     = os.environ.get('SENDER') or SMTP_USER
NOTIFY_CC  = os.environ.get('NOTIFY_CC', '')

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
        CREATE TABLE IF NOT EXISTS sequences (
            key  TEXT PRIMARY KEY,
            val  INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO users (username,password,name,email,role,dept) VALUES
          ('admin',  'admin123', 'Admin User',       'admin@tgt.co.th',  'admin',      'IT'),
          ('acct',   'acct123',  'บัญชี สมหญิง',    'acct@tgt.co.th',   'accounting', 'ACC'),
          ('buyer',  'buyer123', 'Buyer สมชาย',     'buyer@tgt.co.th',  'buyer',      'PR30'),
          ('mkt',    'mkt123',   'Marketing สมศรี', 'mkt@tgt.co.th',    'marketing',  'MKT'),
          ('viewer', 'view123',  'Viewer ทดสอบ',    'viewer@tgt.co.th', 'viewer',     'QA');
    ''')
    # Migrate plain-text passwords → bcrypt (runs on every startup, safe due to '$2' check)
    c.execute("SELECT id, password FROM users WHERE password NOT LIKE '$2%'")
    for row in c.fetchall():
        c.execute('UPDATE users SET password=? WHERE id=?', (hash_pw(row['password']), row['id']))
    # Sync sequences table from existing doc_nos to prevent duplicates on restart
    c.execute("""
        INSERT OR REPLACE INTO sequences(key, val)
        SELECT SUBSTR(doc_no, 1, 8), MAX(CAST(SUBSTR(doc_no, 10) AS INTEGER))
        FROM requests
        WHERE doc_no LIKE 'PSB-____-_%'
        GROUP BY SUBSTR(doc_no, 1, 8)
    """)
    conn.commit()
    conn.close()
    print('SQLite DB ready')

# ── EMAIL ─────────────────────────────────────────────────────
def send_email(to_list, subject, body_html):
    if not (SMTP_USER and SMTP_PASS):
        print('Email skipped: SMTP_USER/SMTP_PASS not configured')
        return False
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
        c.execute('SELECT * FROM users WHERE (username=? OR email=?)', (u, u))
        row = to_dict(c.fetchone())
        if row and check_pw(p, row['password']):
            # On-the-fly migration: re-hash if stored as plain-text
            if not row['password'].startswith('$2'):
                c.execute('UPDATE users SET password=? WHERE id=?', (hash_pw(p), row['id']))
                conn.commit()
        else:
            conn.close()
            return jsonify({'error': 'Invalid credentials'}), 401
        conn.close()
    else:
        res = sb.table('users').select('*').or_(f'username.eq.{u},email.eq.{u}').execute()
        row = next((r for r in (res.data or []) if check_pw(p, r['password'])), None)
        if not row:
            return jsonify({'error': 'Invalid credentials'}), 401
        # On-the-fly migration for Supabase
        if not row['password'].startswith('$2'):
            sb.table('users').update({'password': hash_pw(p)}).eq('id', row['id']).execute()
    row.pop('password', None)
    token = _make_token(row['id'], row['role'], row['name'])
    log(f'{row["name"]} เข้าสู่ระบบ', 'ok', row['name'])
    return jsonify({**row, 'token': token})

# ── USERS ─────────────────────────────────────────────────────
@app.route('/api/users')
@require_auth()
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
@require_auth(['admin'])
def create_user():
    d = request.json or {}
    if not d.get('username') or not d.get('password') or not d.get('name'):
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        hashed = hash_pw(d['password'])
        if USE_SQLITE:
            conn = get_db()
            c = conn.cursor()
            c.execute(
                'INSERT INTO users(username,password,name,email,role,dept) VALUES(?,?,?,?,?,?)',
                (d['username'], hashed, d['name'], d.get('email',''), d.get('role','viewer'), d.get('dept',''))
            )
            conn.commit()
            conn.close()
        else:
            sb.table('users').insert({
                'username': d['username'], 'password': hashed,
                'name': d['name'], 'email': d.get('email',''),
                'role': d.get('role','viewer'), 'dept': d.get('dept',''),
            }).execute()
        return jsonify({'message': 'Created'}), 201
    except Exception as e:
        if 'unique' in str(e).lower() or '23505' in str(e):
            return jsonify({'error': 'Username already exists'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:uid>', methods=['PUT'])
@require_auth(['admin'])
def update_user(uid):
    d = request.json or {}
    if not d.get('name'):
        return jsonify({'error': 'Missing name'}), 400
    payload = {'name': d['name'], 'email': d.get('email',''), 'role': d.get('role','viewer'), 'dept': d.get('dept','')}
    if d.get('password'):
        payload['password'] = hash_pw(d['password'])
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
@require_auth(['admin'])
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
@require_auth()
def list_requests():
    q  = request.args.get('q', '').lower()
    st = request.args.get('status', '')
    fc = request.args.get('factory', '')
    try:
        page     = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 50))))
    except (ValueError, TypeError):
        page, per_page = 1, 50
    offset = (page - 1) * per_page

    if USE_SQLITE:
        filter_sql, params = '', []
        if q:
            filter_sql += ' AND (LOWER(doc_no) LIKE ? OR LOWER(user_name) LIKE ? OR LOWER(dept) LIKE ?)'
            params += [f'%{q}%'] * 3
        if st:
            filter_sql += ' AND status=?'; params.append(st)
        if fc:
            filter_sql += ' AND factory=?'; params.append(fc)

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM requests WHERE 1=1' + filter_sql, params)
        total = c.fetchone()[0]
        c.execute('SELECT * FROM requests WHERE 1=1' + filter_sql + ' ORDER BY id DESC LIMIT ? OFFSET ?',
                  params + [per_page, offset])
        rows = to_list(c.fetchall())
        result = []
        for row in rows:
            c.execute('SELECT * FROM products WHERE request_id=? ORDER BY seq', (row['id'],))
            row['products'] = to_list(c.fetchall())
            result.append(row)
        conn.close()
    else:
        count_q = sb.table('requests').select('id', count='exact')
        query   = sb.table('requests').select('*, products(*)')
        if q:
            f = f'doc_no.ilike.%{q}%,user_name.ilike.%{q}%,dept.ilike.%{q}%'
            count_q = count_q.or_(f); query = query.or_(f)
        if st:
            count_q = count_q.eq('status', st); query = query.eq('status', st)
        if fc:
            count_q = count_q.eq('factory', fc); query = query.eq('factory', fc)
        total  = (count_q.execute()).count or 0
        result = query.order('id', desc=True).range(offset, offset + per_page - 1).execute().data or []

    return jsonify({'data': result, 'total': total, 'page': page, 'per_page': per_page})

@app.route('/api/requests', methods=['POST'])
@require_auth()
def create_request():
    d = request.json or {}
    y = datetime.now().year
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        # Atomic sequence increment — safe from race condition
        year_key = f'PSB-{y}'
        c.execute('INSERT OR IGNORE INTO sequences(key, val) VALUES(?, 0)', (year_key,))
        c.execute('UPDATE sequences SET val = val + 1 WHERE key = ?', (year_key,))
        c.execute('SELECT val FROM sequences WHERE key = ?', (year_key,))
        cnt    = c.fetchone()[0]
        doc_no = f'PSB-{y}-{str(cnt).zfill(3)}'
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
        # Supabase: use gtap_next_seq RPC for atomic increment
        year_key = f'PSB-{y}'
        try:
            seq_res = sb.rpc('gtap_next_seq', {'p_key': year_key}).execute()
            cnt = seq_res.data
        except Exception:
            # Fallback if RPC not deployed yet
            cnt_res = sb.table('requests').select('id', count='exact').like('doc_no', f'{year_key}-%').execute()
            cnt = (cnt_res.count or 0) + 1
        doc_no  = f'PSB-{y}-{str(cnt).zfill(3)}'
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
@require_auth()
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
@require_auth(['admin'])
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
@require_auth()
def stats():
    IN_PROGRESS = ('Pending','Acct_Approved','Buyer_Approved','Mkt_Approved','Mkt_Returned')
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM requests'); t = c.fetchone()[0]
        ph = ','.join('?' * len(IN_PROGRESS))
        c.execute(f'SELECT COUNT(*) FROM requests WHERE status IN ({ph})', IN_PROGRESS); ip = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM requests WHERE status='Done'"); done = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM products'); items = c.fetchone()[0]
        conn.close()
    else:
        t    = (sb.table('requests').select('id', count='exact').execute()).count or 0
        ip   = (sb.table('requests').select('id', count='exact').in_('status', list(IN_PROGRESS)).execute()).count or 0
        done = (sb.table('requests').select('id', count='exact').eq('status', 'Done').execute()).count or 0
        items = (sb.table('products').select('id', count='exact').execute()).count or 0
    return jsonify({'total': t, 'in_progress': ip, 'done': done, 'items': items})

@app.route('/api/logs')
@require_auth()
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

@app.route('/api/import-excel', methods=['POST'])
@require_auth()
def import_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['file']
    try:
        import openpyxl, io
        wb = openpyxl.load_workbook(io.BytesIO(f.read()), data_only=True)
    except Exception as e:
        return jsonify({'error': f'Cannot open file: {e}'}), 400

    def cell(rows, r, c):
        try: v = rows[r][c]; return v if v is not None else ''
        except: return ''

    def fmt_date(v):
        if hasattr(v, 'strftime'): return v.strftime('%Y-%m-%d')
        return str(v) if v else ''

    ws0 = wb.worksheets[0]
    rows0 = list(ws0.iter_rows(values_only=True))
    header = {
        'issueDate':   fmt_date(cell(rows0, 3, 2)),
        'requestDate': fmt_date(cell(rows0, 4, 2)),
        'factory':     str(cell(rows0, 5, 2)),
        'userName':    str(cell(rows0, 6, 2)),
        'dept':        str(cell(rows0, 7, 2)),
        'section':     str(cell(rows0, 8, 2)),
        'ext':         str(cell(rows0, 9, 2)),
        'email':       str(cell(rows0, 10, 2)),
        'purpose':     str(cell(rows0, 3, 14)),
        'purposeDesc': str(cell(rows0, 7, 14)),
        'docNo':       str(cell(rows0, 3, 22)),
    }

    products = []
    for ws in wb.worksheets[1:]:
        rows_p = list(ws.iter_rows(values_only=True))
        i = 0
        while i < len(rows_p):
            r1  = rows_p[i]
            seq = r1[0] if r1 else None
            if isinstance(seq, (int, float)) and not isinstance(seq, bool) and seq == int(seq) and int(seq) > 0:
                r2 = rows_p[i + 1] if i + 1 < len(rows_p) else [None] * 26
                new_old = 'P' if r1[10] else ('O' if (len(r1) > 11 and r1[11]) else 'P')
                products.append({
                    'model':    str(r1[1] or ''),
                    'partNo':   str(r1[2] or ''),
                    'name':     str(r2[2] or ''),
                    'qty':      str(r1[3] or '1'),
                    'unit':     str(r1[4] or 'Set'),
                    'budget':   str(r1[8] or ''),
                    'gtapCode': str(r1[9] or ''),
                    'gtapName': str(r2[9] or ''),
                    'newOld':   new_old,
                    'supCode':  str(r1[12] or ''),
                    'supName':  str(r2[12] or ''),
                    'leadTime': str(r1[13] or ''),
                    'currency': str(r1[14] or 'THB'),
                    'price':    str(r2[14] or ''),
                    'moq':      str(r1[18] or '1'),
                    'remark':   str(r1[25] if len(r1) > 25 and r1[25] else ''),
                })
                i += 2
            else:
                i += 1

    return jsonify({'header': header, 'products': products})

# ── EXCEL EXPORT (template-based) ────────────────────────────
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Copy of G-TAP Format-REV01.xlsx')

def _fetch_request_and_products(rid):
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM requests WHERE id=?', (rid,))
        r = to_dict(c.fetchone())
        if not r:
            conn.close()
            return None, []
        c.execute('SELECT * FROM products WHERE request_id=? ORDER BY seq', (rid,))
        prods = to_list(c.fetchall())
        conn.close()
    else:
        res = sb.table('requests').select('*').eq('id', rid).execute()
        if not res.data:
            return None, []
        r = res.data[0]
        res2 = sb.table('products').select('*').eq('request_id', rid).order('seq').execute()
        prods = res2.data or []
    return r, prods

def _build_gtap_wb(requests_products):
    """Build workbook from template for one or more (request, products) pairs."""
    import openpyxl, io
    from openpyxl.styles import Font, Alignment

    with open(TEMPLATE_PATH, 'rb') as _f:
        _tpl_bytes = _f.read()

    wb = openpyxl.load_workbook(io.BytesIO(_tpl_bytes))
    for name in list(wb.sheetnames):
        if name not in [wb.worksheets[0].title, 'detail D92A KRT']:
            del wb[name]
    tpl_psb_title = wb.worksheets[0].title

    for req, prods in requests_products:
        sheet_name = (req.get('doc_no') or f'REQ-{req["id"]}').replace('/', '-')[:28]
        det_name   = f'{sheet_name[:24]}-Det'

        ws  = wb.copy_worksheet(wb[tpl_psb_title])
        ws.title = sheet_name
        det = wb.copy_worksheet(wb['detail D92A KRT'])
        det.title = det_name
        sheet_name = (req.get('doc_no') or f'REQ-{req["id"]}').replace('/', '-')[:31]
        ws.title = sheet_name

        ws['C4']  = req.get('issue_date', '')
        ws['C5']  = req.get('request_date', '')
        ws['C6']  = req.get('factory', '')
        ws['C7']  = req.get('user_name', '')
        ws['C8']  = req.get('dept', '')
        ws['C9']  = req.get('section', '')
        ws['C10'] = req.get('ext', '')
        ws['C11'] = req.get('email', '')
        ws['H3']  = req.get('product_type', '')
        purpose   = req.get('purpose', '')
        ws['O4']  = f'  ☑ {purpose}' if purpose else ''
        ws['O8']  = req.get('purpose_desc', '')
        ws['V4']  = req.get('doc_no', '')
        ws['V6']  = req.get('order_type', '')
        ws['V6'].font      = Font(bold=False, size=18, name='Calibri')
        ws['V6'].alignment = Alignment(horizontal='center', vertical='center')
        ws['Y6']  = req.get('status', '')

        REMARK_ROW = max(21, 7 + len(prods) * 2 + 1)
        for row_num in range(7, REMARK_ROW):
            for col_num in range(1, 27):
                det.cell(row=row_num, column=col_num).value = None

        for i, p in enumerate(prods):
            r1 = 7 + i * 2
            r2 = r1 + 1
            det.cell(r1, 1).value  = i + 1
            det.cell(r1, 2).value  = p.get('model', '')
            det.cell(r1, 3).value  = p.get('part_no', '')
            det.cell(r2, 3).value  = p.get('name', '')
            det.cell(r1, 4).value  = p.get('qty', '')
            det.cell(r1, 5).value  = p.get('unit', '')
            det.cell(r1, 6).value  = '-'
            det.cell(r1, 7).value  = '-'
            det.cell(r1, 8).value  = '-'
            det.cell(r1, 9).value  = p.get('budget', '')
            det.cell(r1, 10).value = p.get('gtap_code', '')
            det.cell(r2, 10).value = p.get('gtap_name', '')
            new_old = p.get('new_old', 'P')
            det.cell(r1, 11).value = 'P' if new_old in ('P', 'New', 'new') else ''
            det.cell(r1, 12).value = 'O' if new_old in ('O', 'Old', 'old') else ''
            det.cell(r1, 13).value = p.get('sup_code', '')
            det.cell(r2, 13).value = p.get('sup_name', '')
            det.cell(r1, 14).value = p.get('lead_time', '')
            det.cell(r1, 15).value = p.get('currency', '')
            det.cell(r2, 15).value = p.get('price', '')
            det.cell(r1, 16).value = 1
            det.cell(r1, 17).value = p.get('unit', '')
            det.cell(r1, 19).value = p.get('moq', '')
            det.cell(r1, 26).value = p.get('prod_remark', '')

        det.cell(REMARK_ROW, 1).value  = req.get('remark', '')
        det.cell(REMARK_ROW, 20).value = req.get('payment', '')

    for name in [tpl_psb_title, 'detail D92A KRT']:
        if name in wb.sheetnames:
            del wb[name]

    return wb

@app.route('/api/export-excel/<int:rid>')
@require_auth()
def export_excel(rid):
    from flask import Response
    import io
    r, prods = _fetch_request_and_products(rid)
    if r is None:
        return jsonify({'error': 'Not found'}), 404
    wb = _build_gtap_wb([(r, prods)])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f'GTAP_{r.get("doc_no", rid)}.xlsx'
    return Response(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{fname}"'})

@app.route('/api/export-excel-all')
@require_auth()
def export_excel_all():
    from flask import Response
    import io
    if USE_SQLITE:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM requests ORDER BY id DESC')
        reqs = to_list(c.fetchall())
        pairs = []
        for req in reqs:
            c.execute('SELECT * FROM products WHERE request_id=? ORDER BY seq', (req['id'],))
            pairs.append((req, to_list(c.fetchall())))
        conn.close()
    else:
        res = sb.table('requests').select('*').order('id', desc=True).execute()
        reqs = res.data or []
        pairs = []
        for req in reqs:
            res2 = sb.table('products').select('*').eq('request_id', req['id']).order('seq').execute()
            pairs.append((req, res2.data or []))
    if not pairs:
        return jsonify({'error': 'No data'}), 404
    wb = _build_gtap_wb(pairs)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    from datetime import date
    fname = f'GTAP_All_{date.today()}.xlsx'
    return Response(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{fname}"'})

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
