from django.urls import path
from .views import CheckStatusView, GeneratePDFView, VerifyPayPalPayment, SitemapView

urlpatterns = [
    path('api/status/', CheckStatusView.as_view(), name='check-status'),
    path('api/generate-pdf/', GeneratePDFView.as_view(), name='generate-pdf'),
    path('api/verify-payment/', VerifyPayPalPayment.as_view(), name='verify-payment'),
    path('sitemap.xml', SitemapView.as_view(), name='sitemap'),
]