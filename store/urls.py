from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home_view'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('add-to-cart/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('change-language/<str:lang_code>/', views.change_language, name='change_language'),
    path('checkout/', views.checkout_view, name='checkout_view'),
    path('order-success/<str:tracking_number>/', views.order_success_view, name='order_success'),
    path('custom-admin/order/update-status/<int:pk>/', views.admin_update_order_status, name='admin_update_order_status'),
    path('track-order/', views.track_order_view, name='track_order_view'),
    path('custom-admin/login/', views.custom_admin_login, name='custom_admin_login'),
    path('register/', views.register_view, name='register_view'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('custom-admin/category/add/', views.admin_add_category, name='admin_add_category'),
    path('products/', views.shop_products_view, name='shop_products'),
    
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    # لوحة التحكم المنفصلة عن Django Admin الأساسية
    path('custom-admin/product/edit/<int:pk>/', views.admin_edit_product, name='admin_edit_product'),
    path('custom-admin/product/delete/<int:pk>/', views.admin_delete_product, name='admin_delete_product'),
    path('custom-admin/print-financial-report/', views.admin_print_financial_report, name='admin_print_financial_report'),
    path('custom-admin/print-invoice/<str:tracking_number>/', views.admin_print_invoice, name='admin_print_invoice'),
    path('custom-admin/', views.admin_dashboard, name='admin_dashboard'),
    path('custom-admin/add-product/', views.admin_add_product, name='admin_add_product'),

    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
]