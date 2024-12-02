from django.urls import path
from .views import RedirectView,Index,Products,Staff,Orders,OrderRequest,CustomSignupView,EditProducts,DeleteProduct

urlpatterns=[
    path('', RedirectView.as_view(), name='redirect_view'),
    path('dashboard/',Index.as_view(), name='dashboard'),
    path('products/',Products.as_view(), name='products'),
    path('products/edit_product/<str:product_id>/',EditProducts.as_view(),name='edit_product'),
    path('products/delete_product/<str:product_id>/',DeleteProduct.as_view(),name='delete_product'),
    path('staff/',Staff.as_view(),name='staff'),
    path('orders/',Orders.as_view(),name='orders'),
    path('order_request/',OrderRequest.as_view(), name='order_request'),
    path('accounts/signup',CustomSignupView.as_view(), name="account_signup")

]