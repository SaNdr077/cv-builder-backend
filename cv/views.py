
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
        
# ----------------------





def sitemap_view(request):
    raw_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://www.cvgener.com/</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/"/>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/about</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/about"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/about"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/about"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/about"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/about"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/about"/>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/contact</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/contact"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/contact"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/contact"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/contact"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/contact"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/contact"/>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog"/>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/professional-cv-2026</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/professional-cv-2026"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/professional-cv-2026"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/professional-cv-2026"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/professional-cv-2026"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/professional-cv-2026"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/professional-cv-2026"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/ats-friendly-cv</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/ats-friendly-cv"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/ats-friendly-cv"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/ats-friendly-cv"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/ats-friendly-cv"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/ats-friendly-cv"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/ats-friendly-cv"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/common-cv-mistakes</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/common-cv-mistakes"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/common-cv-mistakes"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/common-cv-mistakes"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/common-cv-mistakes"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/common-cv-mistakes"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/common-cv-mistakes"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/linkedin-profile-optimization</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/linkedin-profile-optimization"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/linkedin-profile-optimization"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/linkedin-profile-optimization"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/linkedin-profile-optimization"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/linkedin-profile-optimization"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/linkedin-profile-optimization"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/career-change-resume-tips</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/career-change-resume-tips"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/career-change-resume-tips"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/career-change-resume-tips"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/career-change-resume-tips"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/career-change-resume-tips"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/career-change-resume-tips"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/action-verbs-for-resume</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/action-verbs-for-resume"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/action-verbs-for-resume"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/action-verbs-for-resume"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/action-verbs-for-resume"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/action-verbs-for-resume"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/action-verbs-for-resume"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/how-to-talk-about-salary-in-interview</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/how-to-talk-about-salary-in-interview"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/how-to-talk-about-salary-in-interview"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/how-to-talk-about-salary-in-interview"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/how-to-talk-about-salary-in-interview"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/how-to-talk-about-salary-in-interview"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/how-to-talk-about-salary-in-interview"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/remote-work-cv-requirements</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/remote-work-cv-requirements"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/remote-work-cv-requirements"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/remote-work-cv-requirements"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/remote-work-cv-requirements"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/remote-work-cv-requirements"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/remote-work-cv-requirements"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/ats-resume-scanner-secrets</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/ats-resume-scanner-secrets"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/ats-resume-scanner-secrets"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/ats-resume-scanner-secrets"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/ats-resume-scanner-secrets"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/ats-resume-scanner-secrets"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/ats-resume-scanner-secrets"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/body-language-in-video-interviews</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/body-language-in-video-interviews"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/body-language-in-video-interviews"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/body-language-in-video-interviews"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/body-language-in-video-interviews"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/body-language-in-video-interviews"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/body-language-in-video-interviews"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/portfolio-importance-for-developers</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/portfolio-importance-for-developers"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/portfolio-importance-for-developers"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/portfolio-importance-for-developers"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/portfolio-importance-for-developers"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/portfolio-importance-for-developers"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/portfolio-importance-for-developers"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/overcoming-gap-in-resume</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/overcoming-gap-in-resume"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/overcoming-gap-in-resume"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/overcoming-gap-in-resume"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/overcoming-gap-in-resume"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/overcoming-gap-in-resume"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/overcoming-gap-in-resume"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/soft-skills-that-employers-value</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/soft-skills-that-employers-value"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/soft-skills-that-employers-value"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/soft-skills-that-employers-value"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/soft-skills-that-employers-value"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/soft-skills-that-employers-value"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/soft-skills-that-employers-value"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/ai-tools-for-career-growth</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/ai-tools-for-career-growth"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/ai-tools-for-career-growth"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/ai-tools-for-career-growth"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/ai-tools-for-career-growth"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/ai-tools-for-career-growth"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/ai-tools-for-career-growth"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/linkedin-profile-optimization-tips</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/linkedin-profile-optimization-tips"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/linkedin-profile-optimization-tips"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/linkedin-profile-optimization-tips"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/linkedin-profile-optimization-tips"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/linkedin-profile-optimization-tips"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/linkedin-profile-optimization-tips"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/salary-negotiation-strategies</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/salary-negotiation-strategies"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/salary-negotiation-strategies"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/salary-negotiation-strategies"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/salary-negotiation-strategies"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/salary-negotiation-strategies"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/salary-negotiation-strategies"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/remote-work-productivity-hacks</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/remote-work-productivity-hacks"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/remote-work-productivity-hacks"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/remote-work-productivity-hacks"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/remote-work-productivity-hacks"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/remote-work-productivity-hacks"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/remote-work-productivity-hacks"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/cv-writing-for-non-tech-professions</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/cv-writing-for-non-tech-professions"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/cv-writing-for-non-tech-professions"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/cv-writing-for-non-tech-professions"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/cv-writing-for-non-tech-professions"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/cv-writing-for-non-tech-professions"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/cv-writing-for-non-tech-professions"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/what-is-ats-resume-and-how-to-pass-it</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/what-is-ats-resume-and-how-to-pass-it"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/what-is-ats-resume-and-how-to-pass-it"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/what-is-ats-resume-and-how-to-pass-it"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/what-is-ats-resume-and-how-to-pass-it"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/what-is-ats-resume-and-how-to-pass-it"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/what-is-ats-resume-and-how-to-pass-it"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/europass-vs-modern-cv-templates</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/europass-vs-modern-cv-templates"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/europass-vs-modern-cv-templates"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/europass-vs-modern-cv-templates"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/europass-vs-modern-cv-templates"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/europass-vs-modern-cv-templates"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/europass-vs-modern-cv-templates"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/how-to-write-first-it-resume-without-experience</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/how-to-write-first-it-resume-without-experience"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/how-to-write-first-it-resume-without-experience"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/how-to-write-first-it-resume-without-experience"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/how-to-write-first-it-resume-without-experience"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/how-to-write-first-it-resume-without-experience"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/how-to-write-first-it-resume-without-experience"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/how-to-choose-the-right-cv-design-template</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/how-to-choose-the-right-cv-design-template"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/how-to-choose-the-right-cv-design-template"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/how-to-choose-the-right-cv-design-template"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/how-to-choose-the-right-cv-design-template"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/how-to-choose-the-right-cv-design-template"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/how-to-choose-the-right-cv-design-template"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/how-to-prepare-for-it-interview-2026</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/how-to-prepare-for-it-interview-2026"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/how-to-prepare-for-it-interview-2026"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/how-to-prepare-for-it-interview-2026"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/how-to-prepare-for-it-interview-2026"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/how-to-prepare-for-it-interview-2026"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/how-to-prepare-for-it-interview-2026"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/importance-of-action-verbs-in-resume-building</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/importance-of-action-verbs-in-resume-building"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/importance-of-action-verbs-in-resume-building"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/importance-of-action-verbs-in-resume-building"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/importance-of-action-verbs-in-resume-building"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/importance-of-action-verbs-in-resume-building"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/importance-of-action-verbs-in-resume-building"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/remote-work-job-search-strategy-2026</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/remote-work-job-search-strategy-2026"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/remote-work-job-search-strategy-2026"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/remote-work-job-search-strategy-2026"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/remote-work-job-search-strategy-2026"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/remote-work-job-search-strategy-2026"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/remote-work-job-search-strategy-2026"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/how-to-write-resume-with-no-experience</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/how-to-write-resume-with-no-experience"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/how-to-write-resume-with-no-experience"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/how-to-write-resume-with-no-experience"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/how-to-write-resume-with-no-experience"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/how-to-write-resume-with-no-experience"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/how-to-write-resume-with-no-experience"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/soft-skills-vs-hard-skills-in-cv</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/soft-skills-vs-hard-skills-in-cv"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/soft-skills-vs-hard-skills-in-cv"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/soft-skills-vs-hard-skills-in-cv"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/soft-skills-vs-hard-skills-in-cv"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/soft-skills-vs-hard-skills-in-cv"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/soft-skills-hard-skills-in-cv"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/how-to-write-ats-friendly-resume</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/how-to-write-ats-friendly-resume"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/how-to-write-ats-friendly-resume"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/how-to-write-ats-friendly-resume"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/how-to-write-ats-friendly-resume"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/how-to-write-ats-friendly-resume"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/how-to-write-ats-friendly-resume"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.cvgener.com/blog/portfolio-vs-resume-for-creatives-and-developers</loc>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.cvgener.com/en/blog/portfolio-vs-resume-for-creatives-and-developers"/>
    <xhtml:link rel="alternate" hreflang="ka" href="https://www.cvgener.com/blog/portfolio-vs-resume-for-creatives-and-developers"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://www.cvgener.com/en/blog/portfolio-vs-resume-for-creatives-and-developers"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://www.cvgener.com/de/blog/portfolio-vs-resume-for-creatives-and-developers"/>
    <xhtml:link rel="alternate" hreflang="fr" href="https://www.cvgener.com/fr/blog/portfolio-vs-resume-for-creatives-and-developers"/>
    <xhtml:link rel="alternate" hreflang="ru" href="https://www.cvgener.com/ru/blog/portfolio-vs-resume-for-creatives-and-developers"/>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>"""

    response = HttpResponse(raw_xml.strip(), content_type="application/xml; charset=utf-8")
    return response