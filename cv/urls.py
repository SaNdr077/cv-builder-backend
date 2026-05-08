from django.urls import path
from .views import CheckStatusView, GeneratePDFView, VerifyPayPalPayment

# urls.py
urlpatterns = [
    path('api/status/', CheckStatusView.as_view(), name='check-status'),
    path('api/generate-pdf/', GeneratePDFView.as_view(), name='generate-pdf'),
    path('api/verify-payment/', VerifyPayPalPayment.as_view(), name='verify-payment'),
]