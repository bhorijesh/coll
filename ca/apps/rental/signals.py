from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mass_mail
from django.contrib.auth.models import User
from .models import Car
from django.conf import settings

@receiver(post_save, sender=Car)
def notify_users_new_car(sender, instance, created, **kwargs):
    if created:  # Only send email when a new car is created
        users = User.objects.all()
        subject = "New Car Available!"
        message = f"""
        Hello!
        
        A new car has been added to our fleet!
        
        Car Details:
        Name: {instance.name}
        Year: {instance.year}
        Fuel Type: {instance.fuel_type}
        Seating Capacity: {instance.seating_capacity}
        Price per km: ${instance.price_per_km}
        
        Visit our website to check it out!
        """
        
        # Prepare mass mail
        emails = [(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email]
        ) for user in users if user.email]
        
        # Send mass mail
        send_mass_mail(emails, fail_silently=False)