from django import forms
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class authForm(forms.ModelForm):
    class Meta :
        model = User
        fields = ['username', 'password']
        
        
class RegisterForm(UserCreationForm):
    is_admin = forms.BooleanField(required=False, label="Register as Admin")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'is_admin']

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data['is_admin']:
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = False
        if commit:
            user.save()
        return user
    
class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)

class CarCreateForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ['name', 'year', 'fuel_type', 'seating_capacity', 'price_per_km', 'is_available', 'image', 'latitude', 'longitude']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter car model'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter year'}),
            'fuel_type': forms.Select(attrs={'class': 'form-control'}),
            'seating_capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Seats'}),
            'price_per_km': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price per Day'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    price_per_km = forms.DecimalField(label="Price per Day", widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price per day'}))
    latitude = forms.FloatField()
    longitude = forms.FloatField()

class LocationForm(forms.Form):
    latitude = forms.DecimalField(max_digits=9, decimal_places=6, label="Latitude")
    longitude = forms.DecimalField(max_digits=9, decimal_places=6, label="Longitude")