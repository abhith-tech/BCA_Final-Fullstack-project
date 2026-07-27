# ============================================================
#  EmpowerAccess — Flask Backend  (app.py)
#  Author  : EmpowerAccess Team
#  Purpose : Handles all API requests from:
#              - user_dashboard.html  (web browser)
#              - admin_dashboard.html (web browser)
#              - EmpowerAccess.exe    (desktop app)
#  Database: MySQL  (empoweraccess)
#  Auth    : JWT tokens (24-hour expiry)
# ============================================================

# Imports Flask framework, query parameters, json serializers, and file serving helpers
from flask import Flask, request, jsonify, send_from_directory
# Imports Cross-Origin Resource Sharing modules allowing GUI clients to load remote records
from flask_cors import CORS          # allows browser/exe to call this API from different origin
# Imports MySQL connector drivers to perform raw cursor queries on localized tables
import mysql.connector               # connects to MySQL database
# Imports bcrypt security helper to perform salted password hashing algorithms
import bcrypt                        # hashes and verifies passwords securely
# Imports JSON Web Token engine to sign and verify client auth headers
import jwt                           # creates and verifies login tokens
# Imports datetime packages to compute auth sessions expiration limits
import datetime                      # used for token expiry and timestamps
# Imports standard SMTP transport protocols to dispatch notifications and OTP logs
import smtplib                       # sends emails via Gmail SMTP
# Imports cryptographically secure secrets generators to produce 6-digit OTP passcodes
import secrets                       # generates secure random OTP numbers
import os                            # file/folder operations
import psutil                        # reads CPU, RAM, disk, battery stats
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# Imports wrap utilities to preserve routing metadata under protected wrappers
from functools import wraps          # preserves function names when using decorators

# ── Create the Flask app and allow all cross-origin requests ──
# static_folder='.' means Flask can serve HTML files from the same folder
# Constructs global Flask server instance pointing static assets folders
app = Flask(__name__, static_folder='.')
# Enforces cross-origin permissions allowing desktop widgets to make requests
CORS(app)   # without this, browser will block API calls due to CORS policy


# ============================================================
# CONFIG  —  edit these values before running
# ============================================================

# MySQL connection settings — change password to your MySQL root password
# Binds MySQL credentials host, port, database names, and passwords
DB_CONFIG = {
    'host':     '',
    'user':     '',
    'password': '',   # ← your MySQL password
    'database': ''
}

# Secret key used to sign JWT tokens — set this in the environment before running
JWT_SECRET = os.getenv('JWT_SECRET', '')
JWT_EXPIRY_HOURS = 24   # token is valid for 24 hours after login

# Gmail SMTP settings — use environment variables to keep credentials out of source control
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))  # Gmail TLS port
EMAIL_USER = os.getenv('EMAIL_USER', '')         # sender Gmail address
EMAIL_PASS = os.getenv('EMAIL_PASS', '')         # Gmail App Password
EMAIL_FROM = os.getenv('EMAIL_FROM', '')

# Gemini AI API key — used for /api/user/ai endpoint (ask/translate/explain)
# Get free key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Twilio SMS API settings — used to send real text messages on SOS trigger
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_FROM = os.getenv('TWILIO_PHONE_FROM', '')


def normalize_sms_number(number):
    """
    Converts stored local/international phone values into a Twilio-friendly E.164 number.
    Defaults 10-digit local numbers to India (+91), matching the existing SOS flow.
    """
    cleaned = ''.join(ch for ch in str(number or '').strip() if ch.isdigit() or ch == '+')
    if not cleaned:
        return ''
    if cleaned.startswith('+'):
        return cleaned
    if len(cleaned) == 10:
        return f"+91{cleaned}"
    return f"+{cleaned}"


def send_twilio_sms(to_number, body):
    """
    Sends a real SMS through Twilio.
    Raises RuntimeError when Twilio is not configured or the upstream call fails.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_FROM:
        raise RuntimeError('Twilio SMS is not configured')

    import urllib.request, urllib.parse, base64

    sms_to = normalize_sms_number(to_number)
    sms_from = normalize_sms_number(TWILIO_PHONE_FROM)
    if not sms_to:
        raise RuntimeError('Recipient phone number is missing')

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    payload = urllib.parse.urlencode({'To': sms_to, 'From': sms_from, 'Body': body}).encode('utf-8')
    auth_str = f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}"
    b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

    req = urllib.request.Request(url, data=payload, headers={'Authorization': f"Basic {b64_auth}"}, method='POST')
    urllib.request.urlopen(req, timeout=10)
    return sms_to


# ============================================================
# DATABASE HELPER
# ============================================================

# Orchestrates fresh database connections pools using connection parameters
def get_db():
    """
    Opens and returns a fresh MySQL database connection.
    Called at the start of every API route that needs the database.
    Always close the connection after use to avoid connection leaks.
    """
    # Returns processed data outputs back to calling functions
    return mysql.connector.connect(**DB_CONFIG)


# ============================================================
# JWT HELPERS
# ============================================================

# Produces signed JWT payloads binding user IDs and authorization categories
def generate_token(user_id, role):
    """
    Creates a signed JWT token containing the user's ID and role.
    This token is sent to the client after login and must be
    included in all future requests as:  Authorization: Bearer <token>

    Args:
        user_id : int  — the user's primary key from User or Admin table
        role    : str  — 'user' or 'admin'
    Returns:
        str — the encoded JWT token
    """
    payload = {
        'user_id': user_id,
        'role':    role,
        # exp = expiry time — JWT will reject tokens older than this
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS) 
    }
    # Returns processed data outputs back to calling functions
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


# Protected API decorator intercepting token signatures to secure client actions
def token_required(f):
    """
    Decorator that protects any route — only logged-in users can access it.
    Reads the Authorization header, decodes the JWT, and stores
    the decoded data in  request.user  so route functions can use it.

    Usage:
        # Registers HTTP route path rules binding specific controller logic below
        @app.route('/some/route')
        @token_required
        # API controller routing routine executing client transactions
        def my_route():
            user_id = request.user['user_id']
    """
    @wraps(f)
    # API controller routing routine executing client transactions
    def decorated(*args, **kwargs):
        # Extract token from header — format is "Bearer <token>"
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Token missing'}), 401

        # Safety try guard tracking runtime execution exceptions
        try:
            # Decode the token using our secret key
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            request.user = data   # attach decoded data to the request object
        except jwt.ExpiredSignatureError:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Token expired, please login again'}), 401
        except jwt.InvalidTokenError:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Invalid token'}), 401

        # Returns processed data outputs back to calling functions
        return f(*args, **kwargs)
    # Returns processed data outputs back to calling functions
    return decorated


# Admin API decorator enforcing validation that users hold administrative permissions
def admin_required(f):
    """
    Decorator that protects admin-only routes.
    Works exactly like token_required but also checks that role == 'admin'.
    Regular users will get a 403 Forbidden response.
    """
    @wraps(f)
    # API controller routing routine executing client transactions
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Token missing'}), 401

        # Safety try guard tracking runtime execution exceptions
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

            # Block access if role is not admin
            if data.get('role') != 'admin':
                # Translates python dictionary records back to standard JSON returns format
                return jsonify({'success': False, 'message': 'Admin access required'}), 403

            request.user = data
        except jwt.ExpiredSignatureError:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Invalid token'}), 401

        # Returns processed data outputs back to calling functions
        return f(*args, **kwargs)
    # Returns processed data outputs back to calling functions
    return decorated


# ============================================================
# SERVE STATIC HTML FILES
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/')
# API controller routing routine executing client transactions
def index():
    """Serves the main index.html when someone visits http://localhost:5000"""
    # Returns processed data outputs back to calling functions
    return send_from_directory('.', 'index.html')

# Registers HTTP route path rules binding specific controller logic below
@app.route('/<path:filename>')
# API controller routing routine executing client transactions
def static_files(filename):
    """
    Serves any static file (HTML, CSS, JS, .exe) from the project folder.
    Example: http://localhost:5000/user_dashboard.html
    """
    # Returns processed data outputs back to calling functions
    return send_from_directory('.', filename)


# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/contact', methods=['POST'])
# API controller routing routine executing client transactions
def contact_form():
    """
    Handles contact form submissions from index.html.
    """
    data    = request.get_json()
    name    = data.get('name', '').strip()
    email   = data.get('email', '').strip()
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()

    if not name or not email or not subject or not message:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        send_contact_email(name, email, subject, message)
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'Your message has been sent successfully!'})
    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Failed to send message: {str(e)}'}), 500


# ============================================================
# AUTH — REGISTER
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/register', methods=['POST'])
# API controller routing routine executing client transactions
def register():
    """
    Registers a new user account.

    Expected JSON body:
        { name, email, password, confirmPassword, phone }

    Steps:
        1. Validate all required fields
        2. Check email is not already used in User or Admin table
        3. Hash the password with bcrypt (never store plain text)
        4. Insert into User table with status='active'
        5. Generate JWT and return it so user is auto-logged in
    """
    data = request.get_json()

    # Extract fields with defaults to avoid KeyError
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    phone    = data.get('phone', '').strip()
    confirm  = data.get('confirmPassword', '')

    # ── Validation ──
    if not name or not email or not password:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Name, email and password are required'}), 400

    if password != confirm:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Passwords do not match'}), 400

    if len(password) < 6:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)   # dictionary=True → rows returned as dicts not tuples

        # Check if email already exists in User table
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT user_id FROM User WHERE email = %s", (email,))
        if cursor.fetchone():
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Email already registered'}), 409

        # Also check Admin table — admin emails should not be reused for user accounts
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT admin_id FROM Admin WHERE email = %s", (email,))
        if cursor.fetchone():
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Email already registered'}), 409

        # Hash password — bcrypt adds a random salt automatically each time
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert the new user — phone and emergency_contact are optional
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "INSERT INTO User (name, email, password, phone, emergency_contact, status) VALUES (%s, %s, %s, %s, %s, 'active')",
            (name, email, hashed, phone or None, data.get('emergency_contact', '').strip() or None)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        user_id = cursor.lastrowid   # get the auto-incremented ID of the new user

        # Generate token so user is logged in immediately after registration
        token = generate_token(user_id, 'user')

        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success':  True,
            'message':  'Registration successful!',
            'token':    token,
            'role':     'user',
            'name':     name,
            'redirect': 'user_dashboard.html'
        }), 201

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500


# ============================================================
# AUTH — LOGIN
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/login', methods=['POST'])
# API controller routing routine executing client transactions
def login():
    """
    Logs in a user or admin.

    Steps:
        1. Check Admin table first — admins are checked separately
        2. If not admin, check User table
        3. Verify password with bcrypt
        4. For users: insert a Login_Log row (tracks session, IP, device)
        5. Return JWT token + role so frontend knows where to redirect
    """
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)

        # ── Check if email belongs to an Admin ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT admin_id AS id, name, email, password FROM Admin WHERE email = %s",
            (email,)
        )
        admin = cursor.fetchone()

        if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password'].encode('utf-8')):
            # Admin login successful
            token = generate_token(admin['id'], 'admin')
            # Note: we do NOT insert Login_Log for admin because the FK references User table only
            # Saves SQL updates and data insertion records securely to system storage
            db.commit()
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({
                'success':  True,
                'message':  'Welcome Admin!',
                'token':    token,
                'role':     'admin',
                'name':     admin['name'],
                'redirect': 'admin_dashboard.html'
            })

        # ── Check User table ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT user_id AS id, name, email, password, status FROM User WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        if not user:
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

        # Check if admin disabled this account
        if user['status'] == 'disabled':
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Your account has been disabled. Contact admin.'}), 403

        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

        # ── Generate token for user ──
        token = generate_token(user['id'], 'user')

        # ── Detect device type from User-Agent header ──
        # User-Agent is sent automatically by browsers and the .exe's requests library
        ua = request.headers.get('User-Agent', '').lower()
        if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
            device = 'Mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            device = 'Tablet'
        else:
            device = 'Desktop'   # default — .exe app will show as Desktop

        # ── Record this login session in Login_Log ──
        # logout_time is NULL until the user calls /api/logout
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "INSERT INTO Login_Log (user_id, login_time, ip_address, device_type) VALUES (%s, NOW(), %s, %s)",
            (user['id'], request.remote_addr, device)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success':  True,
            'message':  f"Welcome back, {user['name']}!",
            'token':    token,
            'role':     'user',
            'name':     user['name'],
            'redirect': 'user_dashboard.html'
        })

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500


# ============================================================
# AUTH — FORGOT PASSWORD  (Step 1: Send OTP)
# ============================================================

# Temporary in-memory OTP store: { email: { otp, expiry, name } }
# This resets every time the server restarts — good enough for OTPs
reset_otps = {}

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/forgot-password', methods=['POST'])
# API controller routing routine executing client transactions
def forgot_password():
    """
    Sends a 6-digit OTP to the user's email for password reset.

    Security note: We always return success even if email doesn't exist.
    This prevents attackers from discovering which emails are registered.
    """
    data  = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Email is required'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)

        # 1. Check Admin table first
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT admin_id, name FROM Admin WHERE email = %s", (email,))
        user_record = cursor.fetchone()
        role = 'admin'

        # 2. If not admin, check User table
        if not user_record:
            # Executes custom SQL script parameter patterns securely
            cursor.execute("SELECT user_id, name FROM User WHERE email = %s", (email,))
            user_record = cursor.fetchone()
            role = 'user'

        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # If email not found in either table, still return success (security best practice)
        if not user_record:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': True, 'message': 'If this email exists, a reset OTP has been sent.'})

        # Generate a random 6-digit OTP (100000 to 999999)
        otp    = str(secrets.randbelow(900000) + 100000)
        expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

        # Store OTP temporarily in memory with role information
        reset_otps[email] = {
            'otp': otp, 
            'expiry': expiry, 
            'name': user_record['name'],
            'role': role
        }

        # Send the OTP via email
        send_reset_email(email, user_record['name'], otp)

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'OTP sent to your email! Valid for 10 minutes.'})

    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ============================================================
# AUTH — RESET PASSWORD  (Step 2: Verify OTP + Set New Password)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/reset-password', methods=['POST'])
# API controller routing routine executing client transactions
def reset_password():
    """
    Verifies the OTP and updates the user's password.

    Expected JSON body:
        { email, otp, newPassword }
    """
    data         = request.get_json()
    email        = data.get('email', '').strip().lower()
    otp          = data.get('otp', '').strip()
    new_password = data.get('newPassword', '')

    if not email or not otp or not new_password:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    # Check if an OTP was actually requested for this email
    record = reset_otps.get(email)
    if not record:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'No OTP requested for this email'}), 400

    # Check if OTP has expired (10-minute window)
    if datetime.datetime.utcnow() > record['expiry']:
        del reset_otps[email]   # clean up expired OTP
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'OTP has expired. Please request a new one.'}), 400

    # Verify OTP matches
    if record['otp'] != otp:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400

    if len(new_password) < 6:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        # Hash the new password before saving
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        role = record.get('role', 'user') # default to user if role missing

        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        
        if role == 'admin':
            # Executes custom SQL script parameter patterns securely
            cursor.execute("UPDATE Admin SET password = %s WHERE email = %s", (hashed, email))
        else:
            # Executes custom SQL script parameter patterns securely
            cursor.execute("UPDATE User SET password = %s WHERE email = %s", (hashed, email))
            
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Remove OTP from memory — it has been used
        del reset_otps[email]

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'Password reset successfully! You can now login.'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500


