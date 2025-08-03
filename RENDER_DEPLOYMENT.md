# Deploying to Render

This guide provides step-by-step instructions for deploying the Legal Job Aggregator to Render's cron job service.

## Prerequisites

1. A [Render](https://render.com/) account
2. Your code pushed to a GitHub repository
3. API keys for Tavily and Google Gemini
4. Email credentials (for sending notifications)

## Deployment Steps

### 1. Push Your Code to GitHub

Ensure your repository includes:
- `main.py`
- `requirements.txt`
- `render.yaml`

### 2. Connect to Render

1. Log in to your Render account
2. Click "New" and select "Blueprint"
3. Connect your GitHub repository
4. Render will automatically detect the `render.yaml` configuration

### 3. Configure Environment Variables

Add the following environment variables in the Render dashboard:

- `TAVILY_API_KEY`: Your Tavily API key
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `EMAIL_SENDER`: Your email address (for sending notifications)
- `EMAIL_PASSWORD`: Your email password or app password
- `EMAIL_RECIPIENT`: The email address to receive job notifications

**Note for Gmail users:** You need to use an App Password instead of your regular password. Generate one at: https://myaccount.google.com/apppasswords

### 4. Deploy

Click "Apply" to deploy your service. Render will automatically:

1. Install the required dependencies from `requirements.txt`
2. Set up the cron job to run daily at 8:00 AM UTC (as specified in `render.yaml`)

## Monitoring and Logs

You can monitor your cron job's execution and view logs in the Render dashboard:

1. Go to your Render dashboard
2. Select your cron job service
3. Click on "Logs" to view execution logs

## Modifying the Schedule

To change when the job runs, update the `schedule` field in `render.yaml`:

```yaml
schedule: "0 8 * * *"  # Runs daily at 8:00 AM UTC
```

The schedule uses standard cron syntax:
- `0 8 * * *` = 8:00 AM daily
- `0 */12 * * *` = Every 12 hours
- `0 0 * * 1` = Midnight on Mondays

After changing the schedule, redeploy your service for the changes to take effect.

## Troubleshooting

- **Email Issues**: Check that your email credentials are correct and that you're using an app password for Gmail
- **API Errors**: Verify your API keys are valid and have sufficient quota
- **Execution Failures**: Check the logs in the Render dashboard for error messages