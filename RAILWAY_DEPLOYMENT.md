# Railway Deployment Guide

This guide explains how to deploy the Incremental News Intelligence System to Railway.

## Prerequisites

1. A Railway account (sign up at https://railway.app)
2. A GitHub repository with your code
3. API keys for the services you want to use

## Deployment Steps

### 1. Prepare Your Repository

Ensure all necessary files are committed:
- `Procfile` - Defines the web process
- `railway.json` - Railway configuration
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification
- All source code files

### 2. Connect to Railway

1. Go to https://railway.app and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect the project

### 3. Configure Environment Variables

In Railway dashboard, go to your project → Variables tab and add:

**Required:**
- `SEARCHAPI_KEY` - Your SearchAPI key for news ingestion
- `PORT` - Automatically set by Railway (don't override)

**Optional:**
- `NEWSAPI_AI_KEY` - NewsAPI.ai key for additional sources
- `OPENAI_API_KEY` - OpenAI API key for LLM features
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint (if using Azure)
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key (if using Azure)
- `FLASK_DEBUG` - Set to `false` for production (default)

### 4. Configure Storage

Railway uses ephemeral storage. For persistent data storage, you have two options:

**Option A: Use Railway Volume (Recommended)**
1. In Railway dashboard, go to your service
2. Click "Add Volume"
3. Mount it to `/app/data` or your preferred data path
4. Update `STORAGE_BASE_PATH` environment variable if needed

**Option B: Use External Storage**
- Configure S3, Google Cloud Storage, or another cloud storage service
- Update the storage configuration in `incremental_news_intelligence/storage/`

### 5. Deploy

Railway will automatically:
1. Detect the Python project
2. Install dependencies from `requirements.txt`
3. Start the application using the `Procfile`
4. Expose the service on a public URL

### 6. Verify Deployment

1. Check the deployment logs in Railway dashboard
2. Visit the public URL provided by Railway
3. Test the dashboard functionality

## Configuration

### Port Configuration

The application automatically uses the `PORT` environment variable provided by Railway. No manual configuration needed.

### Production Settings

- Debug mode is disabled by default (set `FLASK_DEBUG=true` to enable)
- The application runs on `0.0.0.0` to accept external connections
- Logs are available in Railway dashboard

### Scaling

Railway automatically handles:
- Process restarts on failure
- Health checks
- Resource allocation

## Troubleshooting

### Build Fails

- Check that `requirements.txt` includes all dependencies
- Verify Python version in `runtime.txt` is supported
- Check build logs in Railway dashboard

### Application Won't Start

- Verify all required environment variables are set
- Check application logs in Railway dashboard
- Ensure `Procfile` command is correct

### Data Not Persisting

- Railway uses ephemeral storage by default
- Add a Railway Volume for persistent storage
- Or configure external cloud storage

### Port Issues

- Railway automatically sets the `PORT` environment variable
- Don't hardcode port numbers in your code
- The application reads `PORT` from environment

## Monitoring

Railway provides:
- Real-time logs
- Metrics dashboard
- Deployment history
- Error tracking

## Custom Domain

1. Go to your service settings in Railway
2. Click "Generate Domain" or "Add Custom Domain"
3. Configure DNS as instructed

## Cost Considerations

- Railway offers a free tier with usage limits
- Monitor your usage in the Railway dashboard
- Consider upgrading for production workloads

## Support

For Railway-specific issues:
- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

For application issues:
- Check application logs in Railway dashboard
- Review error messages and stack traces

