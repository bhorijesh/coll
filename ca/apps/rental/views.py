import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, FormView, CreateView, TemplateView, UpdateView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from django.contrib.auth.forms import PasswordChangeForm
from datetime import datetime
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import math
from .models import *
from django.utils import timezone
from .utils import *
from .forms import *
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class index(ListView):
    model = Car
    template_name = 'car/index.html'
    context_object_name = 'car_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Default values for latitude and longitude
        context['user_lat'] = 0
        context['user_lon'] = 0
        return context

def nearby_cars(request):
    try:
        # Get latitude and longitude from the query parameters
        user_lat = float(request.GET.get('latitude'))
        user_lon = float(request.GET.get('longitude'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid latitude or longitude'}, status=400)

    # Fetch all cars from the database
    cars = Car.objects.all()

    # Calculate distances and filter nearby cars using the Haversine formula
    nearby_cars_list = []
    for car in cars:
        if car.latitude is not None and car.longitude is not None:  # Ensure coordinates are valid
            distance = haversine(user_lat, user_lon, car.latitude, car.longitude)
            if distance <= 30:  # Only include cars within 50 km
                nearby_cars_list.append({
                    'id': car.id,
                    'name': car.name,
                    'year': car.year,
                    'fuel_type': car.fuel_type,
                    'seating_capacity': car.seating_capacity,
                    'price_per_km': str(car.price_per_km),
                    'is_available': car.is_available,
                    'description': car.description,
                    'image_url': car.image.url if car.image else None,
                    'distance': round(distance, 2),
                    'latitude': car.latitude,  # Include latitude in the response
                    'longitude': car.longitude,  # Include longitude in the response
                })

    # Return the list of nearby cars as JSON
    return JsonResponse({'cars': nearby_cars_list})



class BookingView(LoginRequiredMixin, View):
    def get(self, request):
        # Fetch car_id, latitude, and longitude from query parameters
        car_id = request.GET.get('car_id')
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')

        if not car_id:
            return redirect('home')  # Redirect if no car_id is provided

        car = get_object_or_404(Car, id=car_id)

        # If no latitude or longitude is provided, fallback to default or error
        if latitude is None or longitude is None:
            return render(request, 'car/booking_form.html', {
                'car': car,
                'error_message': 'No location data found.'
            })

        return render(request, 'car/booking_form.html', {
            'car': car,
            'latitude': latitude,
            'longitude': longitude
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        car_id = request.POST.get('car_id')
        car = get_object_or_404(Car, id=car_id)

        # Parse start_date and end_date
        try:
            start_date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            return render(request, 'car/booking_form.html', {
                'car': car,
                'error_message': 'Invalid date format. Please use YYYY-MM-DD.'
            })

        # Validate dates
        if start_date >= end_date:
            return render(request, 'car/booking_form.html', {
                'car': car,
                'error_message': 'The end date must be later than the start date.'
            })

        # Check for overlapping bookings (exclude cancelled bookings)
        overlapping_bookings = Booking.objects.filter(
            car=car,
            start_date__lt=end_date,  # The booking starts before the requested end date
            end_date__gt=start_date,  # The booking ends after the requested start date
            status__in=['pending', 'verified', 'paid']  # Exclude cancelled bookings
        ).exists()

        if overlapping_bookings:
            # Get the overlapping booking details
            overlapping_booking = Booking.objects.filter(
                car=car,
                start_date__lt=end_date,
                end_date__gt=start_date,
                status__in=['pending', 'verified', 'paid']
            ).first()

            error_message = (
                f"This car is already booked from {overlapping_booking.start_date} "
                f"to {overlapping_booking.end_date}. Please choose different dates."
            )
            return render(request, 'car/booking_form.html', {
                'car': car,
                'error_message': error_message
            })

        # Capture latitude and longitude from the form
        try:
            latitude = float(request.POST.get('latitude'))
            longitude = float(request.POST.get('longitude'))
        except ValueError:
            return render(request, 'car/booking_form.html', {
                'car': car,
                'error_message': 'Invalid latitude or longitude.'
            })

        # Calculate the total amount based on the car price per day
        total_days = (end_date - start_date).days
        base_amount = car.price_per_km * total_days

        # Apply discount or surcharge based on booking difference
        current_date = timezone.now().date()
        booking_difference = (start_date - current_date).days
        if booking_difference >= 5:
            total_amount = base_amount * Decimal('0.9')  # 10% discount
        else:
            total_amount = base_amount * Decimal('1.05')  # 5% surcharge

        # Create the customer instance
        customer = Customer.objects.create(
            full_name=request.POST.get('billname'),
            email=request.POST.get('billemail'),
            phone=request.POST.get('billphone'),
            address=request.POST.get('billaddress'),
            license_image=request.FILES.get('license_image'),
            latitude=latitude,
            longitude=longitude
        )

        # Create the booking instance
        booking = Booking.objects.create(
            car=car,
            user=request.user,  # Assign the logged-in user to the booking
            customer=customer,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount
        )


        # Send an email notification to the user
        subject = "Car Booking Confirmation"
        message = f"""
        Dear {request.user.username},

        Your booking has been received successfully!

        Booking Details:
        - Car: {car.name}
        - Start Date: {start_date}
        - End Date: {end_date}
        - Total Amount: ${total_amount}

        Your booking is currently pending verification by the admin. 
        You will receive another notification once your booking is verified.

        Thank you for choosing our service!
        """

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [request.user.email],
            fail_silently=False,
        )

        return redirect('your_booking_list')
    
@login_required
def your_booking_list(request):
    # Fetch bookings for the logged-in user
    bookings = request.user.bookings.all()  # Use 'bookings' instead of 'booking_set'
    return render(request, 'car/useerbooking.html', {'bookings': bookings})

class BookingConfirmationView(LoginRequiredMixin, View):
    def get(self, request, booking_id):
        booking = Booking.objects.get(id=booking_id)
        return render(request, 'car/booking_confirmation.html', {
            'booking': booking,
            'formatted_amount': f"{booking.total_amount:,.2f}".replace(",", "")
        })

def logout_page(request):
    logout(request)
    return redirect('index')
# List all cars added by the logged-in admin
@login_required
def admin_car_list(request):
    cars = Car.objects.filter(admin=request.user)
    return render(request, 'car/manage_cars.html', {'cars': cars})

# Create a new car (Admin only)
class CarCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Car
    template_name = 'car/car_create.html'
    form_class = CarCreateForm
    success_url = reverse_lazy('car_create')

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to create a car.")
        return redirect('index')

    def form_valid(self, form):
        form.instance.admin = self.request.user
        return super().form_valid(form)

# Update an existing car (Admin only)
class CarUpdateView(LoginRequiredMixin, UpdateView):
    model = Car
    form_class = CarCreateForm
    template_name = 'car/car_create.html'
    success_url = reverse_lazy('admin_car_list')

# Delete a car (Admin only)
class CarDeleteView(LoginRequiredMixin, DeleteView):
    model = Car
    success_url = reverse_lazy('admin_car_list')

    def get_queryset(self):
        return Car.objects.filter(admin=self.request.user)




class CarListView(ListView):
    model = Car
    template_name = 'car/car_list.html'
    context_object_name = 'cars'

    def get_queryset(self):
        # Retrieve saved location from the session
        user_lat = self.request.session.get('saved_latitude')
        user_lon = self.request.session.get('saved_longitude')

        if user_lat is None or user_lon is None:
            return Car.objects.all()  # Return all cars if no location found in session

        try:
            # Ensure the latitude and longitude values are floats
            user_lat = float(user_lat)
            user_lon = float(user_lon)
        except ValueError:
            # If conversion fails, return all cars
            return Car.objects.all()

        cars = Car.objects.all()
        for car in cars:
            if car.latitude is not None and car.longitude is not None:
                car.distance = haversine(user_lat, user_lon, car.latitude, car.longitude)
            else:
                car.distance = None

        filtered_cars = [car for car in cars if car.distance is not None]
        return sorted(filtered_cars, key=lambda car: car.distance) if filtered_cars else cars

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add the user's latitude and longitude from the session to the context
        user_lat = self.request.session.get('saved_latitude')
        user_lon = self.request.session.get('saved_longitude')

        context['user_lat'] = user_lat
        context['user_lon'] = user_lon

        return context

    




def admin_car_list(request):
    # Get the logged-in user
    user = request.user
    cars = Car.objects.filter(admin=user)
    return render(request, 'car/manage_cars.html', {'cars': cars})


class LoginUserWithCreation(FormView):
    template_name = 'car/form.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        # Log the user in
        user = form.get_user()
        login(self.request, user)

        # Get latitude and longitude from the request
        lat = self.request.POST.get('lat')
        lon = self.request.POST.get('lon')

        if lat and lon:
            try:
                lat = float(lat)
                lon = float(lon)
                # Update or create UserProfile with latitude and longitude
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={'latitude': lat, 'longitude': lon}
                )
            except ValueError:
                pass  # Handle the case where lat/lon are not valid floats

        # Redirect based on user role (admin or regular user)
        if user.is_superuser:
            return redirect('admin_homepage')

        return redirect(self.success_url)

    def form_invalid(self, form):
        # Handle invalid form submission
        return self.render_to_response(self.get_context_data(form=form))


class RegisterView(FormView):
    template_name = 'car/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Account successfully created')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'There was an error with your registration')
        return super().form_invalid(form)

