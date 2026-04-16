from mongoengine import Document, StringField, BooleanField, DateTimeField, ReferenceField, IntField
import datetime
import bcrypt

class User(Document):
    meta = {'collection': 'users', 'strict': False}
    
    email = StringField(required=True, unique=True)
    password = StringField(required=True)
    role = StringField(choices=('student', 'admin'), default='student')
    isActive = BooleanField(default=True)
    
    name = StringField(required=True)
    villageCityName = StringField(default='')
    tehsil = StringField(default='')
    district = StringField(default='')
    state = StringField(default='')
    phone = StringField(default='')
    whatsapp = StringField(default='')
    
    university = ReferenceField('University')
    college = ReferenceField('College')
    degree = ReferenceField('Degree')
    major = ReferenceField('Major')
    rollNumber = StringField(default='')
    enrollmentNumber = StringField(default='')
    
    industry = ReferenceField('Industry')
    supervisorName = StringField(default='')
    supervisorContact = StringField(default='')
    
    profileCompleted = BooleanField(default=False)

    # Forgot-password OTP state
    resetOtpHash = StringField(default=None, null=True)
    resetOtpExpiresAt = DateTimeField(default=None, null=True)
    resetOtpAttemptCount = IntField(default=0)
    
    createdAt = DateTimeField(default=datetime.datetime.utcnow)
    updatedAt = DateTimeField(default=datetime.datetime.utcnow)

    def set_password(self, password):
        salt = bcrypt.gensalt(12)
        self.password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
