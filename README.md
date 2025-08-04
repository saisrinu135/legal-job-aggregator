# Legal Job Aggregator[![Daily Legal Job Search](https://github.com/saisrinu135/legal-job-aggregator/actions/workflows/daily-job-search.yml/badge.svg)](https://github.com/saisrinu135/legal-job-aggregator/actions/workflows/daily-job-search.yml)

This application automatically searches for legal job postings in Hyderabad from various websites, extracts relevant information, and compiles it into an Excel file. It can be configured to run daily and send the results via email using Render's cron job service.

## Features

- Searches multiple legal job websites for opportunities in Hyderabad
- Uses Tavily for web search and Gemini AI for data extraction
- Compiles job listings into an organized Excel file
- Sends daily email notifications with the latest job postings
- Can be scheduled to run automatically using Render's cron job service

## Setup

### Prerequisites

- Python 3.6 or higher
- Required Python packages (install using `pip install -r requirements.txt`)
- Tavily API key (get from [Tavily](https://tavily.com/))
- Google Gemini API key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))
- Email account for sending notifications (Gmail recommended)

### Configuration

#### Local Development

For local testing, you can set environment variables in your terminal:

```bash
# For Windows
set TAVILY_API_KEY=your_tavily_api_key
set GOOGLE_API_KEY=your_gemini_api_key
set EMAIL_SENDER=your_email@gmail.com
set EMAIL_PASSWORD=your_app_password
set EMAIL_RECIPIENT=recipient_email@example.com

# For macOS/Linux
export TAVILY_API_KEY=your_tavily_api_key
export GOOGLE_API_KEY=your_gemini_api_key
export EMAIL_SENDER=your_email@gmail.com
export EMAIL_PASSWORD=your_app_password
export EMAIL_RECIPIENT=recipient_email@example.com
```

**Note for Gmail users:** You need to use an App Password instead of your regular password. Generate one at: https://myaccount.google.com/apppasswords

### Running Manually

Run the script with Python:

```bash
python main.py
```

### Scheduling Automated Runs

You have several options to run this script automatically on a daily basis:

#### 1. Windows Task Scheduler (Local)

Run the included batch script to set up a daily task:

```bash
schedule_task.bat
```

This will create a Windows Task Scheduler job that runs the script daily at 8:00 AM.

#### 2. Linux/macOS Cron (Local)

Run the included shell script to set up a daily cron job:

```bash
chmod +x setup_cron.sh
./setup_cron.sh
```

This will create a cron job that runs the script daily at 8:00 AM.

#### 3. GitHub Actions (Cloud)

If you push this code to a GitHub repository, it includes a workflow file (`.github/workflows/daily-job-search.yml`) that will run the script daily at 8:00 AM UTC.

You'll need to add the following secrets to your GitHub repository:
- `TAVILY_API_KEY`
- `GOOGLE_API_KEY`
- `EMAIL_SENDER`
- `EMAIL_PASSWORD`
- `EMAIL_RECIPIENT`

#### 4. Render Cron Job (Cloud)

This repository includes a `render.yaml` file for deploying to Render's cron job service. See `RENDER_DEPLOYMENT.md` for detailed instructions.

### Deploying to Render

1. Create a new account on [Render](https://render.com/) if you don't have one
2. Fork or push this repository to GitHub
3. In Render dashboard, click "New" and select "Blueprint"
4. Connect your GitHub repository
5. Render will automatically detect the `render.yaml` configuration
6. Add your environment variables in the Render dashboard:
   - TAVILY_API_KEY
   - GOOGLE_API_KEY
   - EMAIL_SENDER
   - EMAIL_PASSWORD
   - EMAIL_RECIPIENT
7. Deploy the service

The cron job will automatically run daily at 8:00 AM UTC. You can adjust the schedule in the `render.yaml` file.

## Customization

To modify the job search queries, edit the `queries` list in `main.py`. You can add or remove search terms and target websites as needed.

## Troubleshooting

Check the `job_aggregator.log` file for detailed logs if you encounter any issues.