class AboutUsView(View):
    def get(self, request):
        return render(request, 'car/about_us.html')
    
class MapView(View):
    def get(self, request):
        return render(request, 'car/map.html')
    
class ContactUsView(FormView):
    template_name = 'car/contact_us.html'
    form_class = ContactForm
    success_url = '/contact/success/'
    
    def form_valid(self, form):
        return super().form_valid(form)

@login_required
def home(request):
    if request.user.is_superuser:
        # Redirect admin to a different homepage
        return redirect('admin_homepage')
    else:
        # Render the regular user homepage
        return render(request, 'car/index.html')  # Regular homepage for non-admin users

@login_required
def admin_homepage(request):
    # Get counts for cars, bookings, and users
    cars = Car.objects.filter(admin=request.user)
    bookings = Booking.objects.filter(user=request.user)
    users = User.objects.all()

    # Pass the logged-in admin's full name
    return render(request, 'admin_homepage.html', {
        'cars': cars,
        'bookings': bookings,
        'users': users,
        'admin_name': request.user.get_full_name()  # Ensure admin's name is passed
    })

@login_required
def manage_bookings(request):
    bookings = Booking.objects.all()  # You can filter based on criteria
    return render(request, 'manage_bookings.html', {'bookings': bookings})


def admin_bookings(request):
    if not request.user.is_authenticated:
        return redirect('login')  # Redirect to login page if not authenticated
    user = request.user
    bookings = Booking.objects.filter(car__admin=user).order_by('-start_date')
    return render(request, 'car/admin_bookings.html', {'bookings': bookings})

