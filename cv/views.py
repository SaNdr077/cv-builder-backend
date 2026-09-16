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
    # ==========================================================================
    # SEO FIX (2026-08): სიტმეპი გადაწერილია hardcoded XML-ის ნაცვლად
    # მონაცემებზე დაფუძნებულად, რომ აღარასდროს დაშორდეს რეალურ React Router
    # routes-ს (App.jsx). წინა ვერსია იყენებდა www.cvgener.com-ს ყველგან,
    # მაშინ როცა საიტი რეალურად non-www დომენზეა ინდექსირებული Google-ში —
    # ეს ერთი მნიშვნელობა (SITE_URL) აკონტროლებს ყველაფერს.
    #
    # თუ Vercel-ის Domain Settings-ში www.cvgener.com არის "Primary Domain",
    # შეცვალე მხოლოდ ეს ერთი ხაზი (და შესაბამისად index.html/BlogPostDetail.jsx).
    # ==========================================================================
    SITE_URL = "https://cvgener.com"

    # ენები, რომლებსაც რეალურად აქვთ საკუთარი route App.jsx-ში.
    # ka არის default ენა (URL პრეფიქსის გარეშე).
    LANGS = ["en", "de", "fr", "ru"]

    # იგივე სია, რაც vite.config.js-შია (prerender-ის paths-ისთვის) —
    # თუ იქ დაამატებ ბლოგ-პოსტს, დაამატე აქაც.
    BLOG_SLUGS = [
        'professional-cv-2026',
        'ats-friendly-cv',
        'common-cv-mistakes',
        'linkedin-profile-optimization',
        'career-change-resume-tips',
        'action-verbs-for-resume',
        'how-to-talk-about-salary-in-interview',
        'remote-work-cv-requirements',
        'ats-resume-scanner-secrets',
        'body-language-in-video-interviews',
        'portfolio-importance-for-developers',
        'overcoming-gap-in-resume',
        'soft-skills-that-employers-value',
        'ai-tools-for-career-growth',
        'linkedin-profile-optimization-tips',
        'salary-negotiation-strategies',
        'remote-work-productivity-hacks',
        'cv-writing-for-non-tech-professions',
        'what-is-ats-resume-and-how-to-pass-it',
        'europass-vs-modern-cv-templates',
        'how-to-write-first-it-resume-without-experience',
        'how-to-choose-the-right-cv-design-template',
        'how-to-prepare-for-it-interview-2026',
        'importance-of-action-verbs-in-resume-building',
        'remote-work-job-search-strategy-2026',
        'how-to-write-resume-with-no-experience',
        'soft-skills-vs-hard-skills-in-cv',
        'how-to-write-ats-friendly-resume',
        'portfolio-vs-resume-for-creatives-and-developers',
    ]

    def multilang_entry(path, priority, changefreq):
        """
        გვერდისთვის, რომელსაც აქვს route ყველა ენაზე (ka + en/de/fr/ru).
        UPDATE (2026-08 v2): ადრე ეს აბრუნებდა ერთ <url>-ს (ka ვერსიით),
        დანარჩენი ენები კი მხოლოდ hreflang-ის დანართად ჩანდნენ — ტექნიკურად
        მუშაობდა, მაგრამ Google-ს არ აძლევდა /fr, /de და ა.შ. პირდაპირ,
        დამოუკიდებელ <loc>-ს. ახლა თითოეული ენა ცალკე <url> ჩანაწერია,
        ყველას აქვს იგივე სრული, რეციპროკული hreflang ნაკრები.
        """
        suffix = f"/{path}" if path else ""

        def loc_for(l):
            if l == "ka":
                return f"{SITE_URL}/{path}" if path else f"{SITE_URL}/"
            return f"{SITE_URL}/{l}{suffix}"

        alt_lines = [
            f'    <xhtml:link rel="alternate" hreflang="x-default" href="{loc_for("en")}"/>',
            f'    <xhtml:link rel="alternate" hreflang="ka" href="{loc_for("ka")}"/>',
        ]
        for lang in LANGS:
            alt_lines.append(
                f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{loc_for(lang)}"/>'
            )
        alt_block = "\n".join(alt_lines)

        blocks = []
        for lang in ["ka"] + LANGS:
            blocks.append(
                f"  <url>\n"
                f"    <loc>{loc_for(lang)}</loc>\n"
                f"{alt_block}\n"
                f"    <changefreq>{changefreq}</changefreq>\n"
                f"    <priority>{priority}</priority>\n"
                f"  </url>"
            )
        return blocks

    entries = []
    entries.extend(multilang_entry("", "1.0", "weekly"))
    entries.extend(multilang_entry("about", "0.7", "monthly"))
    entries.extend(multilang_entry("contact", "0.6", "monthly"))
    entries.extend(multilang_entry("blog", "0.9", "weekly"))

    for slug in BLOG_SLUGS:
        entries.extend(multilang_entry(f"blog/{slug}", "0.8", "monthly"))

    entries.extend(multilang_entry("privacy-policy", "0.3", "yearly"))

    body = "\n".join(entries)
    raw_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        f"{body}\n"
        "</urlset>"
    )

    response = HttpResponse(raw_xml, content_type="application/xml; charset=utf-8")
    return response