# ============================================================
# AUTH — LOGOUT
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/logout', methods=['POST'])
@token_required
# API controller routing routine executing client transactions
def user_logout():
    """
    Records the logout time in Login_Log for the user's most recent session.
    This enables the admin to see session duration in the login logs.

    Note: Admin logout does not update Login_Log because admins have
          no Login_Log entry (FK constraint points to User table only).
    """
    user_id = request.user.get('user_id')
    role    = request.user.get('role')

    # Safety try guard tracking runtime execution exceptions
    try:
        if role == 'user':
            db     = get_db()
            # Spawns dynamic query cursor translating database rows to accessible structures
            cursor = db.cursor()
            # Update only the most recent open session (logout_time IS NULL)
            # Executes custom SQL script parameter patterns securely
            cursor.execute("""
                UPDATE Login_Log
                SET    logout_time = NOW()
                WHERE  user_id     = %s
                  AND  logout_time IS NULL
                ORDER  BY login_time DESC
                LIMIT  1
            """, (user_id,))
            # Saves SQL updates and data insertion records securely to system storage
            db.commit()
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'Logged out successfully'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# EMAIL HELPERS
# ============================================================

# API controller routing routine executing client transactions
def send_reset_email(to_email, name, otp):
    """
    Sends an HTML email containing the OTP for password reset.
    Uses Gmail SMTP with TLS encryption (port 587).
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'EmpowerAccess — Password Reset OTP'
    msg['From']    = EMAIL_FROM
    msg['To']      = to_email

    html = f"""
    <div style="font-family:Poppins,sans-serif;max-width:500px;margin:auto;
                background:#0E6958;padding:40px;border-radius:20px;color:white;">
        <h2 style="color:#E1C300;">EmpowerAccess</h2>
        <p>Hi <strong>{name}</strong>,</p>
        <p>Your password reset OTP is:</p>
        <div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#E1C300;
                    text-align:center;padding:20px;background:rgba(255,255,255,0.1);
                    border-radius:12px;margin:20px 0;">
            {otp}
        </div>
        <p>This OTP is valid for <strong>10 minutes</strong>.</p>
        <p style="opacity:0.7;font-size:12px;">
            If you did not request this, please ignore this email.
        </p>
        <p style="opacity:0.7;font-size:12px;">— EmpowerAccess Team</p>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))

    # Connect to Gmail SMTP, upgrade to TLS, then send
    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()                        # encrypt the connection
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())


# API controller routing routine executing client transactions
def send_announcement_email(to_email, name, subject, message):
    """
    Sends an HTML announcement email to a single user.
    Called in a loop by the admin announce endpoint for all active users.
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = EMAIL_FROM
    msg['To']      = to_email

    # Replace newlines in the message with <br> so they show in HTML email
    html_message = message.replace('\n', '<br>')

    html = f"""
    <div style="font-family:Poppins,sans-serif;max-width:500px;margin:auto;
                background:#0E6958;padding:40px;border-radius:20px;color:white;">
        <h2 style="color:#E1C300;">EmpowerAccess</h2>
        <p>Hi <strong>{name}</strong>,</p>
        <div style="background:rgba(255,255,255,0.1);padding:20px;
                    border-radius:12px;margin:20px 0;line-height:1.7;">
            {html_message}
        </div>
        <p style="opacity:0.7;font-size:12px;">— EmpowerAccess Admin Team</p>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())


# API controller routing routine executing client transactions
def send_contact_email(name, email, subject, message):
    """
    Sends an email from the contact form to the developer's email.
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Contact Form: {subject}"
    msg['From']    = EMAIL_FROM
    msg['To']      = EMAIL_USER  # Send to the developer
    msg['Reply-To'] = email      # So the developer can reply directly to the user

    html = f"""
    <div style="font-family:Poppins,sans-serif;max-width:500px;margin:auto;
                background:#f0ece4;padding:40px;border-radius:20px;color:#1e1b2e;
                border: 1px solid #ddd;">
        <h2 style="color:#5b6af0;">New Message from EmpowerAccess</h2>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Subject:</strong> {subject}</p>
        <div style="background:white;padding:20px;
                    border-radius:12px;margin:20px 0;line-height:1.7;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            {message.replace('\n', '<br>')}
        </div>
        <p style="opacity:0.7;font-size:12px;">This message was sent from the contact form on your website.</p>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())


# ============================================================
# USER — GET PROFILE
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/profile', methods=['GET'])
@token_required
# API controller routing routine executing client transactions
def user_get_profile():
    """
    Returns the logged-in user's profile data.
    Used by the Profile tab in user_dashboard.html to pre-fill the form.
    """
    user_id = request.user.get('user_id')

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT user_id, name, email, phone, emergency_contact, city, status, created_at FROM User WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        if user:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': True, 'user': user})
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'User not found'}), 404

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# USER — UPDATE PROFILE
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/profile', methods=['PUT'])
@token_required
# API controller routing routine executing client transactions
def user_update_profile():
    """
    Updates the user's name and phone number.
    Email cannot be changed (it is the login identifier).

    Expected JSON body:
        { name, phone }
    """
    user_id = request.user.get('user_id')
    data    = request.get_json()
    name    = data.get('name', '').strip()
    phone   = data.get('phone', '').strip()

    if not name:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Name is required'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        em_contact = data.get('emergency_contact', '').strip()
        city = data.get('city', '').strip()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "UPDATE User SET name = %s, phone = %s, emergency_contact = %s, city = %s WHERE user_id = %s",
            (name, phone or None, em_contact or None, city or None, user_id)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'Profile updated successfully!'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# USER — CHANGE PASSWORD
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/change-password', methods=['POST'])
@token_required
# API controller routing routine executing client transactions
def user_change_password():
    """
    Allows a logged-in user to change their password.
    Requires the current password for verification before setting new one.

    Expected JSON body:
        { currentPassword, newPassword }
    """
    user_id  = request.user.get('user_id')
    data     = request.get_json()
    curr_pwd = data.get('currentPassword', '')
    new_pwd  = data.get('newPassword', '')

    if not curr_pwd or not new_pwd:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Both fields are required'}), 400

    if len(new_pwd) < 6:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'New password must be at least 6 characters'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)

        # Fetch the stored hashed password for this user
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT password FROM User WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        # Verify the current password they entered matches the hash in DB
        if not user or not bcrypt.checkpw(curr_pwd.encode(), user['password'].encode()):
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401

        # Hash the new password and update
        hashed = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "UPDATE User SET password = %s WHERE user_id = %s",
            (hashed, user_id)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'Password changed successfully!'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# USER — WEATHER
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/weather', methods=['GET'])
@token_required
# API controller routing routine executing client transactions
def user_weather():
    """
    Fetches real-time weather data for a given city.

    How it works:
        1. Use Open-Meteo Geocoding API to convert city name → lat/lon
        2. Use Open-Meteo Forecast API to get current weather
        3. Save the result to Weather_Log table for admin monitoring

    Query param: ?city=Mumbai
    Returns: { city, country, temperature, description, humidity, wind_speed }
    """
    user_id = request.user.get('user_id')
    city    = request.args.get('city', '').strip()

    if not city:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'City name is required'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        import urllib.request
        import urllib.parse
        import json as _json

        # ── Step 1: Geocode the city name to get coordinates ──
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        with urllib.request.urlopen(geo_url, timeout=8) as resp:
            geo = _json.loads(resp.read())

        if not geo.get('results'):
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': f'City "{city}" not found'}), 404

        loc     = geo['results'][0]
        lat     = loc['latitude']
        lon     = loc['longitude']
        country = loc.get('country', '')

        # ── Step 2: Fetch current weather using coordinates ──
        w_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current_weather=true"
            f"&hourly=relativehumidity_2m,windspeed_10m"
        )
        with urllib.request.urlopen(w_url, timeout=8) as resp:
            w = _json.loads(resp.read())

        cw   = w['current_weather']
        temp = round(cw['temperature'], 1)
        wind = round(cw['windspeed'], 1)

        # Humidity is from hourly data — take the first (current) value
        hum  = w['hourly']['relativehumidity_2m'][0] if w['hourly']['relativehumidity_2m'] else 0

        # ── Step 3: Convert weather code to human-readable description ──
        # Open-Meteo uses WMO weather codes — map the common ones
        codes = {
            0: 'Clear sky',    1: 'Mainly clear',   2: 'Partly cloudy',
            3: 'Overcast',    45: 'Foggy',          48: 'Icy fog',
           51: 'Light drizzle',61: 'Rain',           71: 'Snow',
           80: 'Rain showers', 95: 'Thunderstorm'
        }
        desc = codes.get(cw.get('weathercode', 0), 'Unknown')

        # ── Step 4: Log this weather query to the database ──
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "INSERT INTO Weather_Log (user_id, city, temperature, `condition`) VALUES (%s, %s, %s, %s)",
            (user_id, city, temp, desc)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success': True,
            'data': {
                'city':        loc['name'],
                'country':     country,
                'temperature': temp,
                'description': desc,
                'humidity':    hum,
                'wind_speed':  wind
            }
        })

    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Weather error: {str(e)}'}), 500