def admin_verify_booking(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    booking = get_object_or_404(Booking, id=booking_id)
    if booking.car.admin != request.user:
        messages.error(request, "You do not have permission to verify this booking.")
        return redirect('admin_bookings')

    action = request.POST.get('action', 'verify')

    if booking.status == 'pending':
        if action == 'verify':
            booking.status = 'verified'
            booking.save()

            subject = "Booking Verified - Your Car Rental Request"
            message = f"""
            Dear {booking.customer.full_name},

            Your booking has been verified successfully!

            Booking Details:
            - Car: {booking.car.name}
            - Start Date: {booking.start_date}
            - End Date: {booking.end_date}
            - Total Amount: ${booking.total_amount}

            You can now proceed with the payment.

            Thank you for choosing our service!
            """

        elif action == 'reject':
            booking.status = 'cancelled'
            booking.notification = "Your booking has been cancelled by the admin."
            booking.save()

            subject = "Booking Rejected - Car Rental Request"
            message = f"""
            Dear {booking.customer.full_name},

            Unfortunately, your booking request has been rejected.

            Booking Details:
            - Car: {booking.car.name}
            - Start Date: {booking.start_date}
            - End Date: {booking.end_date}

            If you have any questions, please contact our support team.

            Thank you for your understanding.
            """

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [booking.customer.email],  
                fail_silently=False,
            )
            logger.info(f"Email sent to {booking.customer.email} for booking {booking.id}")
        except Exception as e:
            logger.error(f"Failed to send email to {booking.customer.email} for booking {booking.id}: {e}")

        messages.success(request, f"Booking {booking.id} status updated and notification email sent.")

    else:
        messages.error(request, "Only pending bookings can be verified or rejected.")

    return redirect('admin_bookings')
