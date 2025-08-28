from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .models import StockSubscription, NotificationLog
from .serializers import StockSubscriptionSerializer
from .services import StockDataService, NotificationService


class StockSubscriptionModelTest(TestCase):
    """Test StockSubscription model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_subscription(self):
        """Test creating a stock subscription"""
        subscription = StockSubscription.objects.create(
            user=self.user,
            stock_ticker='AAPL',
            email='notify@example.com',
            stock_price=Decimal('150.00')
        )
        
        self.assertEqual(subscription.stock_ticker, 'AAPL')
        self.assertEqual(subscription.email, 'notify@example.com')
        self.assertEqual(subscription.stock_price, Decimal('150.00'))
        self.assertEqual(subscription.price_display, '$150.00')
        self.assertTrue(subscription.is_active)
    
    def test_unique_constraint(self):
        """Test unique constraint on user/stock/email combination"""
        StockSubscription.objects.create(
            user=self.user,
            stock_ticker='AAPL',
            email='notify@example.com'
        )
        
        with self.assertRaises(Exception):
            StockSubscription.objects.create(
                user=self.user,
                stock_ticker='AAPL',
                email='notify@example.com'
            )
    
    def test_str_representation(self):
        """Test string representation"""
        subscription = StockSubscription.objects.create(
            user=self.user,
            stock_ticker='GOOGL',
            email='test@example.com'
        )
        
        expected = f"{self.user.username} - GOOGL (test@example.com)"
        self.assertEqual(str(subscription), expected)


class StockSubscriptionAPITest(APITestCase):
    """Test StockSubscription API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.subscription_data = {
            'stock_ticker': 'AAPL',
            'email': 'notify@example.com'
        }
    
    def test_create_subscription(self):
        """Test creating subscription via API"""
        url = reverse('stocksubscription-list')
        
        with patch('subscriptions.services.StockDataService.get_current_price') as mock_price:
            mock_price.return_value = Decimal('150.00')
            
            response = self.client.post(url, self.subscription_data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['stock_ticker'], 'AAPL')
            self.assertEqual(response.data['email'], 'notify@example.com')
            
            # Verify subscription was created
            subscription = StockSubscription.objects.get(id=response.data['id'])
            self.assertEqual(subscription.user, self.user)
            self.assertEqual(subscription.stock_price, Decimal('150.00'))
    
    def test_list_user_subscriptions(self):
        """Test listing user's subscriptions"""
        subscription = StockSubscription.objects.create(
            user=self.user,
            stock_ticker='AAPL',
            email='notify@example.com'
        )
        
        url = reverse('stocksubscription-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['stock_ticker'], 'AAPL')
    
    def test_filter_by_ticker(self):
        """Test filtering subscriptions by ticker"""
        StockSubscription.objects.create(
            user=self.user,
            stock_ticker='AAPL',
            email='aapl@example.com'
        )
        StockSubscription.objects.create(
            user=self.user,
            stock_ticker='GOOGL',
            email='googl@example.com'
        )
        
        url = reverse('stocksubscription-list')
        response = self.client.get(url, {'ticker': 'AAPL'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['stock_ticker'], 'AAPL')
    
    def test_send_now_action(self):
        """Test manual notification sending"""
        subscription = StockSubscription.objects.create(
            user=self.user,
            stock_ticker='AAPL',
            email='notify@example.com',
            stock_price=Decimal('150.00')
        )
        
        url = reverse('stocksubscription-send-now', args=[subscription.id])
        
        with patch('subscriptions.services.StockDataService.get_current_price') as mock_price, \
             patch('subscriptions.services.NotificationService.send_stock_notification') as mock_send:
            
            mock_price.return_value = Decimal('155.00')
            mock_notification = MagicMock()
            mock_notification.id = 'test-notification-id'
            mock_send.return_value = mock_notification
            
            response = self.client.post(url, {'message': 'Custom message'}, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('Notification sent successfully', response.data['message'])
            
            # Verify price was updated
            subscription.refresh_from_db()
            self.assertEqual(subscription.stock_price, Decimal('155.00'))
    
    def test_unauthorized_access(self):
        """Test API requires authentication"""
        self.client.force_authenticate(user=None)
        
        url = reverse('stocksubscription-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_isolation(self):
        """Test users can only see their own subscriptions"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create subscription for other user
        StockSubscription.objects.create(
            user=other_user,
            stock_ticker='TSLA',
            email='tesla@example.com'
        )
        
        # Create subscription for current user
        StockSubscription.objects.create(
            user=self.user,
            stock_ticker='AAPL',
            email='apple@example.com'
        )
        
        url = reverse('stocksubscription-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['stock_ticker'], 'AAPL')


class StockDataServiceTest(TestCase):
    """Test StockDataService functionality"""
    
    def setUp(self):
        self.service = StockDataService()
    
    def test_mock_price_generation(self):
        """Test mock price generation for development"""
        price = self.service._get_mock_price('AAPL')
        
        self.assertIsInstance(price, Decimal)
        self.assertGreaterEqual(price, Decimal('50.00'))
        self.assertLessEqual(price, Decimal('150.00'))
        
        # Same ticker should return same mock price
        price2 = self.service._get_mock_price('AAPL')
        self.assertEqual(price, price2)
    
    @patch('requests.get')
    def test_api_failure_fallback(self, mock_get):
        """Test fallback to mock data when APIs fail"""
        mock_get.side_effect = Exception("API Error")
        
        price = self.service.get_current_price('AAPL')
        
        self.assertIsNotNone(price)
        self.assertIsInstance(price, Decimal)


class NotificationServiceTest(TestCase):
    """Test NotificationService functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.subscription = StockSubscription.objects.create(
            user=self.user,
            stock_ticker='AAPL',
            email='notify@example.com',
            stock_price=Decimal('150.00')
        )
        
        self.service = NotificationService()
    
    @patch('django.core.mail.send_mail')
    def test_send_notification_success(self, mock_send_mail):
        """Test successful notification sending"""
        mock_send_mail.return_value = True
        
        notification_log = self.service.send_stock_notification(
            self.subscription,
            notification_type='manual',
            custom_message='Test message'
        )
        
        self.assertEqual(notification_log.status, 'sent')
        self.assertEqual(notification_log.notification_type, 'manual')
        self.assertEqual(notification_log.email_to, 'notify@example.com')
        self.assertIsNotNone(notification_log.sent_at)
        
        # Verify subscription was updated
        self.subscription.refresh_from_db()
        self.assertIsNotNone(self.subscription.last_notification_sent)
        self.assertEqual(self.subscription.last_price_sent, Decimal('150.00'))
    
    @patch('django.core.mail.send_mail')
    def test_send_notification_failure(self, mock_send_mail):
        """Test notification sending failure"""
        mock_send_mail.side_effect = Exception("SMTP Error")
        
        notification_log = self.service.send_stock_notification(self.subscription)
        
        self.assertEqual(notification_log.status, 'failed')
        self.assertIsNotNone(notification_log.error_message)
        self.assertIn('SMTP Error', notification_log.error_message)
    
    def test_subject_generation(self):
        """Test email subject generation"""
        subject = self.service._generate_subject(self.subscription)
        expected = f"AAPL Stock Update - $150.00"
        self.assertEqual(subject, expected)
        
        # Test without price
        self.subscription.stock_price = None
        subject = self.service._generate_subject(self.subscription)
        expected = "AAPL Stock Update"
        self.assertEqual(subject, expected)


class StockSubscriptionSerializerTest(TestCase):
    """Test StockSubscriptionSerializer validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_valid_ticker_validation(self):
        """Test valid stock ticker formats"""
        valid_tickers = ['AAPL', 'GOOGL', 'MSFT', 'BRK.A', 'BRK.B']
        
        for ticker in valid_tickers:
            data = {'stock_ticker': ticker, 'email': 'test@example.com'}
            serializer = StockSubscriptionSerializer(data=data)
            
            # Mock request context
            serializer.context = {'request': MagicMock(user=self.user)}
            
            self.assertTrue(serializer.is_valid(), f"Ticker {ticker} should be valid")
    
    def test_invalid_ticker_validation(self):
        """Test invalid stock ticker formats"""
        invalid_tickers = ['', 'TOOLONG', '123', 'A@PL', 'aa']
        
        for ticker in invalid_tickers:
            data = {'stock_ticker': ticker, 'email': 'test@example.com'}
            serializer = StockSubscriptionSerializer(data=data)
            serializer.context = {'request': MagicMock(user=self.user)}
            
            self.assertFalse(serializer.is_valid(), f"Ticker {ticker} should be invalid")
    
    def test_disposable_email_validation(self):
        """Test disposable email rejection"""
        disposable_emails = [
            'test@10minutemail.com',
            'user@tempmail.org',
            'fake@guerrillamail.com'
        ]
        
        for email in disposable_emails:
            data = {'stock_ticker': 'AAPL', 'email': email}
            serializer = StockSubscriptionSerializer(data=data)
            serializer.context = {'request': MagicMock(user=self.user)}
            
            self.assertFalse(serializer.is_valid(), f"Email {email} should be rejected")
            self.assertIn('email', serializer.errors)