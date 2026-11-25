import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import User, Doctor, Patient, Appointment


class Command(BaseCommand):
    help = 'Seed initial Admin, Doctor, Patient, and Appointment records (mirrors seed.js)'

    def handle(self, *args, **options):
        Appointment.objects.all().delete()
        Patient.objects.all().delete()
        Doctor.objects.all().delete()
        User.objects.all().delete()

        admin_user = User(email='admin@curalync.com', role='Admin', status='Active')
        admin_user.set_password('password123')
        admin_user.save()

        doc_user1 = User(email='doctor@curalync.com', role='Doctor', status='Active')
        doc_user1.set_password('password123')
        doc_user1.save()
        doc1 = Doctor.objects.create(
            user=doc_user1,
            first_name='John',
            last_name='Doe',
            specialization='Cardiology',
            qualifications=['MBBS', 'MD'],
            experience_years=10,
            contact_number='1234567890',
            consultation_fee=150,
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        )

        doc_user2 = User(email='doctor2@curalync.com', role='Doctor', status='Active')
        doc_user2.set_password('password123')
        doc_user2.save()
        doc2 = Doctor.objects.create(
            user=doc_user2,
            first_name='Sarah',
            last_name='Mitchell',
            specialization='General',
            qualifications=['MBBS'],
            experience_years=6,
            contact_number='2222222222',
            consultation_fee=100,
            available_days=['Monday', 'Wednesday', 'Friday'],
        )

        pat_user1 = User(email='patient@curalync.com', role='Patient', status='Active')
        pat_user1.set_password('password123')
        pat_user1.save()
        pat1 = Patient.objects.create(
            user=pat_user1,
            first_name='Jane',
            last_name='Smith',
            dob=datetime.datetime(1990, 1, 1, tzinfo=datetime.timezone.utc),
            gender='Female',
            contact_number='0987654321',
            address='123 Main St',
            medical_history=['Penicillin'],
        )

        pat_user2 = User(email='patient2@curalync.com', role='Patient', status='Active')
        pat_user2.set_password('password123')
        pat_user2.save()
        pat2 = Patient.objects.create(
            user=pat_user2,
            first_name='Michael',
            last_name='Brown',
            dob=datetime.datetime(1988, 6, 12, tzinfo=datetime.timezone.utc),
            gender='Male',
            contact_number='7777777777',
            address='456 Park Ave',
            medical_history=[],
        )

        pat_user3 = User(email='patient3@curalync.com', role='Patient', status='Active')
        pat_user3.set_password('password123')
        pat_user3.save()
        pat3 = Patient.objects.create(
            user=pat_user3,
            first_name='Emily',
            last_name='Davis',
            dob=datetime.datetime(1995, 11, 3, tzinfo=datetime.timezone.utc),
            gender='Female',
            contact_number='8888888888',
            address='789 Lake Rd',
            medical_history=['Peanuts'],
        )

        tomorrow = timezone.now() + datetime.timedelta(days=1)
        next_week = timezone.now() + datetime.timedelta(days=7)

        Appointment.objects.create(
            patient=pat1,
            doctor=doc1,
            date=tomorrow,
            time_slot='10:00 AM',
            status='Confirmed',
            reason='Regular Checkup',
        )
        Appointment.objects.create(
            patient=pat2,
            doctor=doc2,
            date=next_week,
            time_slot='01:00 PM',
            status='Pending',
            reason='Fever and cold',
        )
        Appointment.objects.create(
            patient=pat3,
            doctor=doc1,
            date=next_week,
            time_slot='02:30 PM',
            status='Confirmed',
            reason='Follow-up consultation',
        )

        self.stdout.write(self.style.SUCCESS('Data seeded successfully!'))
