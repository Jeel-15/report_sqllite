from mongoengine import Document, StringField, BooleanField, DateTimeField
import datetime

class Degree(Document):
    meta = {'collection': 'degrees', 'strict': False}
    
    name = StringField(required=True, unique=True)
    isActive = BooleanField(default=True)
    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)
