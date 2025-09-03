# Stock Subscription Service

A full-stack web application that provides stock price monitoring with AI-powered recommendations and automated email notifications during business hours.

## 🏗️ Architecture

**Backend**: Django REST Framework with JWT authentication  
**Frontend**: React + Vite + TailwindCSS  
**Database**: PostgreSQL  
**AI Integration**: OpenAI GPT for stock analysis  
**Notifications**: Email via SMTP with merged notifications  
**Scheduling**: Custom business hours scheduler (Mon-Fri, 9AM-5PM ET)

## ✨ Key Features

### 🔐 **Secure Authentication**
- JWT tokens in httpOnly cookies (XSS protection)
- CSRF protection with custom headers
- Role-based access (admin vs regular users)
- Cross-origin support for deployment

### 📈 **Stock Monitoring**
- Real-time stock price fetching from Yahoo Finance API
- AI-powered buy/sell/hold recommendations using OpenAI
- Price caching for performance optimization
- Support for major stock symbols (AAPL, GOOGL, TSLA, etc.)

### 📧 **Smart Notifications**
- **Business Hours Scheduling**: Runs every hour, Mon-Fri 9AM-5PM ET
- **Merged Emails**: One email per user with all their subscriptions
- **Manual "Send Now"**: Instant notifications for specific stocks
- **AI Insights**: Each email includes OpenAI-generated stock analysis
- **Notification Logging**: Complete audit trail for compliance

### 👥 **User Management**
- **Regular Users**: Manage their own subscriptions
- **Admin Users**: View/manage all users' subscriptions
- **Bulk Operations**: Price refresh, notification triggering
- **Pagination**: Optimized for large datasets

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- OpenAI API key (optional, for AI features)

### 1. Backend Setup

```bash
# Clone and navigate
git clone <repository-url>
cd HextomTakeHome

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env with your settings:
```

### 2. Environment Configuration

Create `.env` file:
```env
# Django settings
SECRET_KEY=your-super-secret-key-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DB_NAME=stocksubscription
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Email settings (Gmail example)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# OpenAI (optional - for AI recommendations)
OPENAI_API_KEY=sk-proj-your-openai-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Database Setup

```bash
# Create database
createdb stocksubscription

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (admin)
python manage.py createsuperuser
```

### 4. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Start Backend

```bash
# In project root
python manage.py runserver
```

### 6. Access Application

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/api/
- **Backend Health**: http://localhost:8000/api/auth/verify/

## 📡 API Documentation

### Authentication Endpoints
```
POST /api/auth/register/     # Create new user account
POST /api/auth/login/        # Authenticate user
POST /api/auth/logout/       # Clear authentication
GET  /api/auth/verify/       # Check auth status
POST /api/auth/refresh/      # Refresh JWT tokens
```

### Subscription Management
```
GET    /api/subscriptions/                    # List subscriptions
POST   /api/subscriptions/                    # Create subscription
GET    /api/subscriptions/{id}/               # Get specific subscription
PUT    /api/subscriptions/{id}/               # Update subscription
DELETE /api/subscriptions/{id}/               # Delete subscription

# Custom Actions
POST   /api/subscriptions/{id}/send_now/      # Send notification immediately
POST   /api/subscriptions/refresh_prices/    # Refresh all stock prices
POST   /api/subscriptions/trigger_notifications/ # Start scheduler (admin)
```

### Query Parameters
```
GET /api/subscriptions/?active=true          # Filter by active status
GET /api/subscriptions/?ticker=AAPL          # Filter by stock symbol
GET /api/subscriptions/?page=2&page_size=10  # Pagination
```

### Notification Logs
```
GET /api/subscriptions/logs/                 # View notification history
GET /api/subscriptions/logs/?subscription={id} # Filter by subscription
GET /api/subscriptions/logs/?status=sent     # Filter by status
```

## 🏢 Business Logic

### Notification Scheduling
- **Automatic**: Runs every hour during business hours (Mon-Fri, 9AM-5PM ET)
- **Manual**: Admin users can trigger immediate notifications
- **Smart Batching**: One email per user containing all their subscriptions
- **Fresh Prices**: Always fetches current prices before sending

### AI Integration
- **Stock Analysis**: OpenAI GPT generates buy/sell/hold recommendations
- **Caching**: 1-hour cache to minimize API costs
- **Graceful Fallback**: System works without AI if API unavailable
- **Context-Aware**: Includes current price and ticker in analysis

### Permission Model
```python
# Regular Users
- View/manage only their subscriptions
- Create new subscriptions
- Send manual notifications for their stocks
- View their notification history

