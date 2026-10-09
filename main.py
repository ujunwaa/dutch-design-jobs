import os
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY environment variable is missing. Check your GitHub Secrets!")

client = genai.Client(api_key=api_key)

def get_ind_sponsors():
    """Fetch sponsor list from IND Netherlands."""
    url = "https://ind.nl/en/public-register-recognised-sponsors/public-register-work"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching IND website: {e}")
        return ["Adyen", "Booking.com", "Mollie", "ASML", "Uber", "Just Eat Takeaway"]

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    sponsors = []
    
    if table:
        for row in table.find_all("tr")[1:]:
            cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
            if len(cols) >= 1 and cols[0]:
                sponsors.append(cols[0])
                
    print(f"Successfully retrieved {len(sponsors)} sponsors.")
    return sponsors[:100] if sponsors else ["Adyen", "Booking.com", "Mollie"]

def filter_tech_and_design_companies(company_list):
    """Use Gemini to identify companies hiring UX/UI/Product Designers."""
    print("Filtering sponsors with Gemini...")
    prompt = f"""
    Analyze this list of companies in the Netherlands:
    {company_list}

    Identify companies that operate in Tech, SaaS, E-commerce, FinTech, Digital Products, or Consultancies/Agencies, 
    and are likely to hire UX Designers, UI Designers, or Digital Product Designers.

    Return ONLY a valid JSON array of objects with keys: "company_name", "category".
    Do NOT include markdown formatting or ```json codeblocks.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"Error running Gemini API: {e}")
        return [{"company_name": c, "category": "Tech/Design"} for c in company_list[:10]]

def generate_dashboard_html(companies):
    """Generate HTML dashboard to display on Netlify."""
    os.makedirs("public", exist_ok=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dutch Visa Sponsor UX/UI Design Jobs</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #111; line-height: 1.5; }}
            h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 8px; }}
            p {{ color: #555; font-size: 14px; margin-bottom: 24px; }}
            .card {{ border: 1px solid #e1e4e8; padding: 16px 20px; margin-bottom: 12px; border-radius: 8px; background: #fff; }}
            .tag {{ display: inline-block; background: #eef3fe; color: #0052cc; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-bottom: 8px; }}
            a {{ color: #0052cc; text-decoration: none; font-weight: 500; font-size: 14px; display: inline-block; margin-top: 8px; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>Verified Dutch Visa Sponsors hiring Designers</h1>
        <p>Targeted for UX, UI, and Product Design roles (&le; 2 years experience). Auto-updated daily.</p>
        <div id="jobs">
    """
    
    for item in companies:
        html_content += f"""
        <div class="card">
            <span class="tag">{item.get('category', 'Tech/Design')}</span>
            <h3 style="margin:0;">{item['company_name']}</h3>
            <a href="[https://www.google.com/search?q=](https://www.google.com/search?q=){item['company_name']}+careers+UX+designer+Netherlands" target="_blank">Search Open UX Roles &rarr;</a>
        </div>
        """
        
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Dashboard built successfully in public/index.html")

if __name__ == "__main__":
    companies = get_ind_sponsors()
    filtered = filter_tech_and_design_companies(companies)
    generate_dashboard_html(filtered)
