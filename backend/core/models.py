import os
import bcrypt
from django.db import models
from django.utils import timezone


def generate_object_id():
    return os.urandom(12).hex()


def default_available_days():
    return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']


def default_available_time_slots():
    return ['09:00 AM', '10:00 AM', '11:00 AM', '01:00 PM', '02:00 PM', '03:00 PM', '04:00 PM']


class User(models.Model):
    ROLE_CHOICES = [('Admin', 'Admin'), ('Doctor', 'Doctor'), ('Patient', 'Patient')]
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]

    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    avatar = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    last_login = models.DateTimeField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    reset_password_token = models.CharField(max_length=255, blank=True, null=True)
    reset_password_expire = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def set_password(self, raw_password: str):
        salt = bcrypt.gensalt(rounds=10)
        self.password = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, raw_password: str) -> bool:
        if not self.password or not raw_password:
            return False
        try:
            return bcrypt.checkpw(raw_password.encode('utf-8'), self.password.encode('utf-8'))
        except Exception:
            return False

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
        if self.password and not self.password.startswith(('$2a$', '$2b$', '$2y$')):
            self.set_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.email} ({self.role})'


class Doctor(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_profiles')
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=150)
    department = models.CharField(max_length=150, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar = models.TextField(blank=True, null=True)
    verification_document = models.TextField(blank=True, null=True)
    qualifications = models.JSONField(default=list)
    experience_years = models.IntegerField(default=0)
    contact_number = models.CharField(max_length=50)
    consultation_fee = models.FloatField(default=0)
    is_available = models.BooleanField(default=True)
    available_days = models.JSONField(default=default_available_days)
    available_time_slots = models.JSONField(default=default_available_time_slots)
    average_rating = models.FloatField(default=0)
    total_reviews = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'doctors'

    def __str__(self):
        return f'Dr. {self.first_name} {self.last_name}'


class Patient(models.Model):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]

    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_profiles')
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    dob = models.DateTimeField()
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    contact_number = models.CharField(max_length=50)
    address = models.TextField(blank=True, null=True)
    avatar = models.TextField(blank=True, null=True)
    blood_group = models.CharField(max_length=20, blank=True, null=True)
    allergies = models.JSONField(default=list)
    emergency_contact = models.JSONField(default=dict, blank=True)
    insurance_details = models.JSONField(default=dict, blank=True)
    medical_history = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patients'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Appointment(models.Model):
    TYPE_CHOICES = [('In-Person', 'In-Person'), ('Video', 'Video'), ('Phone', 'Phone')]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateTimeField()
    time_slot = models.CharField(max_length=50)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='In-Person')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    reason = models.TextField()
    notes = models.TextField(blank=True, null=True)
    cancel_reason = models.TextField(blank=True, null=True)
    attachments = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointments'


class Prescription(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescriptions')
    medications = models.JSONField(default=list)
    instructions = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'prescriptions'


class MedicalRecord(models.Model):
    UPLOADER_CHOICES = [('Doctor', 'Doctor'), ('Patient', 'Patient')]
    RECORD_TYPE_CHOICES = [
        ('Lab Result', 'Lab Result'),
        ('Diagnosis', 'Diagnosis'),
        ('Scan', 'Scan'),
        ('Prescription', 'Prescription'),
        ('Other', 'Other'),
    ]

    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_records')
    uploaded_by = models.CharField(max_length=20, choices=UPLOADER_CHOICES, default='Doctor')
    record_type = models.CharField(max_length=30, choices=RECORD_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file_url = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'medical_records'


class Message(models.Model):
    SENDER_ROLE_CHOICES = [('Patient', 'Patient'), ('Doctor', 'Doctor')]

    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    conversation_id = models.CharField(max_length=100, db_index=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    sender_role = models.CharField(max_length=20, choices=SENDER_ROLE_CHOICES)
    text = models.TextField(blank=True, null=True)
    attachment = models.JSONField(blank=True, null=True)
    is_call_log = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messages'


class Notification(models.Model):
    TYPE_CHOICES = [
        ('Appointment', 'Appointment'),
        ('Prescription', 'Prescription'),
        ('System', 'System'),
        ('MedicalRecord', 'MedicalRecord'),
    ]

    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='System')
    is_read = models.BooleanField(default=False)
    link = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'


class ApprovalRequest(models.Model):
    ROLE_CHOICES = [('Admin', 'Admin'), ('Doctor', 'Doctor'), ('AdminReset', 'AdminReset')]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Expired', 'Expired'),
    ]

    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    token = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    notify_email = models.EmailField()
    payload = models.JSONField(default=dict)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_requests')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approval_requests'


class AuditLog(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=100)
    resource = models.CharField(max_length=100)
    details = models.JSONField(default=dict, blank=True, null=True)
    ip_address = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'audit_logs'


class FAQ(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    question = models.TextField()
    answer = models.TextField()
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'faqs'


class Review(models.Model):
    STATUS_CHOICES = [('approved', 'approved'), ('pending', 'pending'), ('rejected', 'rejected')]

    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='reviews')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='reviews')
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField()
    comment = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'


class Service(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    tags = models.JSONField(default=list)
    image = models.TextField(blank=True, default='')
    icon_name = models.CharField(max_length=100, default='Stethoscope')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'services'


class Subscriber(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_object_id, editable=False)
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscribers'
