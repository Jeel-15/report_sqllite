from mongoengine import Document, StringField, BooleanField, DateTimeField, ReferenceField, DictField, IntField
import datetime

class Report(Document):
    meta = {'collection': 'reports', 'strict': False}
    
    user = ReferenceField('User', required=True)
    
    # Academic
    degree = ReferenceField('Degree', required=True)
    major = ReferenceField('Major', required=True)
    college = ReferenceField('College')
    university = ReferenceField('University')
    
    # Industry
    industry = ReferenceField('Industry')
    
    # Report Cover Page (Page 1)
    projectTitle = StringField(required=True)
    internshipTitle = StringField(default='')
    academicYear = StringField(default='')
    rollNumber = StringField(default='')
    studentEmail = StringField(default='')
    
    # Internship details
    supervisorName = StringField(default='')
    supervisorContact = StringField(default='')
    duration = StringField(default='')
    startDate = StringField(default='')
    endDate = StringField(default='')
    positionTitle = StringField(default='')
    
    # User input for AI
    briefDescription = StringField(required=True)
    keySkills = StringField(default='')
    
    # Generated
    reportLanguage = StringField(default='English')
    generatedContent = DictField(default=dict)
    generatedTitles = DictField(default=dict)
    generatedUiLabels = DictField(default=dict)
    editedContent = DictField(default=dict)
    # { "sectionKey": [ { "url": "...", "filename": "...", "position": "top|middle|bottom", "caption": "", "widthPercent": 100 } ] }
    sectionImages = DictField(default=dict)
    
    status = StringField(
        choices=('pending', 'generating', 'generated', 'edited', 'final', 'error'),
        default='pending'
    )
    errorMessage = StringField(default='')
    
    # Payment
    isPaid = BooleanField(default=False)
    payment = ReferenceField('Payment')
    downloadCount = IntField(default=0)
    
    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)
