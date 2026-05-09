# import os
# import requests
# import geoip2.database
# from django.conf import settings
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from django.http import HttpResponse
# from django.utils import timezone
# from .models import Device
# from .services import generate_resume_pdf
# import os
# from dotenv import load_dotenv

# load_dotenv()
# # PayPal კონფიგურაცია (Sandbox-ისთვის)
# PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
# PAYPAL_SECRET = os.getenv('PAYPAL_SECRET')
# PAYPAL_BASE_URL = 'https://api-m.sandbox.paypal.com'

# def get_client_ip(request):
#     x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#     if x_forwarded_for:
#         ip = x_forwarded_for.split(',')[0]
#     else:
#         ip = request.META.get('REMOTE_ADDR')
#     return ip

# class CheckStatusView(APIView):
#     def get(self, request):
#         device_id = request.query_params.get('device_id')
#         if not device_id:
#             return Response({"error": "Device ID required"}, status=400)

#         device, created = Device.objects.get_or_create(device_id=device_id)
        
#         # ენის დეტექცია
#         user_ip = get_client_ip(request)
#         if user_ip == '127.0.0.1': user_ip = '94.232.176.0'
#         detected_lang = "ka"
        
#         db_path = os.path.join(settings.GEOIP_PATH, 'GeoLite2-Country.mmdb')
#         try:
#             if os.path.exists(db_path):
#                 with geoip2.database.Reader(db_path) as reader:
#                     code = reader.country(user_ip).country.iso_code
#                     detected_lang = {'GE':'ka','RU':'ru','DE':'de','FR':'fr'}.get(code, 'en')
#         except: pass

#         return Response({
#             "can_download": device.can_download(),
#             "downloads_left": device.paid_downloads_balance,
#             "is_premium": device.can_download(),
#             "detected_lang": detected_lang 
#         })

# class GeneratePDFView(APIView):
#     def post(self, request):
#         device_id = request.data.get('device_id')
#         html_content = request.data.get('html')

#         try:
#             device = Device.objects.get(device_id=device_id)
#             if not device.can_download():
#                 return Response({"error": "გადაიხადეთ ჩამოტვირთვისთვის"}, status=402)
            
#             pdf_data = generate_resume_pdf(html_content)
#             device.increment_download()

#             response = HttpResponse(pdf_data, content_type='application/pdf')
#             response['Content-Disposition'] = 'attachment; filename="CV.pdf"'
#             return response
#         except Exception as e:
#             return Response({"error": str(e)}, status=500)

# class VerifyPayPalPayment(APIView):
#     def post(self, request):
#         order_id = request.data.get('orderID')
#         device_id = request.data.get('device_id')
        
#         # 1. Access Token-ის აღება
#         auth_res = requests.post(
#             f"{PAYPAL_BASE_URL}/v1/oauth2/token",
#             auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
#             data={'grant_type': 'client_credentials'}
#         ).json()
#         token = auth_res.get('access_token')

#         # 2. ფულის ჩამოჭრა (Capture the Order)
#         # ეს ნაბიჯი აკლდა შენს კოდს - ის APPROVED-ს აქცევს COMPLETED-ად
#         capture_res = requests.post(
#             f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
#             headers={
#                 'Content-Type': 'application/json',
#                 'Authorization': f"Bearer {token}"
#             }
#         )
#         capture_data = capture_res.json()

#         # 3. შემოწმება და ბალანსის დამატება
#         if capture_data.get('status') == 'COMPLETED':
#             device, _ = Device.objects.get_or_create(device_id=device_id)
#             device.add_paid_limit(3)
#             return Response({"status": "success", "balance": device.paid_downloads_balance})
        
#         print("CAPTURE FAILED:", capture_data)
#         return Response({"error": "გადახდა ვერ დადასტურდა", "details": capture_data}, status=400)


import os
import requests
import geoip2.database
import logging # შეცდომების უკეთ დასალოგად
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.utils import timezone
from .models import Device
from .services import generate_resume_pdf
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# PayPal კონფიგურაცია
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET')
PAYPAL_BASE_URL = 'https://api-m.paypal.com'


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class CheckStatusView(APIView):
    def get(self, request):
        device_id = request.query_params.get('device_id')
        if not device_id:
            return Response({"error": "Device ID required"}, status=400)

        device, created = Device.objects.get_or_create(device_id=device_id)
        
        # ენის დეტექცია
        user_ip = get_client_ip(request)
        if user_ip == '127.0.0.1': user_ip = '94.232.176.0'
        detected_lang = "ka"
        
        db_path = os.path.join(settings.GEOIP_PATH, 'GeoLite2-Country.mmdb')
        try:
            if os.path.exists(db_path):
                with geoip2.database.Reader(db_path) as reader:
                    code = reader.country(user_ip).country.iso_code
                    detected_lang = {'GE':'ka','RU':'ru','DE':'de','FR':'fr'}.get(code, 'en')
        except Exception as e:
            logger.error(f"GeoIP Error: {e}")

        return Response({
            "can_download": device.can_download(),
            "downloads_left": device.paid_downloads_balance,
            "is_premium": device.can_download(),
            "detected_lang": detected_lang 
        })

class GeneratePDFView(APIView):
    def post(self, request):
        device_id = request.data.get('device_id')
        html_content = request.data.get('html')

        if not device_id:
            return Response({"error": "Device ID is missing"}, status=400)

        try:
            # ვიყენებთ get_or_create-ს, რომ თუ ბაზაში არაა, არ დაიქრაშოს
            device, _ = Device.objects.get_or_create(device_id=device_id)
            
            # დროებითი შემოწმება ტესტირებისთვის (რომ 402 არ ამოაგდოს)
            if not device.can_download():
                return Response({"error": "გადაიხადეთ ჩამოტვირთვისთვის"}, status=402)
            
            # PDF-ის გენერაცია
            pdf_data = generate_resume_pdf(html_content)
            
            # მხოლოდ წარმატებული გენერაციის შემდეგ ვამცირებთ ლიმიტს
            device.increment_download()

            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="CV.pdf"'
            return response
            
        except Exception as e:
            logger.exception("PDF Generation Failed") # ეს Railway-ს ლოგებში სრულ Traceback-ს დაწერს
            return Response({"error": str(e)}, status=500)

class VerifyPayPalPayment(APIView):
    def post(self, request):
        order_id = request.data.get('orderID')
        device_id = request.data.get('device_id')
        
        if not order_id or not device_id:
            return Response({"error": "Missing orderID or device_id"}, status=400)

        try:
            # 1. Access Token-ის აღება
            auth_res = requests.post(
                f"{PAYPAL_BASE_URL}/v1/oauth2/token",
                auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
                data={'grant_type': 'client_credentials'}
            ).json()
            token = auth_res.get('access_token')

            # 2. ფულის ჩამოჭრა
            capture_res = requests.post(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {token}"
                }
            )
            capture_data = capture_res.json()

            # 3. ბალანსის დამატება
            if capture_data.get('status') == 'COMPLETED':
                device, _ = Device.objects.get_or_create(device_id=device_id)
                device.add_paid_limit(3)
                return Response({"status": "success", "balance": device.paid_downloads_balance})
            
            return Response({"error": "გადახდა ვერ დადასტურდა", "details": capture_data}, status=400)
        except Exception as e:
            return Response({"error": f"Payment Verification Error: {str(e)}"}, status=500)