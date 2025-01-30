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
import math
from .models import *
from .utils import *
from .forms import *

class index(ListView):
    model = Car
    template_name = 'car/index.html'
    context_object_name = 'car_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if the nearest car ID exists in the session
        nearest_car_id = self.request.session.get('nearest_car_id')
        if nearest_car_id:
            nearest_car = Car.objects.get(id=nearest_car_id)
            context['nearest_car'] = nearest_car

        return context

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

        start_date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d')
        total_days = (end_date - start_date).days
        
        # Calculate total amount based on the chosen pricing method
        if request.POST.get('pricing_method') == 'per_day':
            total_amount = car.price_per_km * total_days
        else: 
            distance = Decimal(calculate_haversine_distance(
                float(request.POST.get('fl_lat')),
                float(request.POST.get('fl_lon')),
                float(request.POST.get('tl_lat')),
                float(request.POST.get('tl_lon'))
            ))
            total_amount = distance * Decimal(car.price_per_km)  
        
        booking = Booking.objects.create(
            car=car,
            customer=customer,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
            from_location_lat=request.POST.get('fl_lat'),
            from_location_lon=request.POST.get('fl_lon'),
            to_location_lat=request.POST.get('tl_lat'),
            to_location_lon=request.POST.get('tl_lon')
        )
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

    def get_queryset(self):
        # Get the user's latitude and longitude from the GET request
        user_lat = self.request.GET.get('lat')
        user_lon = self.request.GET.get('lon')

        if user_lat and user_lon:
            user_lat = float(user_lat)
            user_lon = float(user_lon)

            # Get all cars from the database
            cars = Car.objects.all()

            # Calculate the distance for each car and add it as a new field on the car object
            for car in cars:
                car.distance = haversine(user_lat, user_lon, car.latitude, car.longitude)

            # Sort the cars by distance (nearest to farthest)
            return sorted(cars, key=lambda car: car.distance)
        else:
            # If no lat/lon provided, return all cars
            return Car.objects.all()

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
        login(self.request, form.get_user())

        # Check if the logged-in user is an admin
        if self.request.user.is_superuser:
            # Redirect to the admin panel
            return redirect('admin_homepage')

        # Get user's location after successful login
        user_lat = self.request.GET.get('lat')
        user_lon = self.request.GET.get('lon')
        
        if user_lat and user_lon:
            user_lat = float(user_lat)
            user_lon = float(user_lon)

            # Get all cars from the database
            cars = Car.objects.all()

            # Calculate distances and add them to the car objects
            for car in cars:
                car.distance = haversine(user_lat, user_lon, car.latitude, car.longitude)

            # Sort the cars by distance (nearest to farthest)
            sorted_cars = sorted(cars, key=lambda car: car.distance)

            nearest_car = sorted_cars[0] if sorted_cars else None  # Nearest car
            return render(self.request, 'car/car_list.html', {'car_list': sorted_cars, 'nearest_car': nearest_car})

        # Default redirection to the regular homepage if no location is provided
        return super().form_valid(form)


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
    return render(request, 'car/car_details.html', {'car': car})

def car_search(request):
    query = request.GET.get('search', '')  # Get search query from URL parameters
    cars = Car.objects.all()

    if query:
        cars = cars.filter(
            name__icontains=query
        )  # Searching by car name (case-insensitive)

    return render(request, 'car/found_cars.html', {'car_list': cars})