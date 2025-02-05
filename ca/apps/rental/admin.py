from django.contrib import admin
from django.contrib.auth.models import User
from .models import Car, Customer, Booking, UserProfile
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path
from django.contrib import messages

# Inline for UserProfile
class UserProfileInline(admin.StackedInline):  # or admin.TabularInline
    model = UserProfile
    can_delete = False  # Optional: to prevent deletion of UserProfile from inline
    verbose_name_plural = 'User Profile'

# Custom Admin Site
class CustomAdminSite(admin.AdminSite):
    site_header = "Car Booking Admin"
    site_title = "Car Booking Admin Portal"
    index_title = "Welcome to Car Booking Admin"

    # Overriding the index method to customize the homepage
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('home/', self.admin_homepage, name='admin_homepage'),
            path('bookings/', self.admin_bookings, name='admin_bookings'),
            path('bookings/<int:booking_id>/verify/', self.admin_verify_booking, name='admin_verify_booking'),
            path('bookings/<int:booking_id>/delete/', self.admin_booking_delete, name='admin_booking_delete'),
        ]
        return custom_urls + urls

    def admin_homepage(self, request):
        # Query the total data for display
        cars = Car.objects.all()
        bookings = Booking.objects.all()
        users = User.objects.all()  # Assuming you want to show registered users from the User model
        
        # Fetch any admin specific data, if needed (you can pass a specific admin name)
        admin_name = request.user.username
        # Pass data to the template
        context = {
            'cars': cars,
            'bookings': bookings,
            'users': users,
            'admin_name': admin_name
        }
        return render(request, 'car/admin_homepage.html', context)

    def admin_bookings(self, request):
        if not request.user.is_authenticated:
            return redirect('login')  # Redirect to login page if not authenticated
        user = request.user
        bookings = Booking.objects.filter(car__admin=user).order_by('-start_date')
        return render(request, 'car/admin_bookings.html', {'bookings': bookings})

    def admin_verify_booking(self, request, booking_id):
        if not request.user.is_authenticated:
            return redirect('login')
        booking = get_object_or_404(Booking, id=booking_id)
        if booking.car.admin != request.user:
            messages.error(request, "You do not have permission to verify this booking.")
            return redirect('custom_admin:admin_bookings')
        if booking.status == 'pending':
            booking.status = 'verified'
            booking.save()
            messages.success(request, f"Booking {booking.id} has been verified.")
        else:
            messages.error(request, "Only pending bookings can be verified.")
        return redirect('custom_admin:admin_bookings')

    def admin_booking_delete(self, request, booking_id=None):
        if not request.user.is_authenticated:
            return redirect('login')
        
        booking = get_object_or_404(Booking, id=booking_id)
        if booking.car.admin != request.user:
            messages.error(request, "You do not have permission to delete this booking.")
            return redirect('custom_admin:admin_bookings')
        
        # Update the booking status to 'cancelled' and add a notification
        booking.status = 'cancelled'
        booking.notification = "Your booking has been cancelled by the admin."
        booking.save()
        
        messages.success(request, f"Booking {booking.id} has been cancelled.")
        return redirect('custom_admin:admin_bookings')

# Register the custom admin site
admin_site = CustomAdminSite(name='custom_admin')

# Register models with the custom admin site
admin_site.register(Car)
admin_site.register(Customer)

# Custom Booking Admin
class BookingAdmin(admin.ModelAdmin):
    list_display = ('customer', 'car', 'start_date', 'end_date', 'total_amount', 'status')
    list_filter = ('status',)
    actions = ['mark_as_verified']

    def mark_as_verified(self, request, queryset):
        # Update selected bookings to 'verified' status
        queryset.update(status='verified')
    mark_as_verified.short_description = "Mark selected bookings as verified"

# Register Booking with the custom admin site
admin_site.register(Booking, BookingAdmin)

# Register the User model with the inline UserProfile
class UserAdmin(admin.ModelAdmin):
    inlines = [UserProfileInline]

# Unregister the default User admin and register your custom User admin with the inline
admin.site.unregister(User)
admin.site.register(User, UserAdmin)