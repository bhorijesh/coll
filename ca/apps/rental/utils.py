import math
from math import radians, sin, cos, sqrt, atan2,asin
from .models import *
from django.http import JsonResponse
from geopy.distance import geodesic  


def get_nearby_cars(user_lat, user_lon, radius_km=10):
    nearby_cars = []
    for car in Car.objects.all():
        distance = haversine(user_lat, user_lon, car.latitude, car.longitude)
        if distance <= radius_km:
            nearby_cars.append(car)
            return nearby_cars

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of the Earth in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# Haversine formula implementation
def calculate_haversine_distance(from_lat, from_lon, to_lat, to_lon):
    # Convert degrees to radians
    from_lat = math.radians(from_lat)
    from_lon = math.radians(from_lon)
    to_lat = math.radians(to_lat)
    to_lon = math.radians(to_lon)
    
    # Haversine formula
    dlat = to_lat - from_lat
    dlon = to_lon - from_lon
    a = math.sin(dlat / 2) ** 2 + math.cos(from_lat) * math.cos(to_lat) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Radius of the Earth in kilometers
    radius = 6371
    
    # Distance in kilometers
    distance = radius * c
    return distance


# For AJAX requests to calculate the distance without submitting the form
def calculate_distance(request):
    from_lat = float(request.GET.get('from_lat'))
    from_lon = float(request.GET.get('from_lon'))
    to_lat = float(request.GET.get('to_lat'))
    to_lon = float(request.GET.get('to_lon'))
    
    # Haversine formula to calculate the distance
    distance = calculate_haversine_distance(from_lat, from_lon, to_lat, to_lon)
    
    return JsonResponse({'distance': distance})


def get_nearest_car(user_lat, user_lon, min_distance=5, max_distance=10):
    """
    Get the nearest car within a specified distance range (min_distance to max_distance).
    Returns the car if found, otherwise returns None.
    """
    # Get all cars from the database
    cars = Car.objects.all()

    nearest_car = None
    closest_distance = float('inf')  # Start with a very large number

    # Loop through all cars and find the closest one
    for car in cars:
        # Assuming the car model has lat and lon fields
        car_lat = car.latitude
        car_lon = car.longitude

        # Calculate the distance using the haversine formula
        distance = haversine(user_lat, user_lon, car_lat, car_lon)

        # If the car is within the min_distance and max_distance range and is closer than the previous one
        if min_distance <= distance <= max_distance and distance < closest_distance:
            closest_distance = distance
            nearest_car = car

    return nearest_car

def calculate_distance(user_location, car_location):
    """Returns the distance in km between user and car, or None if locations are invalid."""
    if user_location and car_location:
        return geodesic(user_location, car_location).km
    return None