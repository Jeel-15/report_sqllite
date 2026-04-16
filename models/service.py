from mongoengine import (
    Document,
    StringField,
    BooleanField,
    DateTimeField,
    FloatField,
    IntField,
    EmbeddedDocument,
    EmbeddedDocumentField,
    EmbeddedDocumentListField,
    ReferenceField,
)
import datetime


class DegreePricing(EmbeddedDocument):
    degree = ReferenceField('Degree')
    price = FloatField(default=0.0)


class Service(Document):
    meta = {'collection': 'services', 'strict': False}

    name = StringField(required=True, unique=True)
    type = StringField(choices=('resume', 'task', 'report'), required=True)
    price = FloatField(default=0.0)
    gstIncluded = BooleanField(default=False)
    gstPercent = IntField(default=18)
    freeLimit = IntField(default=0)
    degreePricing = EmbeddedDocumentListField(DegreePricing, default=list)
    description = StringField(default='')
    isActive = BooleanField(default=True)

    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)