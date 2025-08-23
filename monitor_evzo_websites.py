import requests
import json
from datetime import datetime
from email.mime.text import MIMEText
# pip install sib-api-v3-sdk
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint
import os
import chardet  # Add this import
import unicodedata

def send_email(api_key, to, subject, htmlcontent):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    payload = {
        "sender": {"name": "Website Monitor", "email": "rzk.rud@gmail.com"},
        "to": [{"email": to, "name": "Recipient"}],
        "subject": subject,
        "htmlContent": htmlcontent
    }
    print(f"Sending email to {to} with subject: {subject}")
    print(f"Email content: {htmlcontent}")
    # Send the email using Brevo API
    response = requests.post(url, headers=headers, json=payload)
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
    return response.status_code, response.json()

# Load configuration from file
with open('websites.json', 'r') as config_file:
    configs = json.load(config_file)

# Get today's date in the required format
today_date = datetime.now().strftime('%Y-%m-%d')

# Open log file for writing
with open('log.txt', 'a') as log_file:
    email_body = ""
    for config in configs:
        language = config.get('language')
        website = config.get('website')
        content_website_template = config.get('contentWebsite')
        keyword = config.get('keyword')

        # Replace the placeholder date in the content website URL with today's date
        content_website = content_website_template.replace('yyyy-mm-dd', today_date)

        # Initialize statuses
        main_website_status = "UP"
        content_website_status = "UP"
        keyword_status = "FOUND"

        # Check if the main website is up
        try:
            response = requests.get(website, timeout=5)
            if response.status_code != 200:
                main_website_status = "DOWN"
        except requests.RequestException:
            main_website_status = "DOWN"

        # Check if the content website is up and contains the keyword
        try:
            response = requests.get(content_website, timeout=5)
            if response.status_code != 200:
                content_website_status = "DOWN"
            else:
                try:
                    # Attempt to parse as JSON to handle escaped Unicode
                    try:
                        decoded_text = json.loads(response.text)
                    except json.JSONDecodeError:
                        # If not JSON, decode normally
                        detected_encoding = chardet.detect(response.content)['encoding']
                        if not detected_encoding:
                            detected_encoding = 'utf-8'
                        decoded_text = response.content.decode(detected_encoding)

                    # If decoded_text is a dictionary (from JSON), convert it to a string
                    if isinstance(decoded_text, dict):
                        decoded_text = json.dumps(decoded_text, ensure_ascii=False)

                    # Normalize the text
                    normalized_text = unicodedata.normalize("NFKC", decoded_text).strip().lower()
                    normalized_keyword = unicodedata.normalize("NFKC", keyword).strip().lower()

                    # print(f"Normalized Text: {normalized_text}")
                    # print(f"Normalized Keyword: {normalized_keyword}")

                    # print(f"Raw Content: {response.content}")
                    # print(f"Raw Text: {response.text}")

                    # Check if the normalized keyword exists in the normalized text
                    if normalized_keyword not in normalized_text:
                        keyword_status = "NOT_FOUND"
                except Exception as e:
                    print(f"Error processing response content: {e}")
                    keyword_status = "NOT_FOUND"
        except requests.RequestException:
            content_website_status = "DOWN"
            keyword_status = "NOT_FOUND"
        # Log the results on three separate lines
        log_file.write(f"{datetime.now()} - {language} - Main website: {main_website_status}\n")
        log_file.write(f"  URL: {website}\n")
        log_file.write(f"{datetime.now()} - {language} - Readings endpoint: {content_website_status}\n")
        log_file.write(f"  URL: {content_website}\n")
        log_file.write(f"{datetime.now()} - {language} - Gospel content: {keyword_status}\n\n")

        # Append to email body if any criteria is not met
        if main_website_status == "DOWN" or content_website_status == "DOWN" or keyword_status == "NOT_FOUND":
            email_body += f"{language}:\n"
            email_body += f"  Main website: {main_website_status} (URL: {website})\n"
            email_body += f"  Readings endpoint: {content_website_status} (URL: {content_website})\n"
            email_body += f"  Gospel content: {keyword_status}\n\n"

    # If there are any issues, send an email notification
    if email_body:
        api_key = os.getenv('BREVO_API_KEY')
        if not api_key:
            raise ValueError("Brevo API key is not set. Please configure the 'BREVO_API_KEY' environment variable.")

        # The rest of the script remains unchanged
        recipient = os.getenv('RECIPIENT_EMAIL')
        print(f"Sending email to {recipient}...")
        subject = "[ALERT] Daily Gospel Websites Monitoring Alert"
        formatted_body = email_body.replace("\n", "<br>")

        email_body_html = f"""
        <p>The following issues were detected during the website monitoring:</p>
        <pre style="font-family: monospace;">{formatted_body}</pre>
        """

        send_email(api_key, recipient, subject, email_body_html)
        print("Email sent successfully.")

# print the log.txt
with open('log.txt', 'r') as log_file:
    log_content = log_file.read()
    print(log_content)