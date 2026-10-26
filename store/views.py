from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import user_passes_test
from .models import Product, Order, OrderItem, Category, Expense
from .forms import *
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import requests
from django.db.models import Sum, Q
from django.contrib import messages
from decimal import Decimal
import uuid 
from django.utils import translation
from django.core.cache import cache  # استيراد نظام التخزين المؤقت للذاكرة
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
import stripe
from django.conf import settings
import io
from django.core.mail import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

stripe.api_key = settings.STRIPE_SECRET_KEY

def change_language(request, lang_code):
    if lang_code in ['ar', 'en']:
        request.session['lang'] = lang_code
        translation.activate(lang_code)
        
    referer_url = request.META.get('HTTP_REFERER', '/')
    response = redirect(referer_url)
    response.set_cookie('django_language', lang_code)
    return response

def register_view(request):
    if request.method == 'POST':
        form = EmailRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home_view')
    else:
        form = EmailRegistrationForm()
    return render(request, 'register.html', {'form': form, 'lang': request.GET.get('lang', 'ar')})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home_view')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form, 'lang': request.GET.get('lang', 'ar')})

def is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

# 🚀 تحسين الصفحة الرئيسية باستخدام التخزين المؤقت (Memory Caching) لمنع الضغط على قاعدة البيانات
def home_view(request):
    lang = request.session.get('lang', request.COOKIES.get('django_language', 'ar'))
    
    # محاولة جلب المنتجات المميزة والتصنيفات من الذاكرة المؤقتة (تجنب الضغط العالي)
    cache_key = f'home_page_data_{lang}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        featured_products = cached_data['featured_products']
        categories = cached_data['categories']
    else:
        # جلب محسّن مع استعلامات سريعة
        featured_products = list(Product.objects.filter(discount_price__isnull=False).select_related('category')[:6])
        categories = list(Category.objects.all())
        
        # تخزين البيانات في الذاكرة لمدة 15 دقائق (900 ثانية)
        cache.set(cache_key, {'featured_products': featured_products, 'categories': categories}, 900)
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'lang': lang,
    }
    return render(request, 'home.html', context)

def product_detail(request, pk):
    # استخدام cache منفصل لكل منتج لسرعة التحميل الفائق
    cache_key = f'product_detail_{pk}'
    product = cache.get(cache_key)
    
    if not product:
        product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
        cache.set(cache_key, product, 1800) # تخزين مؤقت لمدة 30 دقيقة
        
    lang = request.GET.get('lang', 'ar')
    return render(request, 'product_detail.html', {'product': product, 'lang': lang})

def add_to_cart(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        cart = request.session.get('cart', {})
        product_id = str(pk)
        
        cart[product_id] = cart.get(product_id, 0) + 1
        request.session['cart'] = cart
        cart_count = sum(cart.values())

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': f'تمت إضافة "{product.name_ar}" إلى السلة بنجاح!',
                'cart_count': cart_count
            })

    return redirect('cart_view')

def cart_view(request):
    cart = request.session.get('cart', {})
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        
        if product_id in cart:
            if action == 'increase':
                cart[product_id] += 1
            elif action == 'decrease':
                cart[product_id] -= 1
                if cart[product_id] <= 0:
                    del cart[product_id]
            elif action == 'remove':
                del cart[product_id]
                
        request.session['cart'] = cart
        return redirect('cart_view')

    cart_items = []
    subtotal = 0
    total_items_count = sum(cart.values())

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)
        price = product.discount_price if product.discount_price else product.price
        total_price = price * quantity
        subtotal += total_price
        cart_items.append({'product': product, 'quantity': quantity, 'total_price': total_price})
    
    return render(request, 'cart.html', {
        'cart_items': cart_items, 
        'subtotal': subtotal,
        'cart_count': total_items_count
    })

