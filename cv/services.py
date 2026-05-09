# from playwright.sync_api import sync_playwright

# def generate_resume_pdf(html_content):
#     with sync_playwright() as p:
#         browser = p.chromium.launch()
#         page = browser.new_page()
        
#         page.set_content(html_content, wait_until="networkidle")
        
#         # კონტენტის სიმაღლის ავტომატური გამოთვლა
#         content_height = page.evaluate("document.body.scrollHeight")
        
#         pdf_bytes = page.pdf(
#             width="210mm",
#             height=f"{content_height}px",  # ← კონტენტის მიხედვით
#             print_background=True,
#         )
        
#         browser.close()
#         return pdf_bytes

from weasyprint import HTML

def generate_resume_pdf(html_content):
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes