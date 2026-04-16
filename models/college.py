from mongoengine import Document, StringField, BooleanField, DateTimeField, ReferenceField
import datetime
from .university import University

class College(Document):
    meta = {'collection': 'colleges', 'strict': False}
    
    name = StringField(required=True)
    university = ReferenceField(University, required=True)
    villageCityName = StringField(default='')
    tehsil = StringField(default='')
    district = StringField(default='')
    state = StringField(default='')
    website = StringField(default='')
    logo = StringField(default='')
    createdBy = ReferenceField('User')
    isVerified = BooleanField(default=False)
    isActive = BooleanField(default=True)
    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)
