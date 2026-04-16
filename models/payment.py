from mongoengine import Document, StringField, FloatField, DateTimeField, ReferenceField, DynamicField
import datetime

class Payment(Document):
    meta = {'collection': 'payments', 'strict': False}
    
    user = ReferenceField('User', required=True)
    service = DynamicField(required=True)
    report = ReferenceField('Report')
    
    amount = FloatField(required=True)
    gstAmount = FloatField(default=0.0)
    totalAmount = FloatField(required=True)
    
    status = StringField(choices=('pending', 'completed', 'failed', 'refunded'), default='pending')
    paymentMethod = StringField(default='')
    transactionId = StringField(default='')
    
    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)