def admin_reject_booking(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    booking = get_object_or_404(Booking, id=booking_id)
    if booking.car.admin != request.user:
        messages.error(request, "You do not have permission to reject this booking.")
        return redirect('admin_bookings')

    if booking.status == 'pending':
        booking.status = 'cancelled'
        booking.notification = "Your booking has been cancelled by the admin."
        booking.save()

        subject = "Booking Rejected - Car Rental Request"
        message = f"""
        Dear {booking.customer.full_name},

        Unfortunately, your booking request has been rejected.

        Booking Details:
        - Car: {booking.car.name}
        - Start Date: {booking.start_date}
        - End Date: {booking.end_date}

        If you have any questions, please contact our support team.

        Thank you for your understanding.
        """

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [booking.customer.email],
                fail_silently=False,
            )
            logger.info(f"Email sent to {booking.customer.email} for booking {booking.id}")
        except Exception as e:
            logger.error(f"Failed to send email to {booking.customer.email} for booking {booking.id}: {e}")

        messages.success(request, f"Booking {booking.id} has been cancelled and notification email sent.")
    else:
        messages.error(request, "Only pending bookings can be rejected.")

    return redirect('admin_bookings')

def admin_booking_delete(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    booking = get_object_or_404(Booking, id=booking_id)

    if booking.car.admin != request.user:
        messages.error(request, "You do not have permission to delete this booking.")
        return redirect('admin_bookings')

    booking.delete()
    messages.success(request, f"Booking {booking_id} has been deleted successfully.")

    return redirect('admin_bookings')

def admin_booking_detail(request, booking_id):
    # Get the specific booking by ID
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'car/admin_booking_detail.html', {'booking': booking})

class AcceptBookingView(View):
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        booking.status = 'Accepted'
        booking.save()
        return redirect('admin_booking_detail', booking_id=booking.id)

class CancelBookingView(View):
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        booking.status = 'Cancelled'
        booking.save()
        return redirect('admin_booking_detail', booking_id=booking.id)

# def admin_booking_delete(request, booking_id):
#     # Get the specific booking by ID
#     booking = get_object_or_404(Booking, id=booking_id)
    
#     if request.method == 'POST':
#         booking.delete()
#         return redirect('admin_bookings')  # Redirect to bookings list after deletion
    
#     return render(request, 'car/admin_booking_delete.html', {'booking': booking})

@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('admin_homepage')
        else:
            messages.error(request, 'Please correct the error below.')

    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'car/password_change.html', {'form': form})

@login_required
def admin_settings(request):
    return render(request, 'car/admin_settings.html')


def car_details(request, car_id):
    """
    View to display car details, including price per km, location, and booking option.
    """
    car = get_object_or_404(Car, id=car_id)

    # Retrieve saved location from the session
    user_lat = request.session.get('saved_latitude')
    user_lon = request.session.get('saved_longitude')

    # Check if the location is set and valid
    if user_lat is None or user_lon is None:
        print("Saved location not found in session.")
        return render(request, 'car/car_details.html', {'car': car, 'distance': None})

    try:
        # Ensure the session values are floats
        user_lat = float(user_lat)
        user_lon = float(user_lon)
    except ValueError:
        print("Invalid latitude or longitude format in session.")
        return render(request, 'car/car_details.html', {'car': car, 'distance': None})

    # Calculate the distance if both car and user have valid location data
    if car.latitude is not None and car.longitude is not None:
        try:
            distance = haversine(user_lat, user_lon, car.latitude, car.longitude)
        except TypeError:
            print("Invalid data types for distance calculation.")
            distance = None
    else:
        distance = None
        print(f"Car {car.name} has no location data")

    return render(request, 'car/car_details.html', {'car': car, 'distance': distance})



def car_search(request):
    query = request.GET.get('search', '')  # Get search query from URL parameters
    cars = Car.objects.all()

    if query:
        cars = cars.filter(
            name__icontains=query
        )  # Searching by car name (case-insensitive)

    return render(request, 'car/found_cars.html', {'car_list': cars})




