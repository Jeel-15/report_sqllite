from flask import Blueprint, render_template
from models.user import User
from models.report import Report

pages_bp = Blueprint('pages', __name__)

def get_sidebar_counts():
    """Get counts for sidebar badges"""
    try:
        student_count = User.objects(role='student').count()
        report_count = Report.objects().count()
        return {
            'student_count': student_count,
            'report_count': report_count
        }
    except:
        return {
            'student_count': 0,
            'report_count': 0
        }

@pages_bp.route('/')
def home():
    # Typically would redirect to /login or student dashboard
    return render_template('landing.html')

@pages_bp.route('/login')
def login():
    return render_template('login.html')


@pages_bp.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@pages_bp.route('/register')
def register():
    return render_template('register.html')

@pages_bp.route('/admin/dashboard')
def admin_dashboard():
    counts = get_sidebar_counts()
    return render_template('admin/dashboard.html', **counts)

@pages_bp.route('/admin/majors')
def admin_majors():
    counts = get_sidebar_counts()
    return render_template('admin/manage_majors.html', **counts)

@pages_bp.route('/admin/users')
def admin_users():
    counts = get_sidebar_counts()
    return render_template('admin/manage_users.html', **counts)

@pages_bp.route('/admin/degrees')
def admin_degrees():
    counts = get_sidebar_counts()
    return render_template('admin/manage_degrees.html', **counts)

@pages_bp.route('/admin/universities')
def admin_universities():
    counts = get_sidebar_counts()
    return render_template('admin/manage_universities.html', **counts)

@pages_bp.route('/admin/colleges')
def admin_colleges():
    counts = get_sidebar_counts()
    return render_template('admin/manage_colleges.html', **counts)

@pages_bp.route('/admin/industries')
def admin_industries():
    counts = get_sidebar_counts()
    return render_template('admin/manage_industries.html', **counts)

@pages_bp.route('/admin/services')
def admin_services():
    counts = get_sidebar_counts()
    return render_template('admin/manage_services.html', **counts)

@pages_bp.route('/admin/payments')
def admin_payments():
    counts = get_sidebar_counts()
    return render_template('admin/manage_payments.html', **counts)

@pages_bp.route('/admin/reports')
def admin_reports():
    counts = get_sidebar_counts()
    return render_template('admin/manage_reports.html', **counts)


@pages_bp.route('/admin/report/<report_id>')
def admin_report_view(report_id):
    counts = get_sidebar_counts()
    return render_template('admin/report_view.html', report_id=report_id, active_page='reports', **counts)

@pages_bp.route('/admin/types')
def admin_types():
    counts = get_sidebar_counts()
    return render_template('admin/manage_types.html', **counts)

@pages_bp.route('/admin/settings')
def admin_settings():
    counts = get_sidebar_counts()
    return render_template('admin/settings.html', **counts)


@pages_bp.route('/admin/notifications')
def admin_notifications():
    counts = get_sidebar_counts()
    return render_template('admin/notifications.html', active_page='notifications', **counts)

@pages_bp.route('/student/dashboard')
def student_dashboard():
    return render_template('student/dashboard.html')

@pages_bp.route('/student/profile')
def student_profile():
    return render_template('student/profile.html')

@pages_bp.route('/student/create')
def student_create():
    return render_template('student/create_report.html')

@pages_bp.route('/student/report/<report_id>')
def student_report_view(report_id):
    return render_template('student/report_view.html', admin_readonly=False)


@pages_bp.route('/logout')
def logout_page():
    return render_template('logout.html')
