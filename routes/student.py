import os
import re
import json
import html
import uuid
import datetime
import requests
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from routes.auth import token_required
from models.user import User
from models.degree import Degree
from models.major import Major
from models.report import Report
from models.industry import Industry
from models.service import Service
from routes.reports import (
    _is_images_enabled,
    _build_pdf_sections,
    _resolve_cover_logos,
    _resolve_layout_settings,
)
# We'll need to fetch colleges/universities too
from models.college import College
from models.university import University

student_bp = Blueprint('student', __name__)
REPORT_IMAGE_UPLOAD_FOLDER = os.path.join('static', 'uploads', 'report_images')


def _is_profile_complete(user):
    return bool(
        getattr(user, 'name', None) and
        getattr(user, 'college', None) and
        getattr(user, 'university', None) and
        getattr(user, 'degree', None) and
        getattr(user, 'major', None) and
        getattr(user, 'industry', None)
    )


def _to_object_if_json(value):
    if isinstance(value, str):
        raw = value.strip()
        if raw and (raw.startswith('{') or raw.startswith('[')):
            try:
                return json.loads(raw)
            except Exception:
                return value
    return value


def _normalize_section_text(value):
    text = '' if value is None else str(value)
    # Handle literal \n escape sequences (not real newlines) from JSON/webhook payloads
    text = text.replace('\\n', '\n')
    # Handle HTML-encoded br/p tags that bypass regex matching
    text = re.sub(r'&lt;br\s*/?&gt;', '\n', text)
    text = re.sub(r'&lt;/?p\s*&gt;', '\n\n', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    for _ in range(2):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded

    text = re.sub(r'(?i)<\s*br\s*/?\s*>', '\n', text)
    text = re.sub(r'(?i)<\s*/\s*p\s*>', '\n\n', text)
    text = re.sub(r'(?i)<\s*p\b[^>]*>', '', text)
    text = re.sub(r'(?i)<\s*/?\s*div\b[^>]*>', '\n', text)
    text = re.sub(r'(?i)<\s*/?\s*li\b[^>]*>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _sanitize_content_map(content):
    if not isinstance(content, dict):
        return {}
    out = {}
    for key, value in content.items():
        skey = str(key)
        if skey.startswith('__'):
            out[skey] = value
        else:
            out[skey] = _normalize_section_text(value)
    return out


def _sanitize_titles_map(titles):
    if not isinstance(titles, dict):
        return {}
    out = {}
    for key, value in titles.items():
        out[str(key)] = _normalize_section_text(value)
    return out


def _serialize_degree(degree):
    return {
        '_id': str(degree.id),
        'name': degree.name,
        'isActive': degree.isActive
    }


def _serialize_major(major):
    return {
        '_id': str(major.id),
        'name': major.name,
        'degree': str(major.degree.id) if major.degree else None,
        'reportLanguage': major.reportLanguage,
        'reportContentType': major.reportContentType,
        'reportPolicy': major.reportPolicy.to_mongo().to_dict() if major.reportPolicy else {},
        'isActive': major.isActive
    }


def _serialize_university(university):
    return {
        '_id': str(university.id),
        'name': university.name,
        'villageCityName': university.villageCityName,
        'state': university.state,
        'isActive': university.isActive
    }


def _serialize_college(college):
    return {
        '_id': str(college.id),
        'name': college.name,
        'university': str(college.university.id) if college.university else None,
        'villageCityName': college.villageCityName,
        'state': college.state,
        'logo': college.logo,
        'website': college.website,
        'isActive': college.isActive
    }


def _serialize_industry(industry):
    return {
        '_id': str(industry.id),
        'name': industry.name,
        'villageCityName': industry.villageCityName,
        'state': industry.state,
        'logo': industry.logo,
        'website': industry.website,
        'isActive': industry.isActive
    }


def _serialize_profile(user):
    return {
        '_id': str(user.id),
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'profileCompleted': user.profileCompleted,
        'villageCityName': user.villageCityName,
        'tehsil': user.tehsil,
        'district': user.district,
        'state': user.state,
        'phone': user.phone,
        'whatsapp': user.whatsapp,
        'rollNumber': user.rollNumber,
        'enrollmentNumber': user.enrollmentNumber,
        'supervisorName': user.supervisorName,
        'supervisorContact': user.supervisorContact,
        'university': _serialize_university(user.university) if user.university else None,
        'college': _serialize_college(user.college) if user.college else None,
        'degree': _serialize_degree(user.degree) if user.degree else None,
        'major': _serialize_major(user.major) if user.major else None,
        'industry': _serialize_industry(user.industry) if user.industry else None,
    }


def _serialize_service(service):
    return {
        '_id': str(service.id),
        'name': service.name,
        'type': service.type,
        'price': service.price,
        'gstIncluded': service.gstIncluded,
        'gstPercent': service.gstPercent,
        'freeLimit': service.freeLimit,
        'description': service.description,
        'isActive': service.isActive,
        'degreePricing': [
            {
                'degree': {
                    '_id': str(item.degree.id),
                    'name': item.degree.name,
                } if item.degree else None,
                'price': item.price,
            } for item in (service.degreePricing or [])
        ],
    }


@student_bp.route('/degrees', methods=['GET'])
@token_required
def get_degrees(current_user):
    degrees = Degree.objects(isActive=True).order_by('name')
    return jsonify([_serialize_degree(degree) for degree in degrees])


@student_bp.route('/majors', methods=['GET'])
@token_required
def get_all_active_majors(current_user):
    majors = Major.objects(isActive=True).order_by('name')
    return jsonify([_serialize_major(major) for major in majors])


@student_bp.route('/majors/<degree_id>', methods=['GET'])
@token_required
def get_majors_by_degree(current_user, degree_id):
    majors = Major.objects(degree=degree_id, isActive=True).order_by('name')
    return jsonify([_serialize_major(major) for major in majors])


@student_bp.route('/major/<major_id>', methods=['GET'])
@token_required
def get_major(current_user, major_id):
    major = Major.objects(id=major_id).first()
    if not major:
        return jsonify({'message': 'Major not found'}), 404
    return jsonify(_serialize_major(major))


@student_bp.route('/universities', methods=['GET'])
@token_required
def get_universities(current_user):
    query = str(request.args.get('q', '')).strip()
    uni_filter = {'isActive': True}
    if query:
        uni_filter['name__icontains'] = query

    universities = University.objects(**uni_filter).order_by('name')[:50]
    return jsonify([_serialize_university(university) for university in universities])


@student_bp.route('/universities', methods=['POST'])
@token_required
def create_university(current_user):
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'message': 'University name is required'}), 400

    existing = University.objects(name__iexact=name).first()
    if existing:
        return jsonify(_serialize_university(existing)), 200

    university = University(name=name, createdBy=current_user.id)
    university.save()
    return jsonify(_serialize_university(university)), 201


@student_bp.route('/colleges', methods=['GET'])
@token_required
def get_colleges(current_user):
    query = str(request.args.get('q', '')).strip()
    university_id = str(request.args.get('university', '')).strip()

    college_filter = {'isActive': True}
    if query:
        college_filter['name__icontains'] = query
    if university_id:
        college_filter['university'] = university_id

    colleges = College.objects(**college_filter).order_by('name')[:50]
    return jsonify([_serialize_college(college) for college in colleges])


@student_bp.route('/colleges', methods=['POST'])
@token_required
def create_college(current_user):
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    university_id = str(data.get('university', '')).strip()

    if not name or not university_id:
        return jsonify({'message': 'College name and university are required'}), 400

    existing = College.objects(name__iexact=name, university=university_id).first()
    if existing:
        return jsonify(_serialize_college(existing)), 200

    college = College(
        name=name,
        university=university_id,
        createdBy=current_user.id,
        villageCityName=str(data.get('villageCityName', '')).strip(),
        tehsil=str(data.get('tehsil', '')).strip(),
        district=str(data.get('district', '')).strip(),
        state=str(data.get('state', '')).strip(),
        website=str(data.get('website', '')).strip(),
        logo=str(data.get('logo', '')).strip(),
    )
    college.save()
    return jsonify(_serialize_college(college)), 201


@student_bp.route('/industries', methods=['GET'])
@token_required
def get_industries(current_user):
    query = str(request.args.get('q', '')).strip()
    ind_filter = {'isActive': True}
    if query:
        ind_filter['name__icontains'] = query

    industries = Industry.objects(**ind_filter).order_by('name')[:50]
    return jsonify([_serialize_industry(industry) for industry in industries])


@student_bp.route('/industries', methods=['POST'])
@token_required
def create_industry(current_user):
    data = request.get_json() or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'message': 'Industry name is required'}), 400

    existing = Industry.objects(name__iexact=name).first()
    if existing:
        return jsonify(_serialize_industry(existing)), 200

    industry = Industry(
        name=name,
        createdBy=current_user.id,
        villageCityName=str(data.get('villageCityName', '')).strip(),
        tehsil=str(data.get('tehsil', '')).strip(),
        district=str(data.get('district', '')).strip(),
        state=str(data.get('state', '')).strip(),
        website=str(data.get('website', '')).strip(),
        logo=str(data.get('logo', '')).strip(),
    )
    industry.save()
    return jsonify(_serialize_industry(industry)), 201


@student_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify(_serialize_profile(current_user))