@csrf_exempt
def save_location(request):
    if request.method == "POST" and request.user.is_authenticated:
        data = json.loads(request.body)
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_profile.latitude = data.get("latitude")
        user_profile.longitude = data.get("longitude")
        user_profile.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


@csrf_exempt  # You can remove CSRF protection or use CSRF tokens as needed
def save_lat_long(request):
    if request.method == 'POST':
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            # Check if latitude and longitude are valid
            if latitude is None or longitude is None:
                return JsonResponse({'message': 'Latitude and Longitude are required.'}, status=400)
            
            # Save latitude and longitude to the session
            request.session['saved_latitude'] = latitude
            request.session['saved_longitude'] = longitude

            # Optionally, save the location to the database
            location = lat_long.objects.create(latitude=latitude, longitude=longitude)
            
            # Return success response
            return JsonResponse({'message': 'Location saved successfully!'})
        
        except ValueError:
            return JsonResponse({'message': 'Invalid data format.'}, status=400)
    
    return JsonResponse({'message': 'Invalid request method.'}, status=405)


def get_nearby_cars(request):
    # Fetch the user's location from session
    user_lat = request.session.get('saved_latitude')
    user_lon = request.session.get('saved_longitude')

    # Handle missing location
    if user_lat is None or user_lon is None:
        return JsonResponse({"error": "User location not found in session."}, status=400)

    # Get all cars
    cars = Car.objects.all()
    
    # List to store cars with their distance from the user
    car_list = []
    
    # Function to calculate Euclidean distance (scaled by factor for practical distance)
    def calculate_distance(lat1, lon1, lat2, lon2):
        return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)

    # Calculate the distance for each car and add to the list
    for car in cars:
        # Scaling the latitude and longitude to reduce values (optional, for practical range)
        distance = calculate_distance(float(user_lat), float(user_lon), car.latitude, car.longitude)
        
        car_data = {
            "id": car.id,
            "name": car.name,
            "car_type": car.car_type,
            "seating_capacity": car.seating_capacity,
            "fuel_type": car.fuel_type,
            "price_per_km": car.price_per_km,
            "is_available": car.is_available,
            "image_url": car.image.url if car.image else "",
            "distance_km": round(distance, 2)  # Add distance in "unit"
        }
        
        car_list.append(car_data)

    # Sort the cars by distance (ascending)
    nearest_cars = sorted(car_list, key=lambda x: x["distance_km"])[:5]

    return JsonResponse({"cars": nearest_cars})

@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)
        token = data.get("token")
        amount = data.get("amount")

        headers = {
            "Authorization": f"Key {settings.KHALTI_SECRET_KEY}"
        }
        payload = {
            "token": token,
            "amount": amount
        }
        
        response = requests.post("https://khalti.com/api/v2/payment/verify/", data=payload, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            return JsonResponse({"message": "Payment Successful", "data": response_data})
        else:
            return JsonResponse({"message": "Payment Verification Failed", "data": response_data}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

def landing_page(request):
    return render(request, 'car/land.html')


def process_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != 'verified':
        messages.error(request, "You can only pay for verified bookings.")
        return redirect('your_booking_list')

    # Simulate payment processing (replace with actual payment gateway integration)
    booking.status = 'paid'
    booking.save()

    messages.success(request, "Payment successful!")
    return redirect('your_booking_list')

def user_cancel_booking(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Redirect to login page if not authenticated
    
    # Fetch the booking object
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if the booking can be cancelled (e.g., only pending or verified bookings can be cancelled)
    if booking.status in ['pending', 'verified']:
        booking.status = 'cancelled'
        booking.notification = "You have cancelled this booking."
        booking.save()
        messages.success(request, f"Booking {booking.id} has been cancelled.")
    else:
        messages.error(request, "This booking cannot be cancelled.")
    
    return redirect('your_booking_list')

def user_delete_booking(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Allow deletion only for pending or cancelled bookings
    if booking.status in ['pending', 'cancelled']:
        booking.delete()
        messages.success(request, f"Booking {booking.id} has been deleted.")
    else:
        messages.error(request, "Only pending or cancelled bookings can be deleted.")
    
    return redirect('your_booking_list')