# ============================================================
# USER — NEWS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/news', methods=['GET'])
@token_required
# API controller routing routine executing client transactions
def user_news():
    """
    Fetches top news headlines from GNews API.

    Query param: ?category=technology  (technology/sports/business/health/science/entertainment)
    Returns: list of { title, url, source, published_at, description }

    If country-filtered fetch returns no articles, retries without country filter.
    Logs the first article to News_Log for admin monitoring.
    """
    user_id  = request.user.get('user_id')
    category = request.args.get('category', 'technology')

    # Safety try guard tracking runtime execution exceptions
    try:
        import urllib.request
        import urllib.error
        import json as _json

        GNEWS_KEY = os.getenv('GNEWS_KEY', '')
        if not GNEWS_KEY:
            return jsonify({
                'success': False,
                'message': 'GNews API key not configured. Set GNEWS_KEY in your environment.'
            }), 503

        # ── First attempt: fetch India-specific headlines ──
        url = (
            f"https://gnews.io/api/v4/top-headlines"
            f"?category={category}&lang=en&country=in&max=6&apikey={GNEWS_KEY}"
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        # Safety try guard tracking runtime execution exceptions
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data     = _json.loads(r.read())
            articles = data.get('articles', [])

            # ── Fallback: if no India articles, try without country filter ──
            if not articles:
                url2 = (
                    f"https://gnews.io/api/v4/top-headlines"
                    f"?category={category}&lang=en&max=6&apikey={GNEWS_KEY}"
                )
                req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    articles = _json.loads(r2.read()).get('articles', [])

            if not articles:
                # Translates python dictionary records back to standard JSON returns format
                return jsonify({'success': False, 'message': 'No articles found for this category'}), 404

            # Format the response — only keep fields the frontend needs
            result = [
                {
                    'title':        a.get('title', 'No Title'),
                    'url':          a.get('url', '#'),
                    'source':       a.get('source', {}).get('name', 'Unknown'),
                    'published_at': a.get('publishedAt'),
                    'description':  a.get('description', '')
                }
                for a in articles
            ]

        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='ignore')
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': f'GNews error {e.code}: {body}'}), 500

        # ── Log the first article to News_Log ──
        if result:
            db     = get_db()
            # Spawns dynamic query cursor translating database rows to accessible structures
            cursor = db.cursor()
            # Executes custom SQL script parameter patterns securely
            cursor.execute(
                "INSERT INTO News_Log (user_id, news_title, category, source) VALUES (%s, %s, %s, %s)",
                (user_id, result[0]['title'], category, result[0].get('source', ''))
            )
            # Saves SQL updates and data insertion records securely to system storage
            db.commit()
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'articles': result})

    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ============================================================
# USER — STOCK PRICE
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/stock', methods=['GET'])
@token_required
# API controller routing routine executing client transactions
def user_stock():
    """
    Fetches the current stock price from Yahoo Finance (unofficial API).
    Appends '.NS' to the symbol for NSE (Indian) stocks.

    Query param: ?symbol=RELIANCE  (or TCS, INFY, WIPRO, etc.)
    Returns: { symbol, company_name, price, currency }

    Note: Works for NSE stocks. For US stocks remove the .NS suffix.
    """
    user_id = request.user.get('user_id')
    symbol  = request.args.get('symbol', '').strip().upper()

    if not symbol:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Stock symbol is required'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        import urllib.request
        import json as _json

        # Yahoo Finance chart API — .NS suffix = NSE (National Stock Exchange India)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1d&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        with urllib.request.urlopen(req, timeout=8) as r:
            data = _json.loads(r.read())

        result = data['chart']['result']
        if not result:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': f'Symbol "{symbol}" not found'}), 404

        meta  = result[0]['meta']
        price = round(meta.get('regularMarketPrice', 0), 2)
        curr  = meta.get('currency', 'INR')
        name  = meta.get('shortName', symbol)

        # ── Log this stock query ──
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "INSERT INTO Stock_Log (user_id, company_name, stock_symbol, price, currency) VALUES (%s, %s, %s, %s, %s)",
            (user_id, name, symbol, price, curr)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success': True,
            'data': {
                'symbol':       symbol,
                'company_name': name,
                'price':        price,
                'currency':     curr
            }
        })

    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Stock error: {str(e)}'}), 500


