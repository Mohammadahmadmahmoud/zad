import re
from django import forms
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm


import re
from django import forms
from django.contrib.auth.models import User

class EmailRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        label="الاسم الكامل",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الكامل'})
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    phone = forms.CharField(
        label="رقم الهاتف الإماراتي",
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0501234567'})
    )
    
    EMIRATES_CHOICES = [
        ('', 'اختر الإمارة المفضلة...'),
        ('Dubai', 'دبي (Dubai)'),
        ('Sharjah', 'الشارقة (Sharjah)'),
        ('Abu Dhabi', 'أبوظبي (Abu Dhabi)'),
        ('Abu Dhabi - Al Dhafra', 'أبوظبي - المنطقة الغربية / الظفرة (Al Dhafra)'),
        ('Ajman', 'عجمان (Ajman)'),
        ('Ras Al Khaimah', 'رأس الخيمة (Ras Al Khaimah)'),
        ('Fujairah', 'الفجيرة (Fujairah)'),
        ('Umm Al Quwain', 'أم القيوين (Umm Al Quwain)'),
    ]
    
    emirate = forms.ChoiceField(
        label="الإمارة",
        choices=EMIRATES_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    password1 = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'})
    )
    password2 = forms.CharField(
        label="تأكيد كلمة المرور",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'email']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        uae_phone_pattern = r'^(\+971|0)?5[024568]\d{7}$'
        if not re.match(uae_phone_pattern, phone):
            raise forms.ValidationError("يرجى إدخال رقم هاتف إماراتي صحيح (مثال: 0501234567).")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("هذا البريد الإلكتروني مسجل مسبقاً.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("كلمتا المرور غير متطابقتين.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            user.profile.phone = self.cleaned_data['phone']
            user.profile.emirate = self.cleaned_data.get('emirate', '')
            user.profile.save()
        return user

class CheckoutForm(forms.ModelForm):
    full_name = forms.CharField(
        label="الاسم الكامل",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الكامل'})
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    phone = forms.CharField(
        label="رقم الهاتف الإماراتي",
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0501234567'})
    )
    
    EMIRATES_CHOICES = [
        ('', 'اختر الإمارة...'),
        ('Dubai', 'دبي (Dubai) - الشحن 30 درهم'),
        ('Sharjah', 'الشارقة (Sharjah) - الشحن 30 درهم'),
        ('Abu Dhabi', 'أبوظبي (Abu Dhabi) - الشحن 30 درهم'),
        ('Abu Dhabi - Al Dhafra', 'أبوظبي - المنطقة الشرقية / العين (Al ِAin) - الشحن 30 درهم'),
        ('Abu Dhabi - Al Dhafra', 'أبوظبي - المنطقة الغربية / الظفرة (Al Dhafra) - الشحن 50 درهم'),
        ('Ajman', 'عجمان (Ajman) - الشحن 30 درهم'),
        ('Ras Al Khaimah', 'رأس الخيمة (Ras Al Khaimah) - الشحن 30 درهم'),
        ('Fujairah', 'الفجيرة (Fujairah) - الشحن 30 درهم'),
        ('Umm Al Quwain', 'أم القيوين (Umm Al Quwain) - الشحن 30 درهم'),
    ]
    
    emirate = forms.ChoiceField(
        label="الإمارة",
        choices=EMIRATES_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    address = forms.CharField(
        label="عنوان السكن بالتفصيل",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'المنطقة، الشارع، رقم المبنى أو الفلل، توضيح إضافي'})
    )

    class Meta:
        model = Order
        fields = ['full_name', 'email', 'phone', 'emirate', 'address']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # التحقق الصارم من صحة رقم الهاتف الإماراتي
        uae_phone_pattern = r'^(\+971|0)?5[024568]\d{7}$'
        if not re.match(uae_phone_pattern, phone):
            raise forms.ValidationError("يرجى إدخال رقم هاتف إماراتي صحيح (مثال: 0501234567).")
        return phone
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name_ar', 'name_en']
        widgets = {
            'name_ar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم التصنيف بالعربي'}),
            'name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم التصنيف بالإنجليزي'}),
        }
        
class CustomProductForm(forms.ModelForm):
    class Meta :

        model = Product
        fields = "__all__"

class CustomProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # تأكد أن هذه الأسماء مطابقة تماماً للأسماء الموجودة في models.py لديك
        fields = ['category', 'name_ar', 'name_en', 'description_ar', 'description_en', 'price', 'discount_price', 'image', 'is_featured', 'stock']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name_ar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المنتج بالعربي'}),
            'name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المنتج  بالانجليزي'}),
            'description_ar': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'وصف المنتج'}),
            'description_en': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'وصف المنتج بالانجليزي'}),

            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }