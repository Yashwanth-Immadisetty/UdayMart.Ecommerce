from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Review, CustomerProfile
from .services import PhoneNumberError, normalize_phone


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True)
    whatsapp_opt_in = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already uses this email address.')
        return email

    def clean_phone(self):
        try:
            phone = normalize_phone(self.cleaned_data['phone'])
        except PhoneNumberError as error:
            raise forms.ValidationError(str(error))
        if CustomerProfile.objects.filter(phone=phone).exists():
            raise forms.ValidationError('An account already uses this mobile number.')
        return phone


class OTPLoginStartForm(forms.Form):
    identifier = forms.CharField(
        max_length=120,
        label='Username, email, or mobile number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username, email, or mobile number',
            'autocomplete': 'username',
        }),
    )


class OTPVerificationForm(forms.Form):
    email_code = forms.CharField(
        required=False,
        min_length=6,
        max_length=6,
        label='Email code',
        widget=forms.TextInput(attrs={
            'class': 'form-control otp-code-input',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'placeholder': '6-digit email code',
        }),
    )
    phone_code = forms.CharField(
        required=False,
        min_length=4,
        max_length=10,
        label='SMS code',
        widget=forms.TextInput(attrs={
            'class': 'form-control otp-code-input',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'placeholder': 'SMS code',
        }),
    )

    def clean_email_code(self):
        code = self.cleaned_data['email_code'].strip()
        if not code:
            return code
        if not code.isdigit():
            raise forms.ValidationError('Enter the numeric code sent to your email.')
        return code

    def clean_phone_code(self):
        code = self.cleaned_data['phone_code'].strip()
        if not code:
            return code
        if not code.isdigit():
            raise forms.ValidationError('Enter the numeric code sent by SMS.')
        return code


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ('COD', '💵 Cash on Delivery'),
        ('UPI', '📱 UPI Payment'),
        ('CARD', '💳 Credit / Debit Card'),
        ('NETBANKING', '🏦 Net Banking'),
    ]

    full_name = forms.CharField(max_length=200, label='Full Name')
    phone = forms.CharField(max_length=20, label='Phone Number')
    address_line1 = forms.CharField(max_length=300, label='Address Line 1')
    address_line2 = forms.CharField(max_length=300, required=False, label='Address Line 2 (Optional)')
    city = forms.CharField(max_length=100, label='City')
    state = forms.CharField(max_length=100, label='State')
    pincode = forms.CharField(max_length=10, label='PIN Code')
    location_latitude = forms.DecimalField(required=False, widget=forms.HiddenInput())
    location_longitude = forms.DecimalField(required=False, widget=forms.HiddenInput())
    location_accuracy = forms.DecimalField(required=False, widget=forms.HiddenInput())
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES, widget=forms.RadioSelect, label='Payment Method')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.RadioSelect, forms.HiddenInput)):
                field.widget.attrs.update({'class': 'form-control'})

    def clean_phone(self):
        try:
            return normalize_phone(self.cleaned_data['phone'])
        except PhoneNumberError as error:
            raise forms.ValidationError(str(error))

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('location_latitude')
        longitude = cleaned_data.get('location_longitude')
        accuracy = cleaned_data.get('location_accuracy')

        if (latitude is None) != (longitude is None):
            raise forms.ValidationError('Location data is incomplete. Please try sharing your location again.')
        if latitude is not None and not (-90 <= latitude <= 90):
            self.add_error('location_latitude', 'Invalid latitude.')
        if longitude is not None and not (-180 <= longitude <= 180):
            self.add_error('location_longitude', 'Invalid longitude.')
        if accuracy is not None and accuracy < 0:
            self.add_error('location_accuracy', 'Invalid location accuracy.')
        return cleaned_data


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Review title'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share your experience...'}),
        }