def checkout_view(request):
    cart = request.session.get('cart', {})
    
    if not cart:
        return redirect('cart_view')

    # حساب المجموع الكلي
    subtotal = Decimal('0.00')
    for pid, val in cart.items():
        product = get_object_or_404(Product, id=pid)
        qty = int(val.get('quantity', 1)) if isinstance(val, dict) else int(val)
        price = product.discount_price if product.discount_price else product.price
        subtotal += price * Decimal(qty)

    client_secret = None

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'cod')
        cart_items_data = []
        
        # التأكد من توفر المخزون
        for product_id, item_data in cart.items():
            product = get_object_or_404(Product, id=product_id)
            quantity = int(item_data.get('quantity', 1)) if isinstance(item_data, dict) else int(item_data)
            price = product.discount_price if product.discount_price else product.price
            item_total = price * Decimal(quantity)
            
            if product.stock < Decimal(quantity):
                messages.error(request, f"عذراً، الكمية غير متوفرة للمنتج: {product.name_ar}.")
                return redirect('cart_view')
                
            cart_items_data.append({
                'product': product,
                'quantity': quantity,
                'total_price': item_total
            })

        generated_tracking_number = f"ZAD-{str(uuid.uuid4())[:6].upper()}"
        
        # إنشاء الطلب
        new_order = Order.objects.create(
            tracking_number=generated_tracking_number,
            email=request.user.email if request.user.is_authenticated else request.POST.get('email', "guest@zadherbal.com"),
            total_products_price=subtotal,
            shipping_fee=Decimal('0.00'),
            grand_total=subtotal,
            status='Pending',
            payment_method='Card' if payment_method == 'card' else 'Cash on Delivery'
        )

        for item in cart_items_data:
            OrderItem.objects.create(
                order=new_order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['total_price']
            )
            # خصم الكمية من المخزون
            item['product'].stock -= Decimal(item['quantity'])
            item['product'].save()

        # في حال اختيار الدفع عند الاستلام (COD)
        if payment_method == 'cod':
            send_order_confirmation_email(new_order) # إرسال البريد والفاتورة
            request.session['cart'] = {}
            cache.clear()
            messages.success(request, "تم إتمام طلبك بنجاح!")
            return redirect('order_success', tracking_number=new_order.tracking_number)

        # في حال اختيار الدفع بالبطاقة البنكية
        send_order_confirmation_email(new_order) # إرسال البريد والفاتورة عند الدفع بالبطاقة أيضاً
        request.session['cart'] = {}
        cache.clear()
        return JsonResponse({
            'success': True,
            'tracking_number': new_order.tracking_number
        })

    # إنشاء PaymentIntent لبطاقات Stripe عند تحميل الصفحة
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(subtotal * 100), # المبلغ بالفلس الإماراتي
            currency='aed',
            automatic_payment_methods={'enabled': True},
        )
        client_secret = intent.client_secret
    except Exception as e:
        client_secret = None

    context = {
        'cart': cart,
        'subtotal': subtotal,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'client_secret': client_secret,
        'lang': request.session.get('lang', 'ar'),
    }
    return render(request, 'checkout.html', context)

def order_success_view(request, tracking_number):
    order = get_object_or_404(Order, tracking_number=tracking_number)
    context = {
        'order': order,
        'tracking_number': order.tracking_number,
        'lang': request.GET.get('lang', 'ar')
    }
    return render(request, 'order_success.html', context)

@login_required(login_url='/login/')
def my_orders_view(request):
    # استخدام select_related و prefetch_related لمنع مشكلة N+1 Queries العالية عند كثرة المستخدمين
    orders = Order.objects.filter(email=request.user.email).prefetch_related('items__product').order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})

def track_order_view(request):
    order = None
    tracking_number = request.GET.get('tracking_number')
    if tracking_number:
        order = Order.objects.filter(tracking_number=tracking_number.strip()).first()
    return render(request, 'track_order.html', {'order': order, 'tracking_number': tracking_number})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home_view')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home_view')

@user_passes_test(is_admin_user, login_url='/custom-admin/login/')
def admin_dashboard(request):
    if request.method == 'POST' and 'expense_title' in request.POST:
        title = request.POST.get('expense_title')
        amount = request.POST.get('expense_amount')
        category = request.POST.get('expense_category', 'تشغيلي')
        notes = request.POST.get('expense_notes', '')
        
        if title and amount:
            Expense.objects.create(
                title_ar=title,
                title_en=title,
                amount=amount,
                category_ar=category,
                notes=notes
            )
            cache.clear() # مسح الذاكرة المؤقتة عند إضافة مصروفات جديدة لتحديث لوحة التحكم فوراً
            return redirect('admin_dashboard')

    lang = request.session.get('lang', 'ar')
    
    # جلب محسّن للبيانات مع تقليل استهلاك قاعدة البيانات
    products = Product.objects.all().order_by('-created_at')
    orders = Order.objects.all().prefetch_related('items__product').order_by('-created_at')
    expenses = Expense.objects.all().order_by('-date')
    category_form = CategoryForm()
    
    total_revenue = Decimal('0.00')
    for order in orders:
        if order.status == 'Not Delivered':
            total_revenue -= order.grand_total
        else:
            total_revenue += order.grand_total

    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    net_profit = float(total_revenue) - float(total_expenses)

    context = {
        'products': products,
        'orders': orders,
        'expenses': expenses,
        'category_form': category_form,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'lang': lang,
    }
    return render(request, 'custom_admin/dashboard.html', context)

@user_passes_test(is_admin_user, login_url='/custom-admin/login/')
def admin_update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            order.status = new_status
            order.save()
            messages.success(request, "تم تحديث حالة الطلب بنجاح.")
    return redirect('admin_dashboard')

@user_passes_test(is_admin_user, login_url='/custom-admin/login/')
def admin_print_financial_report(request):
    orders = Order.objects.all()
    expenses = Expense.objects.all()
    total_revenue = orders.aggregate(Sum('grand_total'))['grand_total__sum'] or 0
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    net_profit = float(total_revenue) - float(total_expenses)

    context = {
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'expenses': expenses,
    }
    return render(request, 'financial_report_print.html', context)

