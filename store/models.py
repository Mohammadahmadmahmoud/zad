from django.db import models
from django.contrib.auth.models import User
import random
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.email}"

# دالة لإنشاء بروفايل تلقائياً فور تسجيل حساب جديد
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, surtout=False, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class Category(models.Model):
    name_ar = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="صورة التصنيف")
    def __str__(self):
        return f"{self.name_ar} / {self.name_en}"

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name_ar = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    description_ar = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2) # السعر الاصلي بالدرهم
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # سعر الخصم إن وجد
    image = models.ImageField(upload_to='products/')
    is_featured = models.BooleanField(default=False) # للعرض في السلايدر المضيء
    stock = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)    
    # هل المنتج يُباع بالوزن؟ (أعشاب، مطحون، إلخ)
    is_sold_by_weight = models.BooleanField(default=False)   
    # أقل كمية مسموح شرائها بالوزن (مثلا 0.050 كجم أي 50 جرام)
    minimum_weight = models.DecimalField(max_digits=6, decimal_places=3, default=0.050)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name_ar

class Order(models.Model):
    EMIRATES_CHOICES = [
        ('Dubai', 'دبي / Dubai'),
        ('Abu Dhabi - City', 'أبوظبي (المدينة) / Abu Dhabi City'),
        ('Abu Dhabi - Al Dhafra', 'أبوظبي (المنطقة الغربية - الظفرة) / Al Dhafra Region'),
        ('Sharjah', 'الشارقة / Sharjah'),
        ('Ajman', 'عجمان / Ajman'),
        ('Umm Al Quwain', 'أم القيوين / Umm Al Quwain'),
        ('Ras Al Khaimah', 'رأس الخيمة / Ras Al Khaimah'),
        ('Fujairah', 'الفجيرة / Fujairah'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'قيد المعالجة / Pending'),
        ('Shipped', 'تم الشحن / Shipped'),
        ('Delivered', 'تم التوصيل / Delivered'),
        ('Delivered', 'تم الارجاع / Not Delivered'),
    ]
    invoice_printed = models.BooleanField(default=False)
    tracking_number = models.CharField(max_length=20, unique=True, blank=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=15) # رقم إماراتي
    emirate = models.CharField(max_length=50, choices=EMIRATES_CHOICES)
    address = models.TextField()
    
    total_products_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_method = models.CharField(max_length=20, default='Cash on Delivery (COD)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = 'ZAD-' + ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=8))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.tracking_number} - {self.full_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) # السعر وقت الشراء

    def __str__(self):
        return f"{self.quantity} x {self.product.name_ar if self.product else 'Deleted'}"

class Expense(models.Model):
    title_ar = models.CharField(max_length=200, verbose_name="عنوان المصروف (عربي)")
    title_en = models.CharField(max_length=200, verbose_name="عنوان المصروف (إنجليزي)", blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ (AED)")
    category_ar = models.CharField(max_length=100, default="تشغيلي", verbose_name="التصنيف (عربي)")
    category_en = models.CharField(max_length=100, default="Operational", verbose_name="التصنيف (إنجليزي)", blank=True, null=True)
    date = models.DateField(auto_now_add=True, verbose_name="التاريخ")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")

    def __str__(self):
        return f"{self.title_ar} - {self.amount} AED"