@student_bp.route('/services', methods=['GET'])
@token_required
def get_services(current_user):
    services = Service.objects(isActive=True).order_by('name')
    return jsonify([_serialize_service(service) for service in services])


@student_bp.route('/profile/personal', methods=['PUT'])
@token_required
def update_personal_profile(current_user):
    data = request.get_json() or {}
    allowed_fields = ['name', 'villageCityName', 'tehsil', 'district', 'state', 'phone', 'whatsapp']

    for field in allowed_fields:
        if field in data:
            setattr(current_user, field, data[field])

    current_user.profileCompleted = _is_profile_complete(current_user)
    current_user.updatedAt = datetime.datetime.utcnow()
    current_user.save()
    return jsonify(_serialize_profile(current_user))


@student_bp.route('/profile/college', methods=['PUT'])
@token_required
def update_college_profile(current_user):
    data = request.get_json() or {}
    ref_map = {
        'university': University,
        'college': College,
        'degree': Degree,
        'major': Major,
    }

    for field in ['university', 'college', 'degree', 'major']:
        if field not in data:
            # Field not sent at all — leave the existing value unchanged
            continue

        value = str(data.get(field) or '').strip()

        if value == '':
            # Field explicitly sent as empty or null — clear the reference
            setattr(current_user, field, None)
            continue

        doc = ref_map[field].objects(id=value).first()
        if not doc:
            return jsonify({'message': f'Invalid {field}'}), 400
        setattr(current_user, field, doc)

    for field in ['rollNumber', 'enrollmentNumber']:
        if field in data:
            setattr(current_user, field, str(data.get(field) or '').strip())

    current_user.profileCompleted = _is_profile_complete(current_user)
    current_user.updatedAt = datetime.datetime.utcnow()
    current_user.save()
    return jsonify(_serialize_profile(current_user))


@student_bp.route('/profile/industry', methods=['PUT'])
@token_required
def update_industry_profile(current_user):
    data = request.get_json() or {}

    if 'industry' in data:
        industry_value = str(data.get('industry') or '').strip()
        if industry_value == '':
            # Explicitly sent as empty or null — clear the industry reference
            current_user.industry = None
        else:
            industry_doc = Industry.objects(id=industry_value).first()
            if not industry_doc:
                return jsonify({'message': 'Invalid industry'}), 400
            current_user.industry = industry_doc

    if 'supervisorName' in data:
        current_user.supervisorName = str(data.get('supervisorName') or '').strip()
    if 'supervisorContact' in data:
        current_user.supervisorContact = str(data.get('supervisorContact') or '').strip()

    current_user.profileCompleted = _is_profile_complete(current_user)
    current_user.updatedAt = datetime.datetime.utcnow()
    current_user.save()
    return jsonify(_serialize_profile(current_user))

@student_bp.route('/reports', methods=['GET'])
@token_required
def get_my_reports(current_user):
    # Fetch reports for the logged in user
    reports = Report.objects(user=current_user.id).order_by('-createdAt')
    result = []
    for r in reports:
        result.append({
            '_id': str(r.id),
            'projectTitle': r.projectTitle,
            'status': r.status,
            'academicYear': r.academicYear,
            'createdAt': r.createdAt.isoformat()
        })
    return jsonify(result)
