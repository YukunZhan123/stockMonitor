# Stock Monitor - DigitalOcean Deployment Guide

## 🚀 Quick Deployment Steps

### 1. **Prepare Your Repository**
```bash
# Make sure your code is in GitHub
git add .
git commit -m "Prepare for DigitalOcean deployment"
git push origin main
```

### 2. **Create DigitalOcean App**
1. Go to https://cloud.digitalocean.com/apps
2. Click **"Create App"**
3. Choose **"GitHub"** as source
4. Select your repository and **main** branch
5. **Import the app specification**: Upload `.digitalocean/app.yaml`

### 3. **Configure Environment Variables**
In DigitalOcean App Platform, add these environment variables:

#### Required Variables:
```bash
SECRET_KEY=your-django-secret-key-here
OPENAI_API_KEY=sk-your-openai-key
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
```

#### Auto-configured by DigitalOcean:
- `DATABASE_URL` (automatically set by managed database)
- `REDIS_URL` (if you add managed Redis)

### 4. **Deploy!**
- Click **"Create Resources"** 
- Wait 5-10 minutes for deployment
- Your app will be available at: `https://your-app-name.ondigitalocean.app`

## 📊 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │  Django API     │    │  PostgreSQL DB  │
│   (Static Site) │◄──►│  (Backend)      │◄──►│  (Managed)      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              ▲
                              │
                    ┌─────────────────┐
                    │  Celery Workers │
                    │  (Background)   │
                    │  + Redis Cache  │
                    └─────────────────┘
```

## 💰 Estimated Monthly Costs

| Service | Size | Cost |
|---------|------|------|
| Django API | Basic XXS | $5/month |
| React Frontend | Basic XXS | $5/month |
| Celery Worker | Basic XXS | $5/month |
| Celery Beat | Basic XXS | $5/month |
| PostgreSQL DB | Basic XS | $15/month |
| **Total** | | **~$35/month** |

## 🔧 What Gets Deployed

### **Frontend (React + Vite)**
- ✅ Optimized production build
- ✅ Static assets served by CDN
- ✅ Automatic HTTPS
- ✅ Custom domain support

### **Backend (Django)**
- ✅ API endpoints (`/api/`)
- ✅ Database migrations (auto-run)
- ✅ Static files served
- ✅ Gunicorn WSGI server

### **Background Services**
- ✅ **Celery Worker**: Processes email sending
- ✅ **Celery Beat**: Runs hourly email scheduler  
- ✅ **Redis**: Caching + task queue (managed)
- ✅ **PostgreSQL**: Main database (managed)

## 🔐 Security Features

- ✅ **HTTPS everywhere** (auto SSL certificates)
- ✅ **Environment variables** for secrets
- ✅ **Database encryption** at rest
- ✅ **CORS protection** configured
- ✅ **CSRF protection** enabled

## 📧 Post-Deployment Setup

### 1. **Create Admin User**
```bash
# In DigitalOcean Console
python manage.py createsuperuser
```

### 2. **Test Email Sending**
- Verify Gmail app password works
- Send test notification
- Check hourly automation

### 3. **Add Custom Domain** (Optional)
- Point your domain to DigitalOcean
- Update `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`

## 🔍 Monitoring & Logs

### **View Logs:**
- Go to DigitalOcean App Platform
- Click your app → **Runtime Logs**
- Filter by service (api, web, worker, scheduler)

### **Health Checks:**
- `https://your-app.ondigitalocean.app/api/auth/verify/` - API health
- `https://your-app.ondigitalocean.app/` - Frontend health

## 🚨 Troubleshooting

### **Common Issues:**

1. **Build Fails:**
   - Check `requirements.txt` versions
   - Verify Python version in `runtime.txt`

2. **Environment Variables Missing:**
   - Ensure all required vars are set in App Platform
   - Check `.env.example` for reference

3. **Database Connection:**
   - DigitalOcean auto-configures `DATABASE_URL`
   - No manual DB setup needed

4. **Emails Not Sending:**
   - Verify Gmail app password (not regular password)
   - Check `EMAIL_HOST_USER` matches your Gmail

## 🔄 Updates & Maintenance

### **Deploy Updates:**
1. Push code to GitHub main branch
2. DigitalOcean auto-deploys (if enabled)
3. Or manually trigger deployment

### **Database Backups:**
- DigitalOcean managed databases auto-backup daily
- Manual backups available in dashboard

### **Scaling:**
- Increase instance sizes in App Platform
- Add more worker instances for heavy email load

---

## 🎉 Your App Will Have:

✅ **Professional deployment** on DigitalOcean  
✅ **Automatic HTTPS** and SSL certificates  
✅ **Hourly AI-powered stock emails** 📈🤖  
✅ **Redis caching** for performance  
✅ **Managed database** with backups  
✅ **Background task processing** with Celery  
✅ **Production-ready** Django + React stack  

**Deployment URL:** `https://your-app-name.ondigitalocean.app` 🚀