from django.urls import path
from core.views.auth_views import (
    RegisterView,
    LoginView,
    MeView,
    ForgotPasswordView,
    ResetPasswordView,
)
from core.views.user_views import (
    UsersListView,
    UserStatusUpdateView,
    DoctorsListView,
    PatientsListView,
    DoctorProfileUpdateView,
    PatientProfileUpdateView,
    AdminUserProfileView,
    UserDeleteView,
)
from core.views.appointment_views import (
    AppointmentsView,
    AppointmentStatusView,
    AppointmentCancelView,
    AppointmentRescheduleView,
    AppointmentPrescriptionView,
    AvailableSlotsView,
)
from core.views.analytics_views import AnalyticsView
from core.views.approval_views import (
    RequestAdminCreationView,
    RequestDoctorCreationView,
    RequestAdminResetView,
    ApproveByTokenView,
    PendingApprovalsView,
    ApproveRequestByIdView,
    RejectRequestByIdView,
)
from core.views.chat_views import (
    ConversationsView,
    MessagesView,
    SendMessageView,
    ChatUploadView,
    MarkReadView,
    IceServersView,
)
from core.views.faq_views import FAQListCreateView, FAQAllView, FAQDetailView
from core.views.record_views import (
    MedicalRecordCreateView,
    PatientRecordUploadView,
    RecordByIdOrPatientView,
)
from core.views.notification_views import (
    NotificationsListView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
)
from core.views.public_views import PublicDoctorsView, SubscribeNewsletterView
from core.views.review_views import ReviewCreateView, DoctorReviewsView, PublicReviewsView
from core.views.service_views import ServiceListCreateView, ServiceDetailView
from core.views.upload_views import UploadAvatarView, UploadDocumentView

urlpatterns = [
    # Auth
    path('auth/register', RegisterView.as_view()),
    path('auth/login', LoginView.as_view()),
    path('auth/me', MeView.as_view()),
    path('auth/forgot-password', ForgotPasswordView.as_view()),
    path('auth/reset-password', ResetPasswordView.as_view()),

    # Users
    path('users', UsersListView.as_view()),
    path('users/doctors', DoctorsListView.as_view()),
    path('users/doctors/profile', DoctorProfileUpdateView.as_view()),
    path('users/patients', PatientsListView.as_view()),
    path('users/patients/profile', PatientProfileUpdateView.as_view()),
    path('users/<str:user_id>/status', UserStatusUpdateView.as_view()),
    path('users/<str:user_id>/profile', AdminUserProfileView.as_view()),
    path('users/<str:user_id>', UserDeleteView.as_view()),

    # Appointments
    path('appointments/slots', AvailableSlotsView.as_view()),
    path('appointments', AppointmentsView.as_view()),
    path('appointments/<str:appointment_id>/status', AppointmentStatusView.as_view()),
    path('appointments/<str:appointment_id>/reschedule', AppointmentRescheduleView.as_view()),
    path('appointments/<str:appointment_id>/prescription', AppointmentPrescriptionView.as_view()),
    path('appointments/<str:appointment_id>', AppointmentCancelView.as_view()),

    # Analytics
    path('analytics', AnalyticsView.as_view()),

    # Approvals
    path('approvals/admin', RequestAdminCreationView.as_view()),
    path('approvals/doctor', RequestDoctorCreationView.as_view()),
    path('approvals/admin-reset', RequestAdminResetView.as_view()),
    path('approvals/approve/<str:token>', ApproveByTokenView.as_view()),
    path('approvals/pending', PendingApprovalsView.as_view()),
    path('approvals/<str:approval_id>/approve', ApproveRequestByIdView.as_view()),
    path('approvals/<str:approval_id>/reject', RejectRequestByIdView.as_view()),

    # Notifications
    path('notifications', NotificationsListView.as_view()),
    path('notifications/read-all', NotificationMarkAllReadView.as_view()),
    path('notifications/<str:notif_id>/read', NotificationMarkReadView.as_view()),

    # Medical Records
    path('records/my-upload', PatientRecordUploadView.as_view()),
    path('records', MedicalRecordCreateView.as_view()),
    path('records/<str:item_id>', RecordByIdOrPatientView.as_view()),

    # Public
    path('public/doctors', PublicDoctorsView.as_view()),
    path('public/subscribe', SubscribeNewsletterView.as_view()),

    # Uploads (including singular /upload/document alias used by Login.jsx)
    path('uploads/avatar', UploadAvatarView.as_view()),
    path('uploads/document', UploadDocumentView.as_view()),
    path('upload/document', UploadDocumentView.as_view()),

    # Reviews
    path('reviews', ReviewCreateView.as_view()),
    path('reviews/public', PublicReviewsView.as_view()),
    path('reviews/doctor/<str:doctor_id>', DoctorReviewsView.as_view()),

    # Services
    path('services', ServiceListCreateView.as_view()),
    path('services/<str:service_id>', ServiceDetailView.as_view()),

    # FAQs
    path('faqs', FAQListCreateView.as_view()),
    path('faqs/all', FAQAllView.as_view()),
    path('faqs/<str:faq_id>', FAQDetailView.as_view()),

    # Chat
    path('chat/conversations', ConversationsView.as_view()),
    path('chat/messages/<str:conversation_id>', MessagesView.as_view()),
    path('chat/ice-servers', IceServersView.as_view()),
    path('chat/send', SendMessageView.as_view()),
    path('chat/upload', ChatUploadView.as_view()),
    path('chat/mark-read/<str:conversation_id>', MarkReadView.as_view()),
]
