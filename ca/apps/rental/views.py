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
from .utils import *
from .forms import *
from django.conf import settings

class index(ListView):
    model = Car
    template_name = 'car/index.html'
    context_object_name = 'car_list'

class BookingView(LoginRequiredMixin, View):
    def get(self, request):
        car_id = request.GET.get('car_id')  # Fetch car_id from query parameters
        if not car_id:
            return redirect('home')  # Redirect if no car_id is provided

        car = get_object_or_404(Car, id=car_id)
        return render(request, 'car/booking_form.html', {'car': car})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        car_id = request.POST.get('car_id')
        car = Car.objects.get(id=car_id)  # Fetch the selected car

        customer = Customer.objects.create(
            full_name=request.POST.get('billname'),
            email=request.POST.get('billemail'),
            phone=request.POST.get('billphone'),
            address=request.POST.get('billaddress')
        )

        # Parse start and end dates from the form
        start_date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d')

        # Calculate total days for the booking
        total_days = (end_date - start_date).days

        if total_days < 1:
            # Ensure that the end date is after the start date
            return render(request, 'car/booking_form.html', {
                'car': car, 
                'error_message': 'The end date must be later than the start date.'
            })

        # Calculate the total amount based on the number of days
        total_amount = car.price_per_km * total_days

        # Create the booking instance
        booking = Booking.objects.create(
            car=car,
            customer=customer,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
        )

        # Redirect to booking confirmation page with the booking ID
        return redirect('booking_confirmation', booking_id=booking.id)





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
    context_object_name = 'cars'  # Use this context variable in your template

    def get_queryset(self):
        # Retrieve saved location from the session
        user_lat = self.request.session.get('saved_latitude')
        user_lon = self.request.session.get('saved_longitude')

        # Check if the saved location exists in the session
        if user_lat is None or user_lon is None:
            print("Saved location not found in session.")
            return Car.objects.all()  # Return all cars if location is missing

        try:
            # Ensure the latitude and longitude values are floats
            user_lat = float(user_lat)
            user_lon = float(user_lon)
        except ValueError:
            # If conversion fails, return all cars
            print("Invalid latitude or longitude format in session.")
            return Car.objects.all()

        # Get all cars from the database
        cars = Car.objects.all()

        # Add a distance attribute to each car based on the saved location
        for car in cars:
            if car.latitude is not None and car.longitude is not None:
                # Calculate distance only if the car has location data
                car.distance = haversine(user_lat, user_lon, car.latitude, car.longitude)
            else:
                # No distance for cars with no location data
                car.distance = None
                print(f"Car {car.name} has no location data")

        # Exclude cars with None distance and sort by distance (nearest first)
        filtered_cars = [car for car in cars if car.distance is not None]

        if not filtered_cars:
            print("No cars with valid locations found")

        # Return sorted cars by distance (if any valid location data) or all cars if no valid data
        return sorted(filtered_cars, key=lambda car: car.distance) if filtered_cars else cars




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
    user = request.user
    bookings = Booking.objects.filter(car__admin=user)
    return render(request, 'car/admin_bookings.html', {'bookings': bookings})

def admin_booking_detail(request, booking_id):
    # Get the specific booking by ID
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'car/admin_booking_detail.html', {'booking': booking})

def admin_booking_delete(request, booking_id):
    # Get the specific booking by ID
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        booking.delete()
        return redirect('admin_bookings')  # Redirect to bookings list after deletion
    
    return render(request, 'car/admin_booking_delete.html', {'booking': booking})

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
