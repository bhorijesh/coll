from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import *

urlpatterns = [
    path('', views.index.as_view(), name='index'),
    path('admin/home/', views.admin_homepage, name='admin_homepage'),
    path('login/', views.LoginUserWithCreation.as_view(), name='login'),
    path('car/create/', views.CarCreateView.as_view(), name='car_create'),
    path('booking/', views.BookingView.as_view(), name='booking_view'),
    path('your-bookings/', views.your_booking_list, name='your_booking_list'),
    path('booking/confirmation/<int:booking_id>/', views.BookingConfirmationView.as_view(), name='booking_confirmation'),
    path('calculate_distance/', views.calculate_distance, name='calculate_distance'),
    path('cars/', views.CarListView.as_view(), name='car_list'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('about/', views.AboutUsView.as_view(), name='about_us'),
    path('contact/', views.ContactUsView.as_view(), name='contact_us'),
    path('contact/success/', views.ContactUsView.as_view(), name='contact_success'),
    path('manage_cars/', views.admin_car_list, name='admin_car_list'), 
    path('logout/', views.logout_page, name='logout_page'),
    path('car/edit/<int:pk>/', views.CarUpdateView.as_view(), name='car_update'),
    path('car/delete/<int:pk>/', views.CarDeleteView.as_view(), name='car_delete'),
    path('bookings/', views.admin_bookings, name='admin_bookings'),
    path('bookings/<int:booking_id>/', views.admin_booking_detail, name='admin_booking_detail'),
    path('bookings/delete/<int:booking_id>/', views.admin_booking_delete, name='admin_booking_delete'),
    path('settings/', views.admin_settings, name='admin_settings'),
    path('change-password/', views.password_change, name='admin_password_change'),
    path('car/<int:car_id>/', car_details, name='car_details'),
    path('cars/search', car_search, name='car_search'),
    path('save-location/', views.save_lat_long, name='save_lat_long'),
    path('nearby-cars/', views.nearby_cars, name='nearby_cars'),
    path('api/get_nearby_cars/', get_nearby_cars, name='get_nearby_cars'),
    path('save-location/', save_location, name='save_location'),
    path('booking/<int:booking_id>/accept/', views.AcceptBookingView.as_view(), name='accept_booking'),
    path('booking/<int:booking_id>/cancel/', views.CancelBookingView.as_view(), name='cancel_booking'),
    path("verify-payment/", verify_payment, name="verify_payment"),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
