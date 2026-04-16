from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps
from routes.auth import token_required
from models.user import User
from models.report import Report
from models.degree import Degree
from models.major import Major, ReportPolicy, ReportSection
from models.university import University
from models.college import College
from models.industry import Industry
from models.payment import Payment
from models.service import Service
from models.internship_type import InternshipType

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({'message': 'Admin privilege required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated


def _obj_id(doc):
    return str(doc.id) if doc else None


def _safe_ref(doc):
    if not doc:
        return None
    try:
        return {'_id': _obj_id(doc), 'name': getattr(doc, 'name', None)}
    except Exception:
        return None


def _serialize_degree(doc):
    return {
        '_id': _obj_id(doc),
        'name': doc.name,
        'isActive': doc.isActive,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


def _serialize_major(doc):
    return {
        '_id': _obj_id(doc),
        'name': doc.name,
        'degree': {
            '_id': _obj_id(doc.degree),
            'name': doc.degree.name,
        } if doc.degree else None,
        'reportLanguage': doc.reportLanguage,
        'reportContentType': doc.reportContentType,
        'aiPromptContext': doc.aiPromptContext,
        'reportPolicy': doc.reportPolicy.to_mongo().to_dict() if doc.reportPolicy else {},
        'reportSections': [
            {
                'key': s.key,
                'title': s.title,
                'description': s.description,
            } for s in (doc.reportSections or [])
        ],
        'isActive': doc.isActive,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


def _normalize_major_payload(data):
    normalized = {}

    if 'name' in data:
        normalized['name'] = str(data.get('name') or '').strip()

    if 'degree' in data:
        raw_degree = data.get('degree')
        degree_id = None
        if isinstance(raw_degree, dict):
            degree_id = raw_degree.get('_id') or raw_degree.get('id')
        else:
            degree_id = raw_degree

        degree_id = str(degree_id or '').strip()
        if not degree_id:
            raise ValueError('Degree is required')

        degree_doc = Degree.objects(id=degree_id).first()
        if not degree_doc:
            raise ValueError('Invalid degree')
        normalized['degree'] = degree_doc

    if 'reportLanguage' in data:
        normalized['reportLanguage'] = str(data.get('reportLanguage') or 'English').strip() or 'English'

    if 'reportContentType' in data:
        normalized['reportContentType'] = str(data.get('reportContentType') or 'Text').strip() or 'Text'

    if 'aiPromptContext' in data:
        normalized['aiPromptContext'] = str(data.get('aiPromptContext') or '')

    if 'isActive' in data:
        normalized['isActive'] = bool(data.get('isActive'))

    if 'reportPolicy' in data:
        raw_policy = data.get('reportPolicy')
        if raw_policy is None:
            normalized['reportPolicy'] = ReportPolicy()
        elif isinstance(raw_policy, dict):
            # Remove fields that are no longer needed
            filtered_policy = {k: v for k, v in raw_policy.items() if k not in ['allowedScriptsRegex', 'fallbackMessage']}
            normalized['reportPolicy'] = ReportPolicy(**filtered_policy)
        else:
            raise ValueError('reportPolicy must be an object')

    if 'reportSections' in data:
        raw_sections = data.get('reportSections')
        if raw_sections is None:
            normalized['reportSections'] = []
        elif not isinstance(raw_sections, list):
            raise ValueError('reportSections must be an array')
        else:
            sections = []
            for idx, raw in enumerate(raw_sections):
                if not isinstance(raw, dict):
                    raise ValueError(f'reportSections[{idx}] must be an object')

                key = str(raw.get('key') or '').strip()
                title = str(raw.get('title') or '').strip()
                description = str(raw.get('description') or '')

                if not key or not title:
                    raise ValueError(f'reportSections[{idx}] requires key and title')

                sections.append(ReportSection(key=key, title=title, description=description))
            normalized['reportSections'] = sections

    return normalized


def _serialize_university(doc):
    return {
        '_id': _obj_id(doc),
        'name': doc.name,
        'villageCityName': doc.villageCityName,
        'tehsil': doc.tehsil,
        'district': doc.district,
        'state': doc.state,
        'website': doc.website,
        'createdBy': {
            '_id': _obj_id(doc.createdBy),
            'name': doc.createdBy.name,
        } if getattr(doc, 'createdBy', None) else None,
        'isActive': doc.isActive,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


def _serialize_college(doc):
    return {
        '_id': _obj_id(doc),
        'name': doc.name,
        'university': {
            '_id': _obj_id(doc.university),
            'name': doc.university.name,
        } if doc.university else None,
        'villageCityName': doc.villageCityName,
        'tehsil': doc.tehsil,
        'district': doc.district,
        'state': doc.state,
        'logo': doc.logo,
        'website': doc.website,
        'createdBy': {
            '_id': _obj_id(doc.createdBy),
            'name': doc.createdBy.name,
        } if getattr(doc, 'createdBy', None) else None,
        'isActive': doc.isActive,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


def _serialize_industry(doc):
    return {
        '_id': _obj_id(doc),
        'name': doc.name,
        'villageCityName': doc.villageCityName,
        'tehsil': doc.tehsil,
        'district': doc.district,
        'state': doc.state,
        'logo': doc.logo,
        'website': doc.website,
        'createdBy': {
            '_id': _obj_id(doc.createdBy),
            'name': doc.createdBy.name,
        } if getattr(doc, 'createdBy', None) else None,
        'isActive': doc.isActive,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


def _serialize_user(doc):
    return {
        '_id': _obj_id(doc),
        'name': doc.name,
        'email': doc.email,
        'role': doc.role,
        'isActive': doc.isActive,
        'villageCityName': doc.villageCityName,
        'state': doc.state,
        'phone': doc.phone,
        'tehsil': doc.tehsil,
        'district': doc.district,
        'supervisorName': doc.supervisorName,
        'supervisorContact': doc.supervisorContact,
        'profileCompleted': doc.profileCompleted,
        'college': _safe_ref(doc.college),
        'university': _safe_ref(doc.university),
        'industry': _safe_ref(doc.industry),
        'degree': _safe_ref(doc.degree),
        'major': _safe_ref(doc.major),
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


def _serialize_service(doc):
    return {
        '_id': _obj_id(doc),
        'name': doc.name,
        'type': doc.type,
        'price': doc.price,
        'gstIncluded': doc.gstIncluded,
        'gstPercent': doc.gstPercent,
        'freeLimit': doc.freeLimit,
        'degreePricing': [
            {
                'degree': {
                    '_id': _obj_id(item.degree),
                    'name': item.degree.name,
                } if item.degree else None,
                'price': item.price,
            } for item in (doc.degreePricing or [])
        ],
        'description': doc.description,
        'isActive': doc.isActive,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


def _serialize_payment(doc):
    service_val = doc.service
    if hasattr(service_val, 'id'):
        service_data = {
            '_id': str(service_val.id),
            'name': getattr(service_val, 'name', ''),
            'type': getattr(service_val, 'type', ''),
        }
    else:
        service_data = service_val

    return {
        '_id': _obj_id(doc),
        'user': {
            '_id': _obj_id(doc.user),
            'name': getattr(doc.user, 'name', None),
            'email': getattr(doc.user, 'email', None),
            'villageCityName': getattr(doc.user, 'villageCityName', None),
            'state': getattr(doc.user, 'state', None),
            'college': _safe_ref(getattr(doc.user, 'college', None)),
        } if doc.user else None,
        'service': service_data,
        'amount': doc.amount,
        'gstAmount': doc.gstAmount,
        'totalAmount': doc.totalAmount,
        'status': doc.status,
        'paymentMethod': doc.paymentMethod,
        'transactionId': doc.transactionId,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
    }


def _serialize_report(doc):
    university_ref = _safe_ref(doc.university)
    if not university_ref and getattr(doc, 'user', None):
        # Backward compatibility: some old reports may not store university on report.
        university_ref = _safe_ref(getattr(doc.user, 'university', None))

    return {
        '_id': _obj_id(doc),
        'projectTitle': doc.projectTitle,
        'status': doc.status,
        'createdAt': doc.createdAt.isoformat() if doc.createdAt else None,
        'user': {
            '_id': _obj_id(doc.user),
            'name': getattr(doc.user, 'name', None),
            'email': getattr(doc.user, 'email', None),
        } if doc.user else None,
        'degree': _safe_ref(doc.degree),
        'major': _safe_ref(doc.major),
        'college': _safe_ref(doc.college),
        'university': university_ref,
        'industry': _safe_ref(doc.industry),
    }


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_stats(current_user):
    total_users = User.objects(role='student').count()
    total_reports = Report.objects.count()
    total_degrees = Degree.objects.count()
    total_majors = Major.objects.count()
    total_universities = University.objects.count()
    total_colleges = College.objects.count()
    total_industries = Industry.objects.count()
    generated = Report.objects(status__in=['generated', 'edited', 'final']).count()
    pending = Report.objects(status__in=['pending', 'generating']).count()
    total_payments = Payment.objects(status='completed').count()
    total_types = InternshipType.objects(isActive=True).count()
    total_revenue = sum([(p.totalAmount or 0) for p in Payment.objects(status='completed')])

    return jsonify({
        'totalUsers': total_users,
        'totalReports': total_reports,
        'totalDegrees': total_degrees,
        'totalMajors': total_majors,
        'totalUniversities': total_universities,
        'totalColleges': total_colleges,
        'totalIndustries': total_industries,
        'generated': generated,
        'pending': pending,
        'totalPayments': total_payments,
        'totalTypes': total_types,
        'totalRevenue': total_revenue,
    })


@admin_bp.route('/degrees', methods=['GET'])
@admin_required
def get_degrees(current_user):
    q = str(request.args.get('q', '')).strip()
    filters = {'name__icontains': q} if q else {}
    docs = Degree.objects(**filters).order_by('name')
    return jsonify([_serialize_degree(d) for d in docs])


@admin_bp.route('/degrees', methods=['POST'])
@admin_required
def create_degree(current_user):
    data = request.get_json() or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'message': 'Name is required'}), 400

    doc = Degree(name=name, isActive=data.get('isActive', True))
    doc.save()
    return jsonify(_serialize_degree(doc)), 201


@admin_bp.route('/degrees/<degree_id>', methods=['PUT'])
@admin_required
def update_degree(current_user, degree_id):
    doc = Degree.objects(id=degree_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404

    data = request.get_json() or {}
    for field in ['name', 'isActive']:
        if field in data:
            setattr(doc, field, data[field])
    doc.updatedAt = datetime.utcnow()
    doc.save()
    return jsonify(_serialize_degree(doc))


@admin_bp.route('/degrees/<degree_id>', methods=['DELETE'])
@admin_required
def delete_degree(current_user, degree_id):
    Major.objects(degree=degree_id).delete()
    Degree.objects(id=degree_id).delete()
    return jsonify({'message': 'Deleted with all majors'})


@admin_bp.route('/majors', methods=['GET'])
@admin_required
def get_majors(current_user):
    q = str(request.args.get('q', '')).strip()
    degree = str(request.args.get('degree', '')).strip()

    filters = {}
    if q:
        filters['name__icontains'] = q
    if degree:
        filters['degree'] = degree

    docs = Major.objects(**filters).order_by('name')
    return jsonify([_serialize_major(m) for m in docs])


@admin_bp.route('/majors/<major_id>', methods=['GET'])
@admin_required
def get_major(current_user, major_id):
    doc = Major.objects(id=major_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404
    return jsonify(_serialize_major(doc))


@admin_bp.route('/majors', methods=['POST'])
@admin_required
def create_major(current_user):
    data = request.get_json() or {}
    if not data.get('name') or not data.get('degree'):
        return jsonify({'message': 'Missing required fields'}), 400

    try:
        payload = _normalize_major_payload(data)
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400

    doc = Major(
        name=payload.get('name', str(data.get('name') or '').strip()),
        degree=payload.get('degree'),
        reportLanguage=payload.get('reportLanguage', 'English'),
        reportContentType=payload.get('reportContentType', 'Text'),
        aiPromptContext=payload.get('aiPromptContext', ''),
        isActive=payload.get('isActive', True),
    )
    if 'reportPolicy' in payload:
        doc.reportPolicy = payload['reportPolicy']
    if 'reportSections' in payload:
        doc.reportSections = payload['reportSections']

    doc.save()
    return jsonify(_serialize_major(doc)), 201


@admin_bp.route('/majors/<major_id>', methods=['PUT'])
@admin_required
def update_major(current_user, major_id):
    doc = Major.objects(id=major_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404

    data = request.get_json() or {}
    try:
        payload = _normalize_major_payload(data)
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400

    for field in [
        'name',
        'degree',
        'reportLanguage',
        'reportContentType',
        'aiPromptContext',
        'reportPolicy',
        'reportSections',
        'isActive',
    ]:
        if field in payload:
            setattr(doc, field, payload[field])
    doc.updatedAt = datetime.utcnow()
    doc.save()
    return jsonify(_serialize_major(doc))


@admin_bp.route('/majors/<major_id>', methods=['DELETE'])
@admin_required
def delete_major(current_user, major_id):
    Major.objects(id=major_id).delete()
    return jsonify({'message': 'Deleted'})


@admin_bp.route('/universities', methods=['GET'])
@admin_required
def get_universities(current_user):
    q = str(request.args.get('q', '')).strip()
    filters = {'name__icontains': q} if q else {}
    docs = University.objects(**filters).order_by('name')
    return jsonify([_serialize_university(d) for d in docs])


@admin_bp.route('/universities/merge', methods=['POST'])
@admin_required
def merge_universities(current_user):
    data = request.get_json() or {}
    source_id = data.get('sourceId')
    target_id = data.get('targetId')
    if not source_id or not target_id:
        return jsonify({'message': 'sourceId and targetId are required'}), 400

    College.objects(university=source_id).update(set__university=target_id)
    User.objects(university=source_id).update(set__university=target_id)
    Report.objects(university=source_id).update(set__university=target_id)
    University.objects(id=source_id).delete()
    return jsonify({'message': 'Merged successfully'})


@admin_bp.route('/universities/<university_id>', methods=['PUT'])
@admin_required
def update_university(current_user, university_id):
    doc = University.objects(id=university_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404

    data = request.get_json() or {}
    for field in [
        'name', 'villageCityName', 'tehsil', 'district', 'state',
        'website', 'isVerified', 'isActive'
    ]:
        if field in data:
            setattr(doc, field, data[field])
    doc.updatedAt = datetime.utcnow()
    doc.save()
    return jsonify(_serialize_university(doc))


@admin_bp.route('/universities/<university_id>', methods=['DELETE'])
@admin_required
def delete_university(current_user, university_id):
    University.objects(id=university_id).delete()
    return jsonify({'message': 'Deleted'})


@admin_bp.route('/colleges', methods=['GET'])
@admin_required
def get_colleges(current_user):
    q = str(request.args.get('q', '')).strip()
    filters = {'name__icontains': q} if q else {}
    docs = College.objects(**filters).order_by('name')
    return jsonify([_serialize_college(d) for d in docs])


@admin_bp.route('/colleges/merge', methods=['POST'])
@admin_required
def merge_colleges(current_user):
    data = request.get_json() or {}
    source_id = data.get('sourceId')
    target_id = data.get('targetId')
    if not source_id or not target_id:
        return jsonify({'message': 'sourceId and targetId are required'}), 400

    User.objects(college=source_id).update(set__college=target_id)
    Report.objects(college=source_id).update(set__college=target_id)
    College.objects(id=source_id).delete()
    return jsonify({'message': 'Merged successfully'})


@admin_bp.route('/colleges/<college_id>', methods=['PUT'])
@admin_required
def update_college(current_user, college_id):
    doc = College.objects(id=college_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404

    data = request.get_json() or {}
    for field in [
        'name', 'university', 'villageCityName', 'tehsil', 'district',
        'state', 'website', 'logo', 'isVerified', 'isActive'
    ]:
        if field in data:
            setattr(doc, field, data[field])
    doc.updatedAt = datetime.utcnow()
    doc.save()
    return jsonify(_serialize_college(doc))


@admin_bp.route('/colleges/<college_id>', methods=['DELETE'])
@admin_required
def delete_college(current_user, college_id):
    College.objects(id=college_id).delete()
    return jsonify({'message': 'Deleted'})


@admin_bp.route('/industries', methods=['GET'])
@admin_required
def get_industries(current_user):
    q = str(request.args.get('q', '')).strip()
    filters = {'name__icontains': q} if q else {}
    docs = Industry.objects(**filters).order_by('name')
    return jsonify([_serialize_industry(d) for d in docs])


@admin_bp.route('/industries/merge', methods=['POST'])
@admin_required
def merge_industries(current_user):
    data = request.get_json() or {}
    source_id = data.get('sourceId')
    target_id = data.get('targetId')
    if not source_id or not target_id:
        return jsonify({'message': 'sourceId and targetId are required'}), 400

    User.objects(industry=source_id).update(set__industry=target_id)
    Report.objects(industry=source_id).update(set__industry=target_id)
    Industry.objects(id=source_id).delete()
    return jsonify({'message': 'Merged successfully'})


@admin_bp.route('/industries/<industry_id>', methods=['PUT'])
@admin_required
def update_industry(current_user, industry_id):
    doc = Industry.objects(id=industry_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404

    data = request.get_json() or {}
    for field in [
        'name', 'villageCityName', 'tehsil', 'district', 'state',
        'website', 'logo', 'isVerified', 'isActive'
    ]:
        if field in data:
            setattr(doc, field, data[field])
    doc.updatedAt = datetime.utcnow()
    doc.save()
    return jsonify(_serialize_industry(doc))


@admin_bp.route('/industries/<industry_id>', methods=['DELETE'])
@admin_required
def delete_industry(current_user, industry_id):
    Industry.objects(id=industry_id).delete()
    return jsonify({'message': 'Deleted'})


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    q = str(request.args.get('q', '')).strip()
    users_qs = User.objects(role='student')
    if q:
        users_qs = users_qs.filter(__raw__={
            '$or': [
                {'name': {'$regex': q, '$options': 'i'}},
                {'email': {'$regex': q, '$options': 'i'}},
            ]
        })

    docs = users_qs.order_by('-createdAt')
    return jsonify([_serialize_user(u) for u in docs])


@admin_bp.route('/users/<user_id>/toggle', methods=['PUT'])
@admin_required
def toggle_user(current_user, user_id):
    doc = User.objects(id=user_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404
    doc.isActive = not bool(doc.isActive)
    doc.updatedAt = datetime.utcnow()
    doc.save()
    return jsonify(_serialize_user(doc))


@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user, user_id):
    User.objects(id=user_id).delete()
    Report.objects(user=user_id).delete()
    Payment.objects(user=user_id).delete()
    return jsonify({'message': 'Deleted'})


@admin_bp.route('/users/<user_id>', methods=['GET'])
@admin_required
def get_user(current_user, user_id):
    doc = User.objects(id=user_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404
    return jsonify(_serialize_user(doc))


@admin_bp.route('/services', methods=['GET'])
@admin_required
def get_services(current_user):
    docs = Service.objects().order_by('name')
    return jsonify([_serialize_service(s) for s in docs])


@admin_bp.route('/services', methods=['POST'])
@admin_required
def create_service(current_user):
    data = request.get_json() or {}
    if not data.get('name') or not data.get('type'):
        return jsonify({'message': 'name and type are required'}), 400

    doc = Service(
        name=data['name'],
        type=data['type'],
        price=float(data.get('price', data.get('basePrice', 0)) or 0),
        gstIncluded=bool(data.get('gstIncluded', False)),
        gstPercent=int(data.get('gstPercent', 18) or 18),
        freeLimit=int(data.get('freeLimit', 0) or 0),
        description=data.get('description', ''),
        isActive=bool(data.get('isActive', True)),
    )
    if 'degreePricing' in data and isinstance(data['degreePricing'], list):
        doc.degreePricing = data['degreePricing']

    doc.save()
    return jsonify(_serialize_service(doc)), 201


@admin_bp.route('/services/<service_id>', methods=['PUT'])
@admin_required
def update_service(current_user, service_id):
    doc = Service.objects(id=service_id).first()
    if not doc:
        return jsonify({'message': 'Not found'}), 404

    data = request.get_json() or {}
    field_map = {
        'name': 'name',
        'type': 'type',
        'price': 'price',
        'basePrice': 'price',
        'gstIncluded': 'gstIncluded',
        'gstPercent': 'gstPercent',
        'freeLimit': 'freeLimit',
        'description': 'description',
        'degreePricing': 'degreePricing',
        'isActive': 'isActive',
    }
    for in_field, model_field in field_map.items():
        if in_field in data:
            setattr(doc, model_field, data[in_field])
    doc.updatedAt = datetime.utcnow()
    doc.save()
    return jsonify(_serialize_service(doc))


@admin_bp.route('/services/<service_id>', methods=['DELETE'])
@admin_required
def delete_service(current_user, service_id):
    Service.objects(id=service_id).delete()
    return jsonify({'message': 'Deleted'})


@admin_bp.route('/payments', methods=['GET'])
@admin_required
def get_payments(current_user):
    from_date = str(request.args.get('from', '')).strip()
    to_date = str(request.args.get('to', '')).strip()

    filters = {}
    created_filter = {}
    if from_date:
        try:
            created_filter['$gte'] = datetime.fromisoformat(from_date)
        except ValueError:
            pass
    if to_date:
        try:
            created_filter['$lte'] = datetime.fromisoformat(to_date)
        except ValueError:
            pass

    if created_filter:
        filters['createdAt'] = created_filter

    docs = Payment.objects(__raw__=filters).order_by('-createdAt')
    return jsonify([_serialize_payment(p) for p in docs])


@admin_bp.route('/reports', methods=['GET'])
@admin_required
def get_reports(current_user):
    docs = Report.objects().order_by('-createdAt')
    return jsonify([_serialize_report(r) for r in docs])


@admin_bp.route('/reports/<report_id>', methods=['DELETE'])
@admin_required
def delete_report(current_user, report_id):
    Report.objects(id=report_id).delete()
    return jsonify({'message': 'Deleted'})
