from mongoengine import Document, StringField, BooleanField, DateTimeField, ReferenceField
import datetime

class University(Document):
    meta = {'collection': 'universities', 'strict': False}
    
    name = StringField(required=True)
    villageCityName = StringField(default='')
    tehsil = StringField(default='')
    district = StringField(default='')
    state = StringField(default='')
    website = StringField(default='')
    createdBy = ReferenceField('User')
    isVerified = BooleanField(default=False)
    isActive = BooleanField(default=True)
    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)
