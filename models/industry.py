from mongoengine import Document, StringField, BooleanField, DateTimeField, ReferenceField
import datetime

class Industry(Document):
    meta = {'collection': 'industries', 'strict': False}
    
    name = StringField(required=True)
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
