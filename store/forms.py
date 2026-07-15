from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Review, Order


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ('COD', '💵 Cash on Delivery'),
        ('UPI', '📱 UPI Payment'),
        ('CARD', '💳 Credit / Debit Card'),
        ('NETBANKING', '🏦 Net Banking'),
    ]

    full_name = forms.CharField(max_length=200, label='Full Name')
    phone = forms.CharField(max_length=15, label='Phone Number')
    address_line1 = forms.CharField(max_length=300, label='Address Line 1')
    address_line2 = forms.CharField(max_length=300, required=False, label='Address Line 2 (Optional)')
    city = forms.CharField(max_length=100, label='City')
    state = forms.CharField(max_length=100, label='State')
    pincode = forms.CharField(max_length=10, label='PIN Code')
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES, widget=forms.RadioSelect, label='Payment Method')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.update({'class': 'form-control'})


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
