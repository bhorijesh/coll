from django.db import models
from django.contrib.auth.models import User

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

    def __str__(self):
        return self.full_name

class Booking(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Storing the pickup and drop-off locations with lat/lon
    from_location_lat = models.DecimalField(null=True, blank=True,max_digits=9, decimal_places=6)  # Example: 19.30000
    from_location_lon = models.DecimalField(null=True, blank=True,max_digits=9, decimal_places=6)  # Example: 84.79000
    to_location_lat = models.DecimalField(null=True, blank=True,max_digits=9, decimal_places=6)  # Example: 19.50000
    to_location_lon = models.DecimalField(null=True, blank=True,max_digits=9, decimal_places=6)  # Example: 84.80000

    def __str__(self):
        return f'{self.customer.full_name} - {self.car.name}'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    
class lat_long(models.Model):
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
class Payment(models.Model):
    token = models.CharField(max_length=100)
    amount = models.IntegerField()
    status = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)