# Import required libraries
import os
import datetime
import pandas as pd
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
    # Perform web search using Tavily
    search_results = search_tool.search(query=query, search_depth="advanced", max_results=5)

    # Loop through each search result
    for result in search_results.get("results", []):
        logging.info(f"Processing result: {result['title']}")
        
        # Extract detailed content from the URL using Tavily's extract method
        try:
            extracted_content = search_tool.extract(urls=[result['url']])
            print("extracted content", extracted_content)
            raw_content = extracted_content.get("results", [])[0].get("raw_content", "") if extracted_content.get("results") else ""
            logging.info(f"Successfully extracted content from {result['url']}")
        except Exception as e:
            raw_content = ""
            logging.error(f"Failed to extract content from {result['url']}: {e}")
        
        # Create a prompt for Gemini LLM to extract job details from title, snippet, URL and extracted content
        prompt = f"""
        You are a JSON extraction tool. Extract the following job details from this search result and format your response as a valid, parseable JSON object with these exact keys:
        {{
            "company_name": "The name of the company offering the job",
            "job_title": "The title of the job position",
            "recruiter": "Name of the recruiter or recruiting agency if available, otherwise empty string",
            "email": "Contact email if available, otherwise empty string",
            "phone": "Contact phone if available, otherwise empty string",
            "location": "Job location",
            "summary": "Brief job description summary (max 30 words)",
            "application_link": "Direct link to apply for the job if different from source URL",
            "posted_date": "Date when the job was posted if available, otherwise empty string"
        }}

        CRITICAL INSTRUCTIONS:
        1. Return ONLY the JSON object, with no additional text, explanations, or formatting
        2. Ensure all keys are present even if values are empty strings
        3. Use double quotes for all keys and string values
        4. Do not include any markdown formatting, code blocks, or backticks
        5. Ensure the response is valid JSON that can be parsed by json.loads()

        Title: {result['title']}
        Snippet: {result['content']}
        URL: {result['url']}
        Extracted Content: {raw_content[:5000] if raw_content else "No additional content extracted"}
        """

        # Try to get structured data from Gemini
        try:
            response = llm.generate_content(prompt)
            extracted_text = response.text.strip()
            logging.info("Gemini response received successfully.")
            
            # Try to parse the JSON response
            try:
                import json
                job_data = json.loads(extracted_text)
                
                # Append structured data to the results list
                results.append({
                    "Company Name": job_data.get("company_name", ""),
                    "Job Title": job_data.get("job_title", ""),
                    "Recruiter": job_data.get("recruiter", ""),
                    "Email": job_data.get("email", ""),
                    "Phone": job_data.get("phone", ""),
                    "Location": job_data.get("location", ""),
                    "Summary": job_data.get("summary", ""),
                    "Link": job_data.get("application_link", result['url']),
                    "Posted Date": job_data.get("posted_date", ""),
                    "Source": result.get('url', '')
                })
                logging.info("Successfully parsed structured job data.")
            except json.JSONDecodeError as je:
                # If JSON parsing fails, store the raw text in summary
                logging.error(f"Failed to parse JSON response: {je}")
                results.append({
                    "Company Name": "",
                    "Job Title": "",
                    "Recruiter": "",
                    "Email": "",
                    "Phone": "",
                    "Location": "",
                    "Summary": extracted_text,  # Store raw Gemini output for review
                    "Link": result['url'],
                    "Posted Date": "",
                    "Source": result.get('url', '')
                })
        except Exception as e:
            # If LLM call fails, record the error in summary
            extracted_text = f"Error generating content: {e}"
            logging.error(f"Gemini error: {e}")
            results.append({
                "Company Name": "",
                "Job Title": "",
                "Recruiter": "",
                "Email": "",
                "Phone": "",
                "Location": "",
                "Summary": extracted_text,  # Store error message
                "Link": result['url'],
                "Posted Date": "",
                "Source": result.get('url', '')
            })

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