# ============================================================
# USER — VOICE / TEXT COMMAND  (logs all .exe commands)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/command', methods=['POST'])
@token_required
# API controller routing routine executing client transactions
def user_command():
    """
    Central command logging endpoint for the .exe desktop app.

    Every command the user speaks or types in the .exe is sent here.
    The backend detects the intent and returns an appropriate response.
    The command is always saved to Command_Log regardless of intent.

    Intent types:
        weather    → direct to weather section
        news       → direct to news section
        stock      → direct to stock section
        sos        → direct to SOS section
        greeting   → "Hello! I am EmpowerAccess..."
        time       → return current time
        date       → return today's date
        file       → file management command (executed locally in .exe)
        folder     → folder management command (executed locally in .exe)
        app_open   → open application command (executed locally in .exe)
        app_close  → close application command (executed locally in .exe)
        system     → shutdown/restart/sleep/lock/volume (executed locally)
        internet   → search/open website (executed locally in .exe)
        reminder   → set reminder/timer (executed locally in .exe)
        sysinfo    → CPU/RAM/battery (use /api/user/sysinfo for data)
        ai         → ask/explain/translate (use /api/user/ai for response)
        general    → catch-all for unrecognised commands

    Expected JSON body:
        { command: "open chrome" }

    Returns:
        { success, response, intent }
    """
    user_id = request.user.get('user_id')
    data    = request.get_json()
    command = data.get('command', '').strip()

    if not command:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Command text is required'}), 400

    cmd   = command.lower()   # lowercase for easy keyword matching
    intent  = 'general'
    response = ''
    # Imports datetime packages to compute auth sessions expiration limits
    import datetime
    from core.intent_router import match_intent
    
    user_id  = request.user.get('user_id')
    data     = request.get_json()
    command  = data.get('command', '').strip()
    status   = 'success'

    # Safety try guard tracking runtime execution exceptions
    try:
        # ── Unified Intent Detection ──
        result = match_intent(command)
        intent = result.intent
        confidence = result.confidence
        response = ""

        # Special check for software updates before processing standard intents
        is_update_request = any(w in command.lower() for w in ['check update', 'update software', 'new version', 'show version', 'software version'])
        
        if is_update_request:
            intent = 'update'
            response = 'Checking for software updates.'
        elif intent == 'greeting':
            response = 'GREETINGS!! Ready to assist you?'
        elif intent == 'time':
            response = f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."
        elif intent == 'date':
            response = f"Today is {datetime.datetime.now().strftime('%A, %d %B %Y')}."
        elif intent == 'weather':
            response = 'Getting weather data. Use the weather feature for full details.'
        elif intent == 'news':
            response = 'Fetching latest headlines for you.'
        elif intent == 'stock':
            response = 'Use the stock feature with a symbol like RELIANCE or TCS.'
        elif intent == 'sysinfo':
            response = 'Fetching system telemetry. Calling /api/user/sysinfo.'
        elif intent == 'ai':
            if confidence > 0:
                response = 'Processing your AI request. Calling /api/user/ai.'
            else:
                response = "I'm not sure about that command. Falling back to AI assistant."
        elif intent == 'sos':
            response = 'Oops! SOS detected, Sending emergency alert immediately.'
        elif intent != 'general':
            # For specific actions (file, folder, system, app windows etc.)
            response = f'Executing {intent.replace("_", " ")} command on your system.'
        else:
            # Absolute fallback if still 'general'
            intent = 'general'
            response = (
                f"You said: '{command}'. I understand your request. "
                f"Try asking about weather, news, stocks, or say SOS for emergency."
            )

        # ── Save every command to Command_Log ──
        # This is what the admin sees in the Commands tab of admin_dashboard
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            """INSERT INTO Command_Log
               (user_id, command_text, intent_type, response_text, execution_status)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, command, intent, response, status)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'response': response, 'intent': intent})

    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Log failed commands too so admin can see errors
        # Safety try guard tracking runtime execution exceptions
        try:
            db     = get_db()
            # Spawns dynamic query cursor translating database rows to accessible structures
            cursor = db.cursor()
            # Executes custom SQL script parameter patterns securely
            cursor.execute(
                """INSERT INTO Command_Log
                   (user_id, command_text, intent_type, response_text, execution_status)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, command, 'error', str(e), 'failed')
            )
            # Saves SQL updates and data insertion records securely to system storage
            db.commit()
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
        # Fallback catch safety wrapper reporting errors gracefully
        except Exception:
            pass   # if even logging fails, just return the error

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# USER — SOS EMERGENCY ALERT
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/sos', methods=['POST'])
@token_required
# API controller routing routine executing client transactions
def user_sos():
    """
    Records an emergency SOS alert from the .exe app.
    Status is set to 'triggered' — admin can change it to 'resolved'.

    Expected JSON body:
        { location: "Bangalore", emergency_contact: "9876543210" }
    """
    user_id  = request.user.get('user_id')
    data     = request.get_json()
    location = data.get('location', 'Unknown')
    contact  = data.get('emergency_contact', '')

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            """INSERT INTO SOS_Log (user_id, location, emergency_contact, status)
               VALUES (%s, %s, %s, 'triggered')""",
            (user_id, location, contact)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # ── Twilio SMS Execution ──
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and contact:
            # Safety try guard tracking runtime execution exceptions
            try:
                import urllib.request, urllib.parse, base64
                
                # Format to E.164 International
                sms_to = contact if contact.startswith('+') else f"+91{contact}" if len(contact) == 10 else f"+{contact}"
                sms_from = TWILIO_PHONE_FROM if TWILIO_PHONE_FROM.startswith('+') else f"+{TWILIO_PHONE_FROM}"
                
                body = f"⚠ EMERGENCY SOS ALERT  ⚠\nUser has triggered an alarm.\nLocation: {location}\nSend Help Immediately!"
                url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
                
                payload = urllib.parse.urlencode({'To': sms_to, 'From': sms_from, 'Body': body}).encode('utf-8')
                auth_str = f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}"
                b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
                
                req = urllib.request.Request(url, data=payload, headers={'Authorization': f"Basic {b64_auth}"}, method='POST')
                urllib.request.urlopen(req, timeout=10)
            # Fallback catch safety wrapper reporting errors gracefully
            except Exception as e:
                print(f"Twilio SMS Warning: {e}")

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'SOS alert recorded. Emergency services notified.'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# USER — SYSTEM INFO  (NEW)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
# ============================================================
# USER - SEND PROFILE SMS MESSAGE
# ============================================================

@app.route('/api/user/send-sms', methods=['POST'])
@token_required
def user_send_sms():
    """
    Sends a user-written SMS to the emergency contact saved in their profile.
    Optional JSON body:
        { message: "I need help", recipient: "emergency" | "phone" }
    """
    user_id = request.user.get('user_id')
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    recipient = data.get('recipient', 'emergency').strip().lower()

    if not message:
        return jsonify({'success': False, 'message': 'Message text is required'}), 400
    if len(message) > 500:
        return jsonify({'success': False, 'message': 'Message must be 500 characters or less'}), 400
    if recipient not in ('emergency', 'phone'):
        return jsonify({'success': False, 'message': 'Recipient must be emergency or phone'}), 400

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT name, phone, emergency_contact FROM User WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close(); db.close()

        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        contact = user.get('phone') if recipient == 'phone' else user.get('emergency_contact')
        if not contact:
            label = 'phone number' if recipient == 'phone' else 'emergency contact'
            return jsonify({'success': False, 'message': f'No {label} saved in your profile'}), 400

        body = f"EmpowerAccess message from {user.get('name') or 'User'}:\n{message}"
        sms_to = send_twilio_sms(contact, body)

        return jsonify({
            'success': True,
            'message': 'SMS sent successfully',
            'to': sms_to
        })

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'SMS failed: {str(e)}'}), 500


