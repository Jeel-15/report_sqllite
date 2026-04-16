import os
import io
import uuid
from PIL import Image
from flask import Blueprint, request, jsonify
from routes.auth import token_required

upload_bp = Blueprint('upload', __name__)

BASE_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')


@upload_bp.route('/logo/<upload_type>', methods=['POST'])
@token_required
def upload_logo(current_user, upload_type):
    if upload_type not in ['college', 'industry']:
        return jsonify({'message': 'Invalid type'}), 400

    file = request.files.get('logo')
    if not file:
        return jsonify({'message': 'No file uploaded'}), 400

    if not file.mimetype or not file.mimetype.startswith('image/'):
        return jsonify({'message': 'Only images allowed'}), 400

    folder = 'colleges' if upload_type == 'college' else 'industries'
    target_dir = os.path.join(BASE_UPLOAD_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(target_dir, filename)

    try:
        image = Image.open(io.BytesIO(file.read())).convert('RGBA')

        # Keep original aspect ratio and place into 300x300 canvas like old backend.
        image.thumbnail((300, 300))
        canvas = Image.new('RGBA', (300, 300), (255, 255, 255, 255))
        x = (300 - image.width) // 2
        y = (300 - image.height) // 2
        canvas.paste(image, (x, y), image)
        canvas.convert('RGB').save(filepath, format='PNG')

        rel_path = f"/uploads/{folder}/{filename}"
        return jsonify({'path': rel_path, 'filename': filename})
    except Exception as exc:
        return jsonify({'message': str(exc)}), 500