@student_bp.route('/reports/<report_id>', methods=['GET'])
@token_required
def get_report(current_user, report_id):
    try:
        r = Report.objects(id=report_id, user=current_user.id).first()
        if not r:
            return jsonify({'message': 'Not found'}), 404
            
        return jsonify({
            '_id': str(r.id),
            'projectTitle': r.projectTitle,
            'status': r.status,
            'generatedContent': _sanitize_content_map(r.generatedContent or {}),
            'editedContent': _sanitize_content_map(r.editedContent or {}),
            'generatedTitles': _sanitize_titles_map(r.generatedTitles or {}),
            'sectionImages': r.sectionImages or {},
            'imagesEnabled': _is_images_enabled(r),
            'createdAt': r.createdAt.isoformat()
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@student_bp.route('/reports/<report_id>/content', methods=['PUT'])
@token_required
def update_report_content(current_user, report_id):
    data = request.get_json()
    if not data or 'editedContent' not in data:
        return jsonify({'message': 'No content provided'}), 400
        
    try:
        r = Report.objects(id=report_id, user=current_user.id).first()
        if not r:
            return jsonify({'message': 'Not found'}), 404
            
        r.editedContent = _sanitize_content_map(data['editedContent'])
        r.status = 'edited'
        r.save()
        return jsonify({'message': 'Saved successfully'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

from flask import render_template, send_file
import io
from utils.pdf import generate_pdf_from_html

@student_bp.route('/reports/<report_id>/pdf-preview', methods=['POST'])
@token_required
def generate_pdf_preview(current_user, report_id):
    from routes.reports import (
        _build_pdf_sections,
        _resolve_cover_logos,
        _resolve_layout_settings,
    )

    data = request.get_json() or {}
    edited_content = data.get('editedContent') if isinstance(data.get('editedContent'), dict) else None

    r = Report.objects(id=report_id, user=current_user.id).first()
    if not r:
        return jsonify({'message': 'Not found'}), 404

    content = edited_content or r.editedContent or r.generatedContent or {}
    sections = _build_pdf_sections(r, content, request)
    cover_logos = _resolve_cover_logos(content, r, request)
    layout_settings = _resolve_layout_settings(content, r)

    college = College.objects(id=r.college.id).first() if r.college else None
    university = University.objects(id=r.university.id).first() if r.university else None
    industry = Industry.objects(id=r.industry.id).first() if r.industry else None

    html_string = render_template(
        'pdf_template.html',
        report=r,
        college=college,
        university=university,
        industry=industry,
        cover_logos=cover_logos,
        layout_settings=layout_settings,
        sections=sections,
    )
    
    base_url = str(request.host_url).rstrip('/')
    html_string = html_string.replace(
        '<head>',
        f'<head><base href="{base_url}/">',
        1,
    )

    pdf_bytes = generate_pdf_from_html(
        html_string,
        base_url=base_url,
        student_name=r.user.name if r.user else 'Student',
    )

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f"{r.projectTitle or 'preview'}.pdf"
    )

@student_bp.route('/reports/<report_id>/images/<section_key>', methods=['POST'])
@token_required
def student_upload_section_image(current_user, report_id, section_key):
    r = Report.objects(id=report_id, user=current_user.id).first()
    if not r:
        return jsonify({'message': 'Not found'}), 404

    file = request.files.get('image')
    if not file or not file.filename:
        return jsonify({'message': 'No file provided'}), 400

    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return jsonify({'message': 'Invalid file type. Allowed: jpg, jpeg, png, gif, webp'}), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > 5 * 1024 * 1024:
        return jsonify({'message': 'File too large. Maximum size is 5MB.'}), 400

    folder = os.path.join(REPORT_IMAGE_UPLOAD_FOLDER, str(report_id), section_key)
    os.makedirs(folder, exist_ok=True)

    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(folder, filename)
    file.save(filepath)

    url = f"/static/uploads/report_images/{report_id}/{section_key}/{filename}"
    image_entry = {
        'url': url,
        'filename': filename,
        'position': 'bottom',
        'caption': '',
        'widthPercent': 100,
    }

    images = dict(r.sectionImages or {})
    section_list = list(images.get(section_key, []))
    section_list.append(image_entry)
    images[section_key] = section_list
    r.sectionImages = images
    r.save()
    return jsonify({'image': image_entry}), 201


@student_bp.route('/reports/<report_id>/images/<section_key>/<filename>', methods=['PUT'])
@token_required
def student_update_section_image(current_user, report_id, section_key, filename):
    r = Report.objects(id=report_id, user=current_user.id).first()
    if not r:
        return jsonify({'message': 'Not found'}), 404

    data = request.get_json() or {}
    images = dict(r.sectionImages or {})
    section_list = list(images.get(section_key, []))

    updated = False
    for img in section_list:
        if isinstance(img, dict) and img.get('filename') == filename:
            if 'position' in data:
                img['position'] = str(data['position'])
            if 'caption' in data:
                img['caption'] = str(data['caption'])
            if 'widthPercent' in data:
                try:
                    img['widthPercent'] = max(10, min(100, int(data['widthPercent'])))
                except (ValueError, TypeError):
                    pass
            updated = True
            break

    if not updated:
        return jsonify({'message': 'Image not found'}), 404

    images[section_key] = section_list
    r.sectionImages = images
    r.save()
    return jsonify({'message': 'Updated'})


@student_bp.route('/reports/<report_id>/images/<section_key>/<filename>', methods=['DELETE'])
@token_required
def student_delete_section_image(current_user, report_id, section_key, filename):
    r = Report.objects(id=report_id, user=current_user.id).first()
    if not r:
        return jsonify({'message': 'Not found'}), 404

    images = dict(r.sectionImages or {})
    before = list(images.get(section_key, []))
    after = [i for i in before if not (isinstance(i, dict) and i.get('filename') == filename)]

    if len(before) == len(after):
        return jsonify({'message': 'Image not found'}), 404

    images[section_key] = after
    r.sectionImages = images
    r.save()

    filepath = os.path.join(REPORT_IMAGE_UPLOAD_FOLDER, str(report_id), section_key, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass

    return jsonify({'message': 'Deleted'})