@app.route('/api/user/sysinfo', methods=['GET'])
@token_required
# API controller routing routine executing client transactions
def user_sysinfo():
    """
    Returns real-time system statistics using the psutil library.
    Called by the .exe when user says "CPU usage", "RAM usage", etc.

    No database logging here — the .exe will call /api/user/command
    separately to log the command to Command_Log.

    Returns:
        {
          cpu_percent   : float  — current CPU usage %
          ram_used      : float  — used RAM in GB
          ram_total     : float  — total RAM in GB
          ram_percent   : float  — RAM usage %
          disk_used     : float  — used disk in GB
          disk_total    : float  — total disk in GB
          disk_percent  : float  — disk usage %
          battery       : float or null  — battery % (null if desktop)
          battery_plugged: bool or null  — whether charger is connected
        }
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        # ── CPU ──
        # interval=1 means measure CPU over 1 second for accuracy
        cpu_percent = psutil.cpu_percent(interval=1)

        # ── RAM ──
        ram         = psutil.virtual_memory()
        ram_used    = round(ram.used  / (1024 ** 3), 2)    # convert bytes → GB
        ram_total   = round(ram.total / (1024 ** 3), 2)
        ram_percent = ram.percent

        # ── Disk ──
        disk         = psutil.disk_usage('/')
        disk_used    = round(disk.used  / (1024 ** 3), 2)
        disk_total   = round(disk.total / (1024 ** 3), 2)
        disk_percent = disk.percent

        # ── Battery ── (returns None if no battery — desktop PC)
        battery         = psutil.sensors_battery()
        battery_percent = round(battery.percent, 1) if battery else None
        battery_plugged = battery.power_plugged       if battery else None

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success': True,
            'data': {
                'cpu_percent':    cpu_percent,
                'ram_used':       ram_used,
                'ram_total':      ram_total,
                'ram_percent':    ram_percent,
                'disk_used':      disk_used,
                'disk_total':     disk_total,
                'disk_percent':   disk_percent,
                'battery':        battery_percent,
                'battery_plugged': battery_plugged
            }
        })

    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'System info error: {str(e)}'}), 500


# ============================================================
# USER — AI COMMAND  (NEW)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/ai', methods=['POST'])
@token_required
# API controller routing routine executing client transactions
def user_ai():
    """
    Processes AI commands like explain, translate, summarise, generate code.
    Uses Google Gemini API (free tier available).

    How to get your Gemini API key (free):
        1. Go to https://aistudio.google.com/app/apikey
        2. Click "Create API Key"
        3. Set GEMINI_API_KEY in your environment before running the app

    Expected JSON body:
        { prompt: "Explain machine learning in simple words" }

    Returns:
        { success, response: "AI generated text..." }
    """
    user_id = request.user.get('user_id')
    data    = request.get_json()
    prompt  = data.get('prompt', '').strip()

    if not prompt:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Prompt is required'}), 400

    # Check if API key has been configured
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE' or GEMINI_API_KEY == '':
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success': False,
            'message': 'Gemini API key not configured. Set GEMINI_API_KEY in your environment.'
        }), 503

    # Safety try guard tracking runtime execution exceptions
    try:
        import urllib.request
        import urllib.error
        import json as _json

        # Using gemini-2.5-flash — updated per user request
        gemini_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        )

        # Gemini expects a specific JSON structure for the request body
        payload = _json.dumps({
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }).encode('utf-8')

        req = urllib.request.Request(
            gemini_url,
            data    = payload,
            headers = {'Content-Type': 'application/json'},
            method  = 'POST'
        )

        # Safety try guard tracking runtime execution exceptions
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                result = _json.loads(resp.read())
        except urllib.error.HTTPError as he:
            # Safety try guard tracking runtime execution exceptions
            try:
                # Try to parse the Gemini error JSON body
                error_data = _json.loads(he.read().decode('utf-8'))
                gemini_msg = error_data.get('error', {}).get('message', 'Unknown Gemini error')
            except:
                gemini_msg = f"HTTP {he.code}"

            # Provide friendly messages for common errors
            if he.code == 429:
                final_msg = "Gemini AI is currently busy (Rate limit reached). Please wait a few seconds and try again."
            elif he.code == 401:
                final_msg = "Invalid AI API Key. Please check the GEMINI_API_KEY in app.py."
            else:
                final_msg = f"AI Service Error: {gemini_msg}"

            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': final_msg}), he.code

        # Extract the text from Gemini's response structure
        ai_response = (
            result
            .get('candidates', [{}])[0]
            .get('content', {})
            .get('parts', [{}])[0]
            .get('text', 'No response from AI')
        )

        # ── Log the AI command ──
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            """INSERT INTO Command_Log
               (user_id, command_text, intent_type, response_text, execution_status)
               VALUES (%s, %s, 'ai', %s, 'success')""",
            (user_id, prompt, ai_response[:500])   # truncate to 500 chars for DB
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'response': ai_response})

    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': f'Internal Server Error: {str(e)}'}), 500


# ============================================================
# USER — ACTIVITY FEED
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/user/activity', methods=['GET'])
@token_required
# API controller routing routine executing client transactions
def user_activity():
    """
    Returns a combined feed of the user's recent activity across all logs.
    Used by the .exe to show the user their history.

    Query params:
        ?type=all          (all | weather | news | stocks | commands)
        ?limit=20          (number of records to return)
    """
    user_id = request.user.get('user_id')
    type_   = request.args.get('type', 'all')
    limit   = int(request.args.get('limit', 20))
    items   = []

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)

        # Fetch from each log table based on the requested type filter
        if type_ in ('all', 'weather'):
            # Executes custom SQL script parameter patterns securely
            cursor.execute(
                "SELECT 'weather' AS type, city AS title, request_time AS time "
                "FROM Weather_Log WHERE user_id=%s ORDER BY request_time DESC LIMIT %s",
                (user_id, limit)
            )
            items += cursor.fetchall()

        if type_ in ('all', 'news'):
            # Executes custom SQL script parameter patterns securely
            cursor.execute(
                "SELECT 'news' AS type, news_title AS title, request_time AS time "
                "FROM News_Log WHERE user_id=%s ORDER BY request_time DESC LIMIT %s",
                (user_id, limit)
            )
            items += cursor.fetchall()

        if type_ in ('all', 'stocks'):
            # Executes custom SQL script parameter patterns securely
            cursor.execute(
                "SELECT 'stock' AS type, "
                "CONCAT(company_name,' — ',currency,' ',price) AS title, "
                "request_time AS time "
                "FROM Stock_Log WHERE user_id=%s ORDER BY request_time DESC LIMIT %s",
                (user_id, limit)
            )
            items += cursor.fetchall()

        if type_ in ('all', 'commands'):
            # Executes custom SQL script parameter patterns securely
            cursor.execute(
                "SELECT 'command' AS type, command_text AS title, timestamp AS time "
                "FROM Command_Log WHERE user_id=%s ORDER BY timestamp DESC LIMIT %s",
                (user_id, limit)
            )
            items += cursor.fetchall()

        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Sort all items by time descending and return only 'limit' items
        items.sort(key=lambda x: str(x.get('time') or ''), reverse=True)

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'items': items[:limit]})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# SOFTWARE VERSION — GET LATEST  (used by .exe to check updates)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/version', methods=['GET'])
# API controller routing routine executing client transactions
def get_version():
    """
    Returns the latest software version from the database.
    Called by the .exe on startup to check if an update is available.

    No authentication required — the .exe may call this before login.

    Returns:
        { version_number, release_date, description, download_url }
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)

        # Get the most recently added version record
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT version_number, release_date, description FROM Software_Version "
            "ORDER BY version_id DESC LIMIT 1"
        )
        version = cursor.fetchone()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        if not version:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'No version found'}), 404

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success':      True,
            'version':      version['version_number'],
            'release_date': str(version['release_date']),
            'description':  version['description'],
            # Download URL — the .exe file must be in the same folder as app.py
            'download_url': 'http://localhost:5000/EmpowerAccess.exe'
        })

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# SOFTWARE VERSION — DOWNLOAD  (NEW)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/version/download', methods=['GET'])
# API controller routing routine executing client transactions
def download_version():
    """
    Serves the EmpowerAccess.exe file for download.
    Called by the .exe when an update is available and user confirms download.

    The .exe file must be placed in the same folder as app.py.
    Flask's send_from_directory handles the file streaming safely.
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        # send_from_directory safely serves a file from a directory
        # '.' means the current directory (same folder as app.py)
        # Returns processed data outputs back to calling functions
        return send_from_directory(
            '.',
            'EmpowerAccess.exe',
            as_attachment=True   # tells browser to download instead of open
        )
    except FileNotFoundError:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success': False,
            'message': 'EmpowerAccess.exe not found on server. Contact admin.'
        }), 404


# ============================================================
# ADMIN — OVERVIEW STATS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/stats', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_stats():
    """
    Returns summary statistics for the admin dashboard overview cards.

    Returns:
        stats: { total_users, active_users, commands_today, sos_total }
        recent_users: last 5 registered users
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)

        # COUNT(*) returns total rows — rename with AS for clarity
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT COUNT(*) AS total FROM User")
        total_users = cursor.fetchone()['total']

        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT COUNT(*) AS total FROM User WHERE status = 'active'")
        active_users = cursor.fetchone()['total']

        # CURDATE() returns today's date — filter commands from today only
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT COUNT(*) AS total FROM Command_Log WHERE DATE(timestamp) = CURDATE()"
        )
        commands_today = cursor.fetchone()['total']

        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT COUNT(*) AS total FROM SOS_Log")
        sos_total = cursor.fetchone()['total']

        # ── Commands by Categorized Intent (Donut Chart) ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN intent_type = 'ai' THEN 'AI'
                    WHEN intent_type = 'llm_fallback' THEN 'LLM Fallback'
                    WHEN intent_type = 'app_open' THEN 'Open App'
                    WHEN intent_type = 'app_close' THEN 'Close App'
                    WHEN intent_type IN ('web_search', 'open_url', 'youtube') THEN 'Web Search'
                    WHEN intent_type IN ('folder_open', 'folder_create', 'file_open', 'file_create', 'file_delete') THEN 'File Management'
                    WHEN intent_type = 'screenshot' THEN 'Screenshots'
                    WHEN intent_type IN ('weather', 'news', 'stock') THEN 'Web API (News, Stock, Weather)'
                    WHEN intent_type IN ('sysinfo', 'timer', 'reminder', 'alarm', 'vol_up', 'vol_down', 'mute', 'vol_set', 'shutdown', 'restart', 'sleep', 'lock', 'logout', 'exit', 'time', 'date', 'greeting') THEN 'System'
                    ELSE 'Other'
                END AS category,
                COUNT(*) AS count 
            FROM Command_Log 
            GROUP BY category
        """)
        intent_stats = cursor.fetchall()

        # ── Daily Command Activity (Last 7 Days) ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT DATE(timestamp) AS date, COUNT(*) AS count 
            FROM Command_Log 
            WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) 
            GROUP BY DATE(timestamp) 
            ORDER BY date ASC
        """)
        daily_activity = cursor.fetchall()

        # ── User Registration Trend (Last 30 Days) ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT DATE(created_at) AS day, COUNT(*) AS count 
            FROM User 
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY day 
            ORDER BY day ASC
        """)
        registration_trend = cursor.fetchall()

        # ── Device Distribution (Pie Chart) ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT device_type, COUNT(*) AS count FROM Login_Log GROUP BY device_type")
        device_stats = cursor.fetchall()

        # Fetch 5 most recently registered users for the Recent Registrations card
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT user_id, name, email, status, created_at "
            "FROM User ORDER BY created_at DESC LIMIT 5"
        )
        recent_users = cursor.fetchall()

        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success': True,
            'stats': {
                'total_users':    total_users,
                'active_users':   active_users,
                'commands_today': commands_today,
                'sos_total':      sos_total,
                'intent_stats':   intent_stats,
                'daily_activity': daily_activity,
                'registration_trend': registration_trend,
                'device_stats':   device_stats
            },
            'recent_users': recent_users
        })

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — USER-SPECIFIC OVERVIEW STATS  (overview search bar)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/stats/user', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_user_stats():
    """
    Returns overview statistics filtered to a single user matched by name.
    Called when the admin types a name in the overview search bar.

    Query param:
        ?name=<partial username>   (case-insensitive LIKE match)

    Returns the same structure as /api/admin/stats so the frontend
    can reuse the exact same chart-building code.
    """
    name_q = request.args.get('name', '').strip()
    if not name_q:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'name param required'}), 400

    like = f'%{name_q}%'

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)

        # ── Find matching users ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT user_id, name, email, status, created_at "
            "FROM User WHERE name LIKE %s ORDER BY created_at DESC",
            (like,)
        )
        matched_users = cursor.fetchall()
        user_ids = [u['user_id'] for u in matched_users]

        if not user_ids:
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'No users found matching that name'}), 404

        # Build IN clause placeholder  e.g. (%s,%s,%s)
        placeholders = ','.join(['%s'] * len(user_ids))

        # ── Stat card counts ──
        total_users  = len(matched_users)
        active_users = sum(1 for u in matched_users if u['status'] == 'active')

        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM Command_Log "
            f"WHERE DATE(timestamp) = CURDATE() AND user_id IN ({placeholders})",
            user_ids
        )
        commands_today = cursor.fetchone()['total']

        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM SOS_Log WHERE user_id IN ({placeholders})",
            user_ids
        )
        sos_total = cursor.fetchone()['total']

        # ── Command intent distribution for these users ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute(f"""
            SELECT
                CASE
                    WHEN intent_type = 'ai' THEN 'AI'
                    WHEN intent_type = 'llm_fallback' THEN 'LLM Fallback'
                    WHEN intent_type = 'app_open' THEN 'Open App'
                    WHEN intent_type = 'app_close' THEN 'Close App'
                    WHEN intent_type IN ('web_search', 'open_url', 'youtube') THEN 'Web Search'
                    WHEN intent_type IN ('folder_open', 'folder_create', 'file_open', 'file_create', 'file_delete') THEN 'File Management'
                    WHEN intent_type = 'screenshot' THEN 'Screenshots'
                    WHEN intent_type IN ('weather', 'news', 'stock') THEN 'Web API (News, Stock, Weather)'
                    WHEN intent_type IN ('sysinfo', 'timer', 'reminder', 'alarm', 'vol_up', 'vol_down', 'mute',
                                         'vol_set', 'shutdown', 'restart', 'sleep', 'lock', 'logout', 'exit',
                                         'time', 'date', 'greeting') THEN 'System'
                    ELSE 'Other'
                END AS category,
                COUNT(*) AS count
            FROM Command_Log
            WHERE user_id IN ({placeholders})
            GROUP BY category
        """, user_ids)
        intent_stats = cursor.fetchall()

        # ── Daily activity (last 7 days) for these users ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute(f"""
            SELECT DATE(timestamp) AS date, COUNT(*) AS count
            FROM Command_Log
            WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
              AND user_id IN ({placeholders})
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
        """, user_ids)
        daily_activity = cursor.fetchall()

        # ── Registration trend (Last 30 Days) for these users ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute(f"""
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM User
            WHERE user_id IN ({placeholders})
              AND created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY day
            ORDER BY day ASC
        """, user_ids)
        registration_trend = cursor.fetchall()

        # ── Device distribution for these users ──
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            f"SELECT device_type, COUNT(*) AS count FROM Login_Log "
            f"WHERE user_id IN ({placeholders}) GROUP BY device_type",
            user_ids
        )
        device_stats = cursor.fetchall()

        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success': True,
            'filtered_name': name_q,
            'stats': {
                'total_users':        total_users,
                'active_users':       active_users,
                'commands_today':     commands_today,
                'sos_total':          sos_total,
                'intent_stats':       intent_stats,
                'daily_activity':     daily_activity,
                'registration_trend': registration_trend,
                'device_stats':       device_stats
            },
            'recent_users': matched_users[:10]
        })

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — GET ALL USERS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/users', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_get_users():
    """
    Returns all registered users ordered by most recently joined.
    Displayed in the Users tab of admin_dashboard with search and actions.
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT user_id, name, email, phone, status, created_at "
            "FROM User ORDER BY created_at DESC"
        )
        users = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'users': users})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — TOGGLE USER STATUS (enable / disable)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/users/<int:user_id>/status', methods=['PUT'])
