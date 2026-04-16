from mongoengine import (
    Document,
    StringField,
    BooleanField,
    DateTimeField,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    ReferenceField,
)
import datetime


class InternshipTypeSection(EmbeddedDocument):
    key = StringField(required=True)
    title = StringField(required=True)
    description = StringField(default='')


class InternshipType(Document):
    meta = {'collection': 'internshiptypes', 'strict': False}

    name = StringField(required=True)
    description = StringField(required=True)
    aiPromptContext = StringField(required=True)
    reportSections = EmbeddedDocumentListField(InternshipTypeSection, default=list)
    icon = StringField(default='📄')
    isActive = BooleanField(default=True)
    createdBy = ReferenceField('User')

    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)