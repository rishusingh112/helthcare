def _iso(dt):
    return dt.isoformat() if dt else None


def serialize_user(user, include_fields=None):
    if user is None:
        return None
    data = {
        '_id': user.id,
        'email': user.email,
        'avatar': user.avatar,
        'role': user.role,
        'status': user.status,
        'lastLogin': _iso(user.last_login),
        'createdAt': _iso(user.created_at),
        'updatedAt': _iso(user.updated_at),
    }
    if include_fields:
        return {'_id': user.id, **{k: data[k] for k in include_fields if k in data}}
    return data


def serialize_doctor(doc, populate_user=False, user_fields=None):
    if doc is None:
        return None
    user_val = (
        serialize_user(doc.user, include_fields=user_fields)
        if populate_user
        else doc.user_id
    )
    return {
        '_id': doc.id,
        'userId': user_val,
        'firstName': doc.first_name,
        'lastName': doc.last_name,
        'specialization': doc.specialization,
        'department': doc.department,
        'bio': doc.bio,
        'avatar': doc.avatar,
        'verificationDocument': doc.verification_document,
        'qualifications': doc.qualifications or [],
        'experienceYears': doc.experience_years,
        'contactNumber': doc.contact_number,
        'consultationFee': doc.consultation_fee,
        'isAvailable': doc.is_available,
        'availableDays': doc.available_days or [],
        'availableTimeSlots': doc.available_time_slots or [],
        'averageRating': doc.average_rating,
        'totalReviews': doc.total_reviews,
        'createdAt': _iso(doc.created_at),
        'updatedAt': _iso(doc.updated_at),
    }


def serialize_patient(pat, populate_user=False, user_fields=None):
    if pat is None:
        return None
    user_val = (
        serialize_user(pat.user, include_fields=user_fields)
        if populate_user
        else pat.user_id
    )
    return {
        '_id': pat.id,
        'userId': user_val,
        'firstName': pat.first_name,
        'lastName': pat.last_name,
        'dob': _iso(pat.dob),
        'gender': pat.gender,
        'contactNumber': pat.contact_number,
        'address': pat.address,
        'avatar': pat.avatar,
        'bloodGroup': pat.blood_group,
        'allergies': pat.allergies or [],
        'emergencyContact': pat.emergency_contact or {},
        'insuranceDetails': pat.insurance_details or {},
        'medicalHistory': pat.medical_history or [],
        'createdAt': _iso(pat.created_at),
        'updatedAt': _iso(pat.updated_at),
    }


def serialize_appointment(appt, populate=False):
    if appt is None:
        return None
    if populate:
        patient_val = serialize_patient(appt.patient, populate_user=True, user_fields=['email', 'avatar'])
        doctor_val = serialize_doctor(appt.doctor, populate_user=True, user_fields=['email', 'avatar'])
    else:
        patient_val = appt.patient_id
        doctor_val = appt.doctor_id
    return {
        '_id': appt.id,
        'patientId': patient_val,
        'doctorId': doctor_val,
        'date': _iso(appt.date),
        'timeSlot': appt.time_slot,
        'type': appt.type,
        'status': appt.status,
        'reason': appt.reason,
        'notes': appt.notes,
        'cancelReason': appt.cancel_reason,
        'attachments': appt.attachments or [],
        'createdAt': _iso(appt.created_at),
        'updatedAt': _iso(appt.updated_at),
    }


def serialize_prescription(pres):
    if pres is None:
        return None
    return {
        '_id': pres.id,
        'appointmentId': pres.appointment_id,
        'patientId': pres.patient_id,
        'doctorId': pres.doctor_id,
        'medications': pres.medications or [],
        'instructions': pres.instructions,
        'date': _iso(pres.date),
        'createdAt': _iso(pres.created_at),
        'updatedAt': _iso(pres.updated_at),
    }


def serialize_medical_record(rec, populate_doctor=False):
    if rec is None:
        return None
    doctor_val = None
    if rec.doctor_id:
        if populate_doctor and rec.doctor:
            doctor_val = {
                '_id': rec.doctor.id,
                'firstName': rec.doctor.first_name,
                'lastName': rec.doctor.last_name,
                'specialization': rec.doctor.specialization,
            }
        else:
            doctor_val = rec.doctor_id
    return {
        '_id': rec.id,
        'patientId': rec.patient_id,
        'doctorId': doctor_val,
        'uploadedBy': rec.uploaded_by,
        'recordType': rec.record_type,
        'title': rec.title,
        'description': rec.description,
        'fileUrl': rec.file_url,
        'date': _iso(rec.date),
        'createdAt': _iso(rec.created_at),
        'updatedAt': _iso(rec.updated_at),
    }


def serialize_message(msg):
    if msg is None:
        return None
    return {
        '_id': msg.id,
        'conversationId': msg.conversation_id,
        'senderId': msg.sender_id,
        'senderRole': msg.sender_role,
        'text': msg.text,
        'attachment': msg.attachment,
        'isCallLog': msg.is_call_log,
        'readAt': _iso(msg.read_at),
        'createdAt': _iso(msg.created_at),
        'updatedAt': _iso(msg.updated_at),
    }


def serialize_notification(notif):
    if notif is None:
        return None
    return {
        '_id': notif.id,
        'userId': notif.user_id,
        'title': notif.title,
        'message': notif.message,
        'type': notif.type,
        'isRead': notif.is_read,
        'link': notif.link,
        'createdAt': _iso(notif.created_at),
        'updatedAt': _iso(notif.updated_at),
    }


def serialize_approval(app):
    if app is None:
        return None
    return {
        '_id': app.id,
        'role': app.role,
        'status': app.status,
        'token': app.token,
        'expiresAt': _iso(app.expires_at),
        'notifyEmail': app.notify_email,
        'payload': app.payload or {},
        'requestedBy': app.requested_by_id,
        'createdAt': _iso(app.created_at),
        'updatedAt': _iso(app.updated_at),
    }


def serialize_faq(faq):
    if faq is None:
        return None
    return {
        '_id': faq.id,
        'question': faq.question,
        'answer': faq.answer,
        'order': faq.order,
        'isActive': faq.is_active,
        'createdAt': _iso(faq.created_at),
        'updatedAt': _iso(faq.updated_at),
    }


def serialize_review(rev, populate_patient=False, populate_doctor=False):
    if rev is None:
        return None
    patient_val = (
        {
            '_id': rev.patient.id,
            'firstName': rev.patient.first_name,
            'lastName': rev.patient.last_name,
            'avatar': rev.patient.avatar,
        }
        if populate_patient and rev.patient
        else rev.patient_id
    )
    doctor_val = (
        {
            '_id': rev.doctor.id,
            'firstName': rev.doctor.first_name,
            'lastName': rev.doctor.last_name,
            'specialization': rev.doctor.specialization,
        }
        if populate_doctor and rev.doctor
        else rev.doctor_id
    )
    return {
        '_id': rev.id,
        'patientId': patient_val,
        'doctorId': doctor_val,
        'appointmentId': rev.appointment_id,
        'rating': rev.rating,
        'comment': rev.comment,
        'status': rev.status,
        'createdAt': _iso(rev.created_at),
        'updatedAt': _iso(rev.updated_at),
    }


def serialize_service(svc):
    if svc is None:
        return None
    return {
        '_id': svc.id,
        'title': svc.title,
        'description': svc.description,
        'tags': svc.tags or [],
        'image': svc.image,
        'iconName': svc.icon_name,
        'createdAt': _iso(svc.created_at),
        'updatedAt': _iso(svc.updated_at),
    }
