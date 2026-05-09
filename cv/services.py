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

from playwright.sync_api import sync_playwright

def generate_resume_pdf(html_content):
    with sync_playwright() as p:
        # Railway-ზე (Linux) აუცილებელია --no-sandbox არგუმენტი
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage'
            ]
        )
        
        page = browser.new_page()
        
        # ვტვირთავთ HTML-ს და ველოდებით ყველა სკრიპტის (მაგ. Tailwind) ჩატვირთვას
        page.set_content(html_content, wait_until="networkidle")
        
        # კონტენტის სიმაღლის გამოთვლა
        content_height = page.evaluate("document.body.scrollHeight")
        
        # PDF-ის გენერაცია
        pdf_bytes = page.pdf(
            width="210mm",
            height=f"{content_height}px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        
        browser.close()
        return pdf_bytes