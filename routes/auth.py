import os
import jwt
import datetime
import re
import secrets
import bcrypt
import smtplib
import ssl
from email.message import EmailMessage
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models.user import User

auth_bp = Blueprint('auth', __name__)
limiter = Limiter(key_func=get_remote_address)


def _validate_password(password):
    if len(password) < 8:
        return 'Password must be at least 8 characters'
    if not re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter'
    if not re.search(r'[0-9]', password):
        return 'Password must contain at least one number'
    return None


def _validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _generate_otp(length=6):
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def _clear_reset_otp_state(user):
    user.resetOtpHash = None
    user.resetOtpExpiresAt = None
    user.resetOtpAttemptCount = 0


def _env_bool(name, default=False):
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in ('1', 'true', 'yes', 'on')


def _send_reset_otp_email(recipient_email, otp, recipient_name='User'):
    smtp_host = os.getenv('SMTP_HOST', '').strip()
    smtp_port = int(str(os.getenv('SMTP_PORT', '587')).strip() or '587')
    smtp_user = os.getenv('SMTP_USER', '').strip()
    smtp_pass = os.getenv('SMTP_PASS', '').strip()
    sender_email = os.getenv('SMTP_FROM_EMAIL', smtp_user).strip()
    sender_name = os.getenv('SMTP_FROM_NAME', 'ReportGen Support').strip() or 'ReportGen Support'
    use_ssl = _env_bool('SMTP_USE_SSL', False)

    if not smtp_host or not sender_email:
        raise RuntimeError('SMTP is not configured. Missing SMTP_HOST or SMTP_FROM_EMAIL.')

    msg = EmailMessage()
    msg['Subject'] = 'ReportGen Password Reset OTP'
    msg['From'] = f'{sender_name} <{sender_email}>'
    msg['To'] = recipient_email
    msg.set_content(
        f"""
Hi {recipient_name or 'User'},

Your ReportGen password reset OTP is: {otp}

This OTP is valid for 10 minutes.
If you did not request a password reset, please ignore this email.

Thanks,
ReportGen Team
""".strip()
    )

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl.create_default_context(), timeout=20) as server:
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)

def generate_token(user_id, role):
    payload = {
        'userId': str(user_id),
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow()
    }
    secret = os.getenv('JWT_SECRET')
    if not secret:
        raise RuntimeError('JWT_SECRET environment variable is not set')
    return jwt.encode(payload, secret, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            token = request.args.get('token') or request.args.get('access_token')
                
        if not token:
            return jsonify({'message': 'Authorization token is missing!'}), 401

        secret = os.getenv('JWT_SECRET')
        if not secret:
            raise RuntimeError('JWT_SECRET environment variable is not set')
            
        try:
            data = jwt.decode(token, secret, algorithms=['HS256'])
            current_user = User.objects(id=data['userId']).first()
            if not current_user:
                return jsonify({'message': 'User no longer exists'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Please provide email and password'}), 400

    email = data.get('email').strip().lower()
    if not _validate_email(email):
        return jsonify({'message': 'Invalid email format'}), 400
        
    users = list(User.objects(email=email).order_by('-updatedAt'))
    if not users:
        return jsonify({'message': 'Invalid credentials'}), 401

    password = data.get('password')
    user = None
    disabled_match = False
    for candidate in users:
        try:
            if candidate.check_password(password):
                if candidate.isActive:
                    user = candidate
                    break
                disabled_match = True
        except Exception:
            # Skip malformed legacy password records.
            continue

    if user is None:
        if disabled_match:
            return jsonify({'message': 'Account is disabled. Contact admin.'}), 401
        return jsonify({'message': 'Invalid credentials'}), 401
        
    token = generate_token(user.id, user.role)
    
    # Exclude password from the returned user object
    user_dict = {
        '_id': str(user.id),
        'email': user.email,
        'name': user.name,
        'role': user.role,
        'profileCompleted': user.profileCompleted,
        'isActive': user.isActive,
    }
    
    return jsonify({
        'token': token,
        'user': user_dict
    }), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body is required'}), 400

    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))

    if not name or not email or not password:
        return jsonify({'message': 'Name, email and password are required'}), 400

    if not _validate_email(email):
        return jsonify({'message': 'Invalid email format'}), 400

    password_error = _validate_password(password)
    if password_error:
        return jsonify({'message': password_error}), 400

    if User.objects(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400

    user = User(
        name=name,
        email=email,
        role='student',
        profileCompleted=False
    )
    user.set_password(password)
    user.save()

    token = generate_token(user.id, user.role)
    return jsonify({
        'token': token,
        'user': {
            '_id': str(user.id),
            'email': user.email,
            'name': user.name,
            'role': user.role,
            'profileCompleted': user.profileCompleted,
            'isActive': user.isActive,
        }
    }), 201


@auth_bp.route('/logout', methods=['POST'])
def logout():
    # Tokens are stored in localStorage on the client, not in cookies.
    # The client is responsible for clearing localStorage on logout.
    # This endpoint exists so the frontend has a consistent logout API call to make.
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/forgot-password/request-otp', methods=['POST'])
@limiter.limit("5 per 15 minutes")
def forgot_password_request_otp():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()

    if not email or not _validate_email(email):
        return jsonify({'message': 'Please provide a valid email address'}), 400

    # Prevent user enumeration by returning the same success message.
    generic_message = 'If the email is registered, an OTP has been sent.'
    user = User.objects(email=email).first()
    if not user or not user.isActive:
        return jsonify({'message': generic_message}), 200

    otp = _generate_otp(6)
    otp_hash = bcrypt.hashpw(otp.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

    user.resetOtpHash = otp_hash
    user.resetOtpExpiresAt = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    user.resetOtpAttemptCount = 0
    user.updatedAt = datetime.datetime.utcnow()
    user.save()

    debug_otp_enabled = _env_bool('FORGOT_PASSWORD_OTP_DEBUG', False)

    if debug_otp_enabled:
        return jsonify({'message': generic_message, 'otp': otp}), 200

    try:
        _send_reset_otp_email(user.email, otp, user.name)
    except Exception as exc:
        current_app.logger.exception('Failed to send forgot-password OTP email: %s', exc)
        _clear_reset_otp_state(user)
        user.updatedAt = datetime.datetime.utcnow()
        user.save()
        return jsonify({'message': 'Unable to send OTP email right now. Please try again later.'}), 503

    return jsonify({'message': generic_message}), 200


@auth_bp.route('/forgot-password/verify-otp', methods=['POST'])
@limiter.limit("10 per 15 minutes")
def forgot_password_verify_otp():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    otp = str(data.get('otp', '')).strip()
    new_password = str(data.get('newPassword', ''))

    if not email or not _validate_email(email):
        return jsonify({'message': 'Please provide a valid email address'}), 400
    if not re.fullmatch(r'\d{6}', otp):
        return jsonify({'message': 'OTP must be a 6-digit number'}), 400

    password_error = _validate_password(new_password)
    if password_error:
        return jsonify({'message': password_error}), 400

    user = User.objects(email=email).first()
    if not user or not user.isActive:
        return jsonify({'message': 'Invalid or expired OTP'}), 400

    otp_hash = getattr(user, 'resetOtpHash', None)
    otp_exp = getattr(user, 'resetOtpExpiresAt', None)
    attempts = int(getattr(user, 'resetOtpAttemptCount', 0) or 0)

    if not otp_hash or not otp_exp:
        return jsonify({'message': 'Please request OTP first'}), 400

    now = datetime.datetime.utcnow()
    if now > otp_exp:
        _clear_reset_otp_state(user)
        user.updatedAt = now
        user.save()
        return jsonify({'message': 'OTP expired. Please request a new OTP'}), 400

    if attempts >= 5:
        _clear_reset_otp_state(user)
        user.updatedAt = now
        user.save()
        return jsonify({'message': 'Too many invalid attempts. Please request a new OTP'}), 429

    if not bcrypt.checkpw(otp.encode('utf-8'), otp_hash.encode('utf-8')):
        user.resetOtpAttemptCount = attempts + 1
        user.updatedAt = now
        user.save()
        return jsonify({'message': 'Invalid or expired OTP'}), 400

    if user.check_password(new_password):
        return jsonify({'message': 'New password must be different from current password'}), 400

    user.set_password(new_password)
    _clear_reset_otp_state(user)
    user.updatedAt = now
    user.save()

    return jsonify({'message': 'Password reset successful. Please login with your new password.'}), 200

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user):
    user_dict = {
        '_id': str(current_user.id),
        'email': current_user.email,
        'name': current_user.name,
        'role': current_user.role,
        'profileCompleted': current_user.profileCompleted,
        'isActive': current_user.isActive,
        'villageCityName': current_user.villageCityName,
        'tehsil': current_user.tehsil,
        'district': current_user.district,
        'state': current_user.state,
        'phone': current_user.phone,
        'whatsapp': current_user.whatsapp,
        'rollNumber': current_user.rollNumber,
        'enrollmentNumber': current_user.enrollmentNumber,
        'supervisorName': current_user.supervisorName,
        'supervisorContact': current_user.supervisorContact,
        'degree': {
            '_id': str(current_user.degree.id),
            'name': current_user.degree.name,
        } if current_user.degree else None,
        'major': {
            '_id': str(current_user.major.id),
            'name': current_user.major.name,
            'reportLanguage': current_user.major.reportLanguage,
        } if current_user.major else None,
        'college': {
            '_id': str(current_user.college.id),
            'name': current_user.college.name,
            'logo': current_user.college.logo,
        } if current_user.college else None,
        'university': {
            '_id': str(current_user.university.id),
            'name': current_user.university.name,
        } if current_user.university else None,
        'industry': {
            '_id': str(current_user.industry.id),
            'name': current_user.industry.name,
            'logo': current_user.industry.logo,
        } if current_user.industry else None,
    }
    return jsonify(user_dict), 200