@admin_required
# API controller routing routine executing client transactions
def admin_toggle_user(user_id):
    """
    Enables or disables a user account.
    Disabled users cannot login — they get a 403 at the login endpoint.

    URL param   : user_id (int)
    JSON body   : { status: "active" | "disabled" }
    """
    data   = request.get_json()
    status = data.get('status')

    if status not in ('active', 'disabled'):
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Status must be "active" or "disabled"'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "UPDATE User SET status = %s WHERE user_id = %s",
            (status, user_id)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': f'User {status} successfully'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — DELETE USER
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
# API controller routing routine executing client transactions
def admin_delete_user(user_id):
    """
    Permanently deletes a user and all their associated logs.
    MySQL CASCADE will automatically delete related rows in:
        Login_Log, Command_Log, SOS_Log, Weather_Log, News_Log, Stock_Log
    Make sure ON DELETE CASCADE is set in your DB schema foreign keys.

    URL param: user_id (int)
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute("DELETE FROM User WHERE user_id = %s", (user_id,))
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'User deleted successfully'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — LOGIN LOGS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/login_logs', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_login_logs():
    """
    Returns login history with session duration for all users.
    Displayed in the Logins tab of admin_dashboard.

    Calculates duration_seconds using TIMESTAMPDIFF between login and logout.
    If logout_time is NULL the session is still active.
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT
                ll.login_id,
                u.name        AS user_name,
                u.email       AS user_email,
                ll.login_time,
                ll.logout_time,
                ll.ip_address,
                ll.device_type,
                CASE
                    WHEN ll.logout_time IS NOT NULL
                    THEN TIMESTAMPDIFF(SECOND, ll.login_time, ll.logout_time)
                    ELSE NULL
                END AS duration_seconds
            FROM Login_Log ll
            LEFT JOIN User u ON ll.user_id = u.user_id
            ORDER BY ll.login_time DESC
            LIMIT 100
        """)
        data = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'data': data})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — COMMAND LOGS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/command_logs', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_command_logs():
    """
    Returns all voice/text commands made by users through the .exe.
    Shows command text, intent type, response, and status.
    Displayed in the Commands tab of admin_dashboard.
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT cl.*, u.name AS user_name
            FROM   Command_Log cl
            LEFT   JOIN User u ON cl.user_id = u.user_id
            ORDER  BY cl.timestamp DESC
            LIMIT  100
        """)
        data = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'data': data})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — SOS LOGS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/sos_logs', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_sos_logs():
    """
    Returns all SOS emergency alerts.
    Displayed in the SOS tab of admin_dashboard with a Resolve button.
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT sl.*, u.name AS user_name
            FROM   SOS_Log sl
            LEFT   JOIN User u ON sl.user_id = u.user_id
            ORDER  BY sl.triggered_time DESC
        """)
        data = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'data': data})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — RESOLVE SOS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/sos/<int:sos_id>/resolve', methods=['PUT'])
@admin_required
# API controller routing routine executing client transactions
def admin_resolve_sos(sos_id):
    """
    Marks a SOS alert as resolved.
    The admin clicks the Resolve button in admin_dashboard after handling.

    URL param: sos_id (int)
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "UPDATE SOS_Log SET status = 'resolved' WHERE sos_id = %s",
            (sos_id,)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'SOS alert resolved'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — WEATHER LOGS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/weather_logs', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_weather_logs():
    """Returns all weather queries made by users, with user names."""
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT wl.*, u.name AS user_name
            FROM   Weather_Log wl
            LEFT   JOIN User u ON wl.user_id = u.user_id
            ORDER  BY wl.request_time DESC
            LIMIT  100
        """)
        data = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'data': data})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — NEWS LOGS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/news_logs', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_news_logs():
    """Returns all news queries made by users, with user names."""
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT nl.*, u.name AS user_name
            FROM   News_Log nl
            LEFT   JOIN User u ON nl.user_id = u.user_id
            ORDER  BY nl.request_time DESC
            LIMIT  100
        """)
        data = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'data': data})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — STOCK LOGS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/stock_logs', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_stock_logs():
    """Returns all stock queries made by users, with user names and prices."""
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute("""
            SELECT sl.*, u.name AS user_name
            FROM   Stock_Log sl
            LEFT   JOIN User u ON sl.user_id = u.user_id
            ORDER  BY sl.request_time DESC
            LIMIT  100
        """)
        data = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'data': data})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — SOFTWARE VERSIONS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/versions', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_get_versions():
    """Returns all software version records, newest first."""
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT * FROM Software_Version ORDER BY version_id DESC")
        data = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'data': data})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/versions', methods=['POST'])
