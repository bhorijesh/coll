from django.contrib import admin
from django.contrib.auth.models import User
from .models import Car, Customer, Booking, UserProfile
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path

class UserProfileInline(admin.StackedInline):  # or admin.TabularInline
    model = UserProfile
    can_delete = False  # Optional: to prevent deletion of UserProfile from inline
    verbose_name_plural = 'User Profile'

class CustomAdminSite(admin.AdminSite):
    site_header = "Car Booking Admin"
    site_title = "Car Booking Admin Portal"
    index_title = "Welcome to Car Booking Admin"

    # Overriding the index method to customize the homepage
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('home/', self.admin_homepage),
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

# Register the custom admin site
admin_site = CustomAdminSite(name='custom_admin')
admin_site.register(Car)
admin_site.register(Customer)
admin_site.register(Booking)

# Register the User model with the inline UserProfile
class UserAdmin(admin.ModelAdmin):
    inlines = [UserProfileInline]

# Unregister the default User admin and register your custom User admin with the inline
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