@user_passes_test(is_admin_user, login_url='/custom-admin/login/')
def admin_print_invoice(request, tracking_number):
    order = get_object_or_404(Order, tracking_number=tracking_number)
    lang = request.GET.get('lang', 'ar')
    return render(request, 'thermal_invoice.html', {'order': order, 'lang': lang})

@user_passes_test(is_admin_user, login_url='/custom-admin/login/')
def admin_add_product(request):
    if request.method == 'POST':
        form = CustomProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            cache.clear() # تفريغ الذاكرة المؤقتة لتحديث المنتجات فورا بالواجهة الرئيسية
            return redirect('admin_dashboard')
    else:
        form = CustomProductForm()
    return render(request, 'custom_admin/add_product.html', {'form': form})

def custom_admin_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                form.add_error(None, "ليس لديك صلاحيات الدخول إلى لوحة التحكم الإدارية.")
    else:
        form = AuthenticationForm()
    
    lang = request.GET.get('lang', 'ar')
    return render(request, 'custom_admin/login.html', {'form': form, 'lang': lang})

@user_passes_test(is_admin_user, login_url='/custom-admin/login/')
def admin_add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            cache.clear()
            return redirect('admin_dashboard')
    else:
        form = CategoryForm()
    return render(request, 'custom_admin/add_category.html', {'form': form})

@user_passes_test(is_admin_user, login_url='/custom-bin/login/' if False else '/custom-admin/login/')
def admin_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = CustomProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            cache.clear()
            return redirect('admin_dashboard')
    else:
        form = CustomProductForm(instance=product)
    return render(request, 'custom_admin/edit_product.html', {'form': form, 'product': product})

@user_passes_test(is_admin_user, login_url='/custom-admin/login/')
def admin_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        cache.clear()
        return redirect('admin_dashboard')
    return render(request, 'custom_admin/delete_product.html', {'product': product})

def shop_products_view(request):
    lang = request.GET.get('lang', 'ar')
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    sort_by = request.GET.get('sort', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')

    products = Product.objects.all().select_related('category')

    if query:
        products = products.filter(
            Q(name_ar__icontains=query) | Q(name_en__icontains=query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    if sort_by == 'latest':
        products = products.order_by('-created_at')
    elif sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'discount':
        products = products.filter(discount_price__isnull=False).order_by('-discount_price')
    else:
        products = products.order_by('-id')

    categories = Category.objects.all()

    context = {
        'products': products,
        'categories': categories,
        'lang': lang,
    }
    return render(request, 'shop_products.html', context)

def generate_invoice_pdf(order):
    """إنشاء ملف PDF للفاتورة في الذاكرة"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # عنوان الفاتورة
    p.setFont("Helvetica-Bold", 18)
    p.drawString(200, 750, "ZAD HERBAL - INVOICE")
    
    # تفاصيل الطلب
    p.setFont("Helvetica", 12)
    p.drawString(50, 710, f"Order Tracking Number: {order.tracking_number}")
    p.drawString(50, 690, f"Customer Email: {order.email}")
    p.drawString(50, 670, f"Payment Method: {order.payment_method}")
    p.drawString(50, 650, f"Order Status: {order.status}")
    p.drawString(50, 630, f"Total Amount: {order.grand_total} AED")
    
    p.line(50, 610, 550, 610)
    
    # تفاصيل المنتجات
    y = 580
    p.drawString(50, y, "Products:")
    y -= 20
    
    for item in order.items.all():
        product_name = item.product.name_en or item.product.name_ar
        p.drawString(70, y, f"- {product_name} x {item.quantity} : {item.price} AED")
        y -= 20
        
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.getvalue()

def send_order_confirmation_email(order):
    """إرسال بريد الشكر وتأكيد الطلب مع إرفاق الفاتورة PDF"""
    subject = f"شكرًا لطلبك من زاد للمنتجات العشبية - رقم الطلب #{order.tracking_number}"
    
    # محتوى الرسالة بحسب طريقة الدفع
    payment_info = "تم دفع المبلغ بنجاح عبر البطاقة البنكية." if order.payment_method == 'Card' else "طريقة الدفع المختارة: الدفع عند الاستلام."
    
    body = f"""مرحباً،

شكرًا لتسوقك من متجر زاد للمنتجات العشبية! تم استلام طلبك بنجاح.

تفاصيل الطلب:
- رقم تتبع الطلب: {order.tracking_number}
- المجموع الكلي: {order.grand_total} د.إ
- حالة الدفع: {payment_info}

تجد في المرفقات فاتورة الشراء الخاصة بطلبك بصيغة PDF.

مع تحيات،
فريق زاد للمنتجات العشبية
Zad Herbal Team
"""

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
    )
    
    # توليد ملف PDF وإرفاقه بالبريد
    pdf_content = generate_invoice_pdf(order)
    email.attach(f"Invoice_{order.tracking_number}.pdf", pdf_content, 'application/pdf')
    
    try:
        email.send(fail_silently=True)
    except Exception as e:
        print(f"Error sending confirmation email: {e}")