import os
from flask import Flask, jsonify, send_from_directory
from dotenv import load_dotenv
from mongoengine import connect

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'fallback_secret')
app.config['SQLITE_PATH'] = os.getenv(
    'SQLITE_PATH',
    os.path.join(app.root_path, 'data', 'app.db')
)
os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'report_images'), exist_ok=True)
os.makedirs(os.path.dirname(app.config['SQLITE_PATH']), exist_ok=True)

# Initialize local SQLite-backed data layer
connect(path=app.config['SQLITE_PATH'])

from routes.auth import auth_bp, limiter
limiter.init_app(app)
app.register_blueprint(auth_bp, url_prefix='/api/auth')

from routes.admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/api/admin')

from routes.student import student_bp
app.register_blueprint(student_bp, url_prefix='/api/student')

from routes.reports import reports_bp
app.register_blueprint(reports_bp, url_prefix='/api/reports')

from routes.upload import upload_bp
app.register_blueprint(upload_bp, url_prefix='/api/upload')

from routes.internship_types import internship_types_bp
app.register_blueprint(internship_types_bp, url_prefix='/api/internship-types')

from routes.pages import pages_bp
app.register_blueprint(pages_bp)


@app.get('/api/health')
def health():
    return jsonify({'status': 'OK'})


@app.get('/uploads/<path:filename>')
def uploads(filename):
    base_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    return send_from_directory(base_dir, filename)


if __name__ == '__main__':
    # Default port is 5000, configurable via PORT environment variable
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
