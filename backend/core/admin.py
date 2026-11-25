from django.contrib import admin
from core.models import (
    User, Doctor, Patient, Appointment, Prescription,
    MedicalRecord, Message, Notification, ApprovalRequest,
    AuditLog, FAQ, Review, Service, Subscriber,
)

for model in (
    User, Doctor, Patient, Appointment, Prescription,
    MedicalRecord, Message, Notification, ApprovalRequest,
    AuditLog, FAQ, Review, Service, Subscriber,
):
    admin.site.register(model)
