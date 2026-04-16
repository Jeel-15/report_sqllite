from mongoengine import Document, StringField, BooleanField, DateTimeField, ReferenceField, ListField, DictField, EmbeddedDocument, EmbeddedDocumentField, EmbeddedDocumentListField
import datetime

class EmploymentOpportunity(EmbeddedDocument):
    meta = {'strict': False}

    companyType = StringField()
    positions = StringField()

class ReportSection(EmbeddedDocument):
    meta = {'strict': False}

    key = StringField(required=True)
    title = StringField(required=True)
    description = StringField(default='')

class ReportPolicy(EmbeddedDocument):
    meta = {'strict': False}

    strictLanguageOnly = BooleanField(default=False)
    allowedLanguages = ListField(StringField(), default=list)
    generationInstruction = StringField(default='')
    uiLabels = DictField(default=dict)
    sectionTitleMap = DictField(default=dict)
    contentFeatures = ListField(StringField(), default=list)
    imagesRequired = BooleanField(default=False)

class Major(Document):
    meta = {
        'collection': 'majors',
        'strict': False,
        'indexes': [
            {'fields': ['degree', 'name'], 'unique': True}
        ]
    }
    
    degree = ReferenceField('Degree', required=True)
    name = StringField(required=True)
    
    reportLanguage = StringField(default='English')
    reportContentType = StringField(default='Text')
    aiPromptContext = StringField(default='')
    
    reportPolicy = EmbeddedDocumentField(ReportPolicy, default=ReportPolicy)
    employmentOpportunities = EmbeddedDocumentListField(EmploymentOpportunity, default=list)
    reportSections = EmbeddedDocumentListField(ReportSection, default=list)
    
    isActive = BooleanField(default=True)
    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)
