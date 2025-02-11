from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings

class Car(models.Model):
    FUEL_TYPES = [
        ('Petrol', 'Petrol'),
        ('Diesel', 'Diesel'),
        ('Electric', 'Electric'),
        ('Hybrid', 'Hybrid'),
    ]
    name = models.CharField(max_length=100)
    year = models.PositiveIntegerField()  # Manufacturing year
    fuel_type = models.CharField(max_length=10, choices=FUEL_TYPES)  # Fuel type
    seating_capacity = models.PositiveIntegerField(default=4)  # Number of seats
    admin = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    is_available = models.BooleanField(default=True)  # Availability status
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='cars/')
    latitude = models.FloatField(null=True, blank=True)  # Latitude field
    longitude = models.FloatField(null=True, blank=True)  # Longitude field

    def __str__(self):
        return self.name

class Customer(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    license_image = models.ImageField(upload_to='license_images/', null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.full_name
    
class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),  # Add a new status for cancelled bookings
    )

    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notification = models.TextField(blank=True, null=True)  # Field for notifications

    def __str__(self):
        return f'{self.customer.full_name} - {self.car.name}'


class lat_long(models.Model):
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to create a UserProfile whenever a User is created.
    """
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal to save the UserProfile whenever the User is saved.
    """
    instance.userprofile.save()
class Payment(models.Model):
    token = models.CharField(max_length=100)
    amount = models.IntegerField()
    status = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Booking)
def send_booking_status_email(sender, instance, **kwargs):
    """
    Send an email notification to the customer when their booking status is updated.
    """
    if instance.status == 'verified':
        subject = "Booking Verified - Your Car Rental Request"
        message = f"""
        Dear {instance.customer.full_name},

        Congratulations! Your booking has been verified.

        Booking Details:
        - Car: {instance.car.name}
        - Start Date: {instance.start_date}
        - End Date: {instance.end_date}
        - Total Amount: ${instance.total_amount}

        Please proceed with the payment.

        Thank you for choosing our service!
        """
    elif instance.status == 'cancelled':
        subject = "Booking Rejected - Car Rental Request"
        message = f"""
        Dear {instance.customer.full_name},

        Unfortunately, your booking request has been rejected.

        Booking Details:
        - Car: {instance.car.name}
        - Start Date: {instance.start_date}
        - End Date: {instance.end_date}

        If you have any questions, please contact our support team.

        Thank you for your understanding.
        """
    else:
        return  # No need to send an email for other status changes

    # Send the email
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,  # Your configured email sender
        [instance.customer.email],  # Send email to the customer
        fail_silently=False,
    )