@admin_required
# API controller routing routine executing client transactions
def admin_add_version():
    """
    Publishes a new software version entry.
    After publishing, the .exe will detect it on next startup check.

    Expected JSON body:
        { version_number: "1.2.0", release_date: "2026-03-15", description: "Bug fixes" }
    """
    data           = request.get_json()
    version_number = data.get('version_number', '').strip()
    release_date   = data.get('release_date', '').strip()
    description    = data.get('description', '').strip()
    admin_id       = request.user.get('user_id')

    if not version_number or not release_date:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Version number and release date are required'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            """INSERT INTO Software_Version
               (version_number, release_date, description, uploaded_by)
               VALUES (%s, %s, %s, %s)""",
            (version_number, release_date, description, admin_id)
        )
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': f'Version {version_number} published!'})

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — SEND ANNOUNCEMENT EMAIL TO ALL ACTIVE USERS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/announce', methods=['POST'])
@admin_required
# API controller routing routine executing client transactions
def admin_announce():
    """
    Sends an HTML announcement email to every active user.
    Continues even if some emails fail — returns count of successful sends.

    Expected JSON body:
        { subject: "Important update", message: "Dear users..." }
    """
    data    = request.get_json()
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()

    if not subject or not message:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Subject and message are required'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)

        # Only send to active users — disabled users should not receive emails
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT email, name FROM User WHERE status = 'active'")
        users = cursor.fetchall()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()

        if not users:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'No active users found'}), 400

        sent = 0
        for user in users:
            # Safety try guard tracking runtime execution exceptions
            try:
                send_announcement_email(user['email'], user['name'], subject, message)
                sent += 1
            # Fallback catch safety wrapper reporting errors gracefully
            except Exception:
                # Skip users with invalid emails — don't stop the whole batch
                pass

        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': f'Announcement sent to {sent} users!'})

    # Fallback catch safety wrapper reporting errors gracefully
    except Exception as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# UTILITY — GET CURRENT USER INFO  (used for token verification)
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/me', methods=['GET'])
@token_required
# API controller routing routine executing client transactions
def get_me():
    """
    Returns the decoded token data for the logged-in user.
    Useful for the .exe to verify the token is still valid on startup.
    """
    # Translates python dictionary records back to standard JSON returns format
    return jsonify({'success': True, 'user': request.user})


# ============================================================
# ADMIN — BULK DELETE LOGS
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/bulk-delete', methods=['POST'])
@admin_required
# API controller routing routine executing client transactions
def admin_bulk_delete():
    """
    Deletes multiple log entries from a specified table.
    Expects JSON: { type: "logins"|"commands"|"sos"|"weather"|"news"|"stocks"|"users", ids: [1, 2, 3] }
    """
    data = request.get_json()
    type_ = data.get('type')
    ids = data.get('ids', [])

    if not type_ or not ids:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Type and IDs are required'}), 400

    # Map the requested type to the actual database table and primary key
    mapping = {
        'users':    ('User',            'user_id'),
        'logins':   ('Login_Log',       'login_id'),
        'commands': ('Command_Log',     'command_log_id'),
        'sos':      ('SOS_Log',         'sos_id'),
        'weather':  ('Weather_Log',     'weather_log_id'),
        'news':     ('News_Log',        'news_log_id'),
        'stocks':   ('Stock_Log',       'stock_log_id')
    }

    if type_ not in mapping:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Invalid log type'}), 400

    table, pk = mapping[type_]

    # Safety try guard tracking runtime execution exceptions
    try:
        # Spawns fresh active database connection instance
        db = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor()
        
        # Build a query using IN (%s, %s, ...) for safety and performance
        placeholders = ', '.join(['%s'] * len(ids))
        query = f"DELETE FROM {table} WHERE {pk} IN ({placeholders})"
        
        # Executes custom SQL script parameter patterns securely
        cursor.execute(query, tuple(ids))
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        
        deleted_count = cursor.rowcount
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({
            'success': True, 
            'message': f'Successfully deleted {deleted_count} items from {type_}'
        })

    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# ADMIN — GET ADMIN PROFILE
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/profile', methods=['GET'])
@admin_required
# API controller routing routine executing client transactions
def admin_get_profile():
    admin_id = request.user.get('user_id')
    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute(
            "SELECT admin_id, name, email FROM Admin WHERE admin_id = %s",
            (admin_id,)
        )
        admin = cursor.fetchone()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        if admin:
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': True, 'admin': admin})
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Admin not found'}), 404
    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# ADMIN — CHANGE OWN PASSWORD
# ============================================================

# Registers HTTP route path rules binding specific controller logic below
@app.route('/api/admin/change-password', methods=['POST'])
@admin_required
# API controller routing routine executing client transactions
def admin_change_password():
    admin_id = request.user.get('user_id')
    data     = request.get_json()
    curr_pwd = data.get('currentPassword', '')
    new_pwd  = data.get('newPassword', '')

    if not curr_pwd or not new_pwd:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'Both fields are required'}), 400
    if len(new_pwd) < 6:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': 'New password must be at least 6 characters'}), 400

    # Safety try guard tracking runtime execution exceptions
    try:
        db     = get_db()
        # Spawns dynamic query cursor translating database rows to accessible structures
        cursor = db.cursor(dictionary=True)
        # Executes custom SQL script parameter patterns securely
        cursor.execute("SELECT password FROM Admin WHERE admin_id = %s", (admin_id,))
        admin = cursor.fetchone()
        if not admin or not bcrypt.checkpw(curr_pwd.encode(), admin['password'].encode()):
            # Releases query cursor and active database resources back to system pools
            cursor.close(); db.close()
            # Translates python dictionary records back to standard JSON returns format
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
        hashed = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
        # Executes custom SQL script parameter patterns securely
        cursor.execute("UPDATE Admin SET password = %s WHERE admin_id = %s", (hashed, admin_id))
        # Saves SQL updates and data insertion records securely to system storage
        db.commit()
        # Releases query cursor and active database resources back to system pools
        cursor.close(); db.close()
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': True, 'message': 'Password changed successfully!'})
    # Catches active database connection and query constraints execution issues
    except mysql.connector.Error as e:
        # Translates python dictionary records back to standard JSON returns format
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# RUN THE SERVER
# ============================================================

if __name__ == '__main__':
    # debug=True — auto-reloads on code changes and shows detailed errors
    # Remove debug=True in production
    app.run(debug=True, port=5000)
