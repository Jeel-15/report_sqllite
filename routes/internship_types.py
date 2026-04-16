from datetime import datetime
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from routes.admin import admin_required
from models.internship_type import InternshipType

internship_types_bp = Blueprint('internship_types', __name__)


def _serialize_type(doc):
    return {
        '_id': str(doc.id),
        'name': doc.name,
        'description': doc.description,
        'aiPromptContext': doc.aiPromptContext,
        'icon': doc.icon,
        'isActive': doc.isActive,
        'reportSections': [
            {
                'key': section.key,
                'title': section.title,
                'description': section.description,
            } for section in (doc.reportSections or [])
        ],
        'createdBy': {
            '_id': str(doc.createdBy.id),
            'name': doc.createdBy.name,
        } if doc.createdBy else None,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


@internship_types_bp.route('/', methods=['GET'])
@token_required
def get_active_types(current_user):
    docs = InternshipType.objects(isActive=True).order_by('name')
    return jsonify([_serialize_type(d) for d in docs])


@internship_types_bp.route('/all', methods=['GET'])
@admin_required
def get_all_types(current_user):
    docs = InternshipType.objects().order_by('-createdAt')
    return jsonify([_serialize_type(d) for d in docs])


@internship_types_bp.route('/<type_id>', methods=['GET'])
@token_required
def get_type(current_user, type_id):
    doc = InternshipType.objects(id=type_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404
    return jsonify(_serialize_type(doc))


@internship_types_bp.route('/', methods=['POST'])
@admin_required
def create_type(current_user):
    data = request.get_json() or {}
    required = ['name', 'description', 'aiPromptContext']
    for field in required:
        if not str(data.get(field, '')).strip():
            return jsonify({'message': f'{field} is required'}), 400

    doc = InternshipType(
        name=data['name'].strip(),
        description=data['description'].strip(),
        aiPromptContext=data['aiPromptContext'].strip(),
        icon=data.get('icon', '📄'),
        isActive=bool(data.get('isActive', True)),
        createdBy=current_user.id,
    )
    if isinstance(data.get('reportSections'), list):
        doc.reportSections = data['reportSections']

    doc.save()
    return jsonify(_serialize_type(doc)), 201


@internship_types_bp.route('/<type_id>', methods=['PUT'])
@admin_required
def update_type(current_user, type_id):
    doc = InternshipType.objects(id=type_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404

    data = request.get_json() or {}
    for field in ['name', 'description', 'aiPromptContext', 'icon', 'isActive', 'reportSections']:
        if field in data:
            setattr(doc, field, data[field])
    doc.updatedAt = datetime.utcnow()
    doc.save()
    return jsonify(_serialize_type(doc))


@internship_types_bp.route('/<type_id>', methods=['DELETE'])
@admin_required
def delete_type(current_user, type_id):
    InternshipType.objects(id=type_id).delete()
    return jsonify({'message': 'Deleted'})
