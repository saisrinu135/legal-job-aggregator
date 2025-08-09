# Import required libraries
import os
import datetime
import pandas as pd
import time
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from tavily import TavilyClient
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("job_aggregator.log"),
        logging.StreamHandler()
    ]
)

# Get API keys and email settings from environment variables (or use placeholders if not set)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "your_tavily_api_key")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "your_gemini_api_key")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_app_password")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "recipient_email@example.com")

# Ensure API keys and email settings are set, raise error if not
if TAVILY_API_KEY == "your_tavily_api_key" or GEMINI_API_KEY == "your_gemini_api_key":
    raise ValueError("Please set TAVILY_API_KEY and GOOGLE_API_KEY as environment variables.")

if EMAIL_SENDER == "your_email@gmail.com" or EMAIL_PASSWORD == "your_app_password" or EMAIL_RECIPIENT == "recipient_email@example.com":
    logging.warning("Email settings not configured. Email notifications will not be sent.")

# Initialize the Tavily client and Gemini LLM
logging.info("Initializing Tavily and Gemini...")
search_tool = TavilyClient(api_key=TAVILY_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
llm = genai.GenerativeModel("gemini-2.5-flash")
logging.info("Initialization complete.")

# Define job search queries focused on law-related opportunities in Hyderabad
queries = [
    # 🎓 Legal Internships – Lawctopus & Lawfer
    'site:lawctopus.com ("legal internship" OR "law intern") AND ("Hyderabad" OR "Telangana") -scholarship -course -competition',
    'site:lawfer.in ("legal internship" OR "law intern") AND ("Hyderabad" OR "Telangana") -competition -webinar -event',

    # 🏢 Junior Legal Roles – LinkedIn, Indeed, Glassdoor
    'site:linkedin.com/jobs ("junior lawyer" OR "legal associate" OR "law graduate") AND "Hyderabad" AND ("we are hiring" OR "apply now")',
    'site:indeed.com ("legal internship" OR "junior advocate" OR "law graduate fresher") AND "Hyderabad"',
    'site:glassdoor.co.in ("legal assistant" OR "junior lawyer" OR "LLB fresher") AND "Hyderabad"',

    # 🧠 Specialized Legal Domains – IP, Contracts, Corporate Law
    '("IP law" OR "contract drafting" OR "corporate law intern") AND "Hyderabad" AND ("law firm" OR "legal department") -training -course',

    # ⚖️ Bar & Bench + Other Legal Publications
    'site:barandbench.com ("junior lawyer" OR "legal recruitment") AND "Hyderabad"',
    'site:lawbhoomi.com ("internship" OR "associate") AND "Hyderabad" AND "apply" -workshop -fellowship -course',

    # 🧑‍⚖️ Govt & NGO Legal Openings
    'site:nalsa.gov.in internship OR volunteer OR lok adalat "Hyderabad"',
    'site:jobsforgood.com ("legal associate" OR "lawyer") AND "Hyderabad" AND "apply" -fellowship',

    # 🌐 Open search fallback for broader visibility (for Gemini parsing)
    '("law firm hiring" OR "legal opening") AND "Hyderabad" AND ("fresher" OR "intern" OR "junior associate")'
]


logging.info(f"Starting search for {len(queries)} queries...")

# This list will hold all extracted job data
results = []

# Loop through each search query
for query in queries:
    logging.info(f"Querying: {query}")
    search_results = search_tool.search(query=query, search_depth="advanced", max_results=5)

    for result in search_results.get("results", []):
        main_url = result.get("url", "")
        logging.info(f"Crawling: {main_url}")

        try:
            crawl_response = search_tool.crawl(
                url=main_url,
                instructions="Find all specific job posting pages for legal interns, junior lawyers, law graduates in Hyderabad. Ignore category pages, pagination, and archive pages.",
                max_depth=2,
                include_domains=["glassdoor.co.in", "lawbhoomi.com", "barandbench.com", "jobsforgood.com", "nalsa.gov.in", "lawfer.in", "lawctopus.com", "linkedin.com", "indeed.com"],
                max_breadth=3,
                limit=10
            )
        except Exception as e:
            logging.error(f"Failed to crawl {main_url}: {e}")
            continue

        # Filter crawled URLs to focus on actual job postings
        crawled_urls = []
        for crawled_page in crawl_response.get("results", []):
            page_url = crawled_page.get("url", "").strip()
            
            # Skip pagination, category, and archive pages
            skip_patterns = [
                "/page/", "/category/", "?page=", "?jsf=", 
                "&meta=", "archive", "pagination", "search?"
            ]
            
            # Only include URLs with job-related keywords
            include_patterns = [
                "internship", "job", "opportunity", "career", 
                "hiring", "recruit", "vacancy", "position"
            ]
            
            should_skip = any(pattern in page_url.lower() for pattern in skip_patterns)
            has_job_keywords = any(pattern in page_url.lower() for pattern in include_patterns)
            
            if not should_skip and has_job_keywords and page_url != main_url:
                crawled_urls.append(crawled_page)
        
        # Limit to first 5 relevant URLs to avoid overloading
        crawled_urls = crawled_urls[:5]
        logging.info(f"Processing {len(crawled_urls)} filtered job URLs from {main_url}")

        # Go through each relevant crawled page and process
        for crawled_page in crawled_urls:
            job_url = crawled_page.get("url", "")
            raw_content = crawled_page.get("raw_content", "")
            
            # # Skip if content is too short (likely not a job posting)
            # if not raw_content or len(raw_content.strip()) < 100:
            #     logging.warning(f"Skipping {job_url} - insufficient content")
            #     continue

            prompt = f"""
            You are a JSON extraction tool. Extract the following job details from this search result and format your response as a valid, parseable JSON object with these exact keys:
            {{
                "company_name": "",
                "job_title": "",
                "recruiter": "",
                "email": "",
                "phone": "",
                "location": "",
                "summary": "",
                "application_link": "",
                "posted_date": "",
                "still_available": "",
                "job_department": "law or others"
            }}

            CRITICAL INSTRUCTIONS:
            1. Return ONLY the JSON object, no extra text
            2. Use double quotes for all keys and values
            3. Ensure the JSON is valid
            4. If this is not a job posting, return empty values for all fields

            Title: {result.get('title', '')}
            Snippet: {result.get('content', '')}
            URL: {job_url}
            Extracted Content: {raw_content[:3000] if raw_content else "No additional content extracted"}
            """

            try:
                response = llm.generate_content(prompt)
                extracted_text = (response.text or "").strip()
                
                if not extracted_text:
                    logging.warning(f"Empty response from Gemini for {job_url}")
                    continue
                
                # Extract JSON from markdown code blocks if present
                if extracted_text.startswith("```json"):
                    # Remove markdown code block formatting
                    extracted_text = extracted_text.replace("```json", "").replace("```", "").strip()
                elif extracted_text.startswith("```"):
                    # Handle generic code blocks
                    extracted_text = extracted_text.replace("```", "").strip()
                    
                import json
                job_data = json.loads(extracted_text)
                
                # Only add to results if we found actual job data
                if job_data.get("company_name") or job_data.get("job_title"):
                    results.append({
                        "Company Name": job_data.get("company_name", ""),
                        "Job Title": job_data.get("job_title", ""),
                        "Recruiter": job_data.get("recruiter", ""),
                        "Email": job_data.get("email", ""),
                        "Phone": job_data.get("phone", ""),
                        "Location": job_data.get("location", ""),
                        "Summary": job_data.get("summary", ""),
                        "Link": job_data.get("application_link", job_url),
                        "Posted Date": job_data.get("posted_date", ""),
                        "Source": job_url,
                        "Still Available": job_data.get("still_available", ""),
                        "Job Department": job_data.get("job_department", "")
                    })
                else:
                    logging.info(f"No job data found in {job_url} - skipping")
                    
            except json.JSONDecodeError as e:
                logging.error(f"JSON parsing error for {job_url}: {e}")
                # Log the actual response for debugging
                logging.error(f"Gemini response was: {extracted_text[:200]}...")
            except Exception as e:
                logging.error(f"Gemini processing error for {job_url}: {e}")

            time.sleep(1)



# Convert results to a DataFrame and include a timestamp
now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
df = pd.DataFrame(results)
df["Scraped On"] = now

# Save the data to an Excel file
output_path = f"legal_jobs_{now}.xlsx"
# Ensure the filename doesn't contain any invalid characters
output_path = output_path.replace(" ", "_").replace(":", "-")
df.to_excel(output_path, index=False)

logging.info(f"Job data successfully saved to {output_path}")

# Function to send email with job data
def send_email_notification(file_path):
    try:
        # Check if email settings are configured
        if EMAIL_SENDER == "your_email@gmail.com" or EMAIL_PASSWORD == "your_app_password" or EMAIL_RECIPIENT == "recipient_email@example.com":
            logging.warning("Email settings not configured. Skipping email notification.")
            return False
            
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = f"Daily Legal Job Postings - {datetime.datetime.now().strftime('%Y-%m-%d')}"
        
        # Email body
        body = f"""Hello,

Attached is today's report of legal job postings in Hyderabad.
This report was generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}.

Regards,
Your Legal Job Aggregator
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach the Excel file
        with open(file_path, 'rb') as file:
            attachment = MIMEApplication(file.read(), Name=os.path.basename(file_path))
        attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        msg.attach(attachment)
        
        # Connect to SMTP server and send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, text)
        server.quit()
        
        logging.info(f"Email notification sent to {EMAIL_RECIPIENT}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email notification: {e}")
        return False

# Send email notification with the job data
send_email_notification(output_path)
# os.remove(output_path)

# Log completion message
logging.info("Job search and email notification process completed successfully.")