# Admin Users  
- View/manage ALL subscriptions
- Bulk price refresh for all users
- Start/stop notification scheduler
- Access to all notification logs
- User management capabilities
```

## 🛠️ Development

### Project Structure
```
HextomTakeHome/
├── authentication/          # JWT auth, user management
├── subscriptions/           # Core business logic
│   ├── models.py           # StockSubscription, NotificationLog
│   ├── views.py            # REST API endpoints
│   ├── services.py         # Stock data, email notifications
│   ├── ai_analysis.py      # OpenAI integration
│   ├── scheduler.py        # Business hours scheduler
│   └── management/commands/ # Django management commands
├── stocksubscription/       # Django project settings
├── frontend/                # React application
│   ├── src/components/     # Reusable UI components
│   ├── src/pages/          # Page components
│   ├── src/services/       # API integration
│   └── src/utils/          # Utilities
├── templates/emails/        # Email templates (HTML + text)
└── requirements.txt         # Python dependencies
```

### Key Services

#### StockDataService
```python
# Real-time price fetching with caching
price = stock_service.get_current_price("AAPL")
```

#### NotificationService
```python
# Send individual notification
notification_service.send_stock_notification(subscription, 'manual')

# Send bulk notifications (merged by user)
notification_service.send_bulk_notifications(subscriptions)
```

#### StockAnalysisService
```python
# AI-powered stock analysis
recommendation = ai_service.get_stock_recommendation("AAPL", current_price)
```

### Running Tests
```bash
# Backend tests
python manage.py test

# Frontend tests  
cd frontend && npm run test
```

### Management Commands
```bash
# Send notifications manually
python manage.py send_notifications

# Refresh all stock prices
python manage.py refresh_stock_prices

# Dry run (testing)
python manage.py send_notifications --dry-run
```

## 🚀 Deployment

### Production Environment Variables
```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
SECRET_KEY=super-secure-production-key
DATABASE_URL=postgres://user:pass@host:port/db
EMAIL_HOST_PASSWORD=production-email-password
OPENAI_API_KEY=production-openai-key
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

### DigitalOcean App Platform
- Environment variables auto-injected from `.env.digitalocean`
- Database connection via `DATABASE_URL`
- Static files served automatically
- HTTPS enabled by default

### Build Commands
```bash
# Frontend production build
cd frontend && npm run build

# Backend static files
python manage.py collectstatic --noinput

# Database migration
python manage.py migrate
```

## 🔧 Configuration

### Email Setup (Gmail)
1. Enable 2FA on Gmail account
2. Generate App Password
3. Use App Password in `EMAIL_HOST_PASSWORD`

### OpenAI Setup
1. Create account at https://openai.com/
2. Generate API key
3. Add to `OPENAI_API_KEY` environment variable

### Database Setup
```sql
-- PostgreSQL setup
CREATE DATABASE stocksubscription;
CREATE USER stockuser WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE stocksubscription TO stockuser;
```

## 🐛 Troubleshooting

### Common Issues

**Authentication Failed**: Check JWT secret key consistency between requests

**Email Not Sending**: Verify SMTP settings and Gmail app password

**Stock Prices Not Loading**: Check Yahoo Finance API availability

**Scheduler Not Running**: Verify timezone settings and business hours logic

**CORS Errors**: Update `CORS_ALLOWED_ORIGINS` in settings

### Debug Mode
```bash
# Enable verbose logging
export DJANGO_LOG_LEVEL=DEBUG
python manage.py runserver

# Check notification logs
python manage.py send_notifications --dry-run
```

## 📝 License

This project is part of a technical assessment. Please check with the project owner for usage permissions.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

For technical issues or questions, please create an issue in the repository or contact the development team.

---

**Built with ❤️ using Django, React, and modern web technologies**