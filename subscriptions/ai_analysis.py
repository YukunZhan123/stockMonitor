"""
AI-powered stock analysis service using OpenAI API
Generates buy/sell/hold recommendations with concise reasoning
"""

import logging
from typing import Dict, Optional
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('subscriptions')


class StockAnalysisService:
    """
    High-level purpose: Generate AI-powered stock recommendations
    - Uses OpenAI GPT to analyze stock data and provide buy/sell/hold decisions
    - Includes concise reasoning for each recommendation
    - Handles API errors gracefully with fallback responses
    """
    
    def __init__(self):
        """Initialize OpenAI client with API key from settings"""
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured - AI analysis will be disabled")
            self.client = None
        else:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.client = None

    def get_stock_recommendation(self, stock_ticker: str, current_price: Optional[Decimal] = None) -> Dict[str, str]:
        """
        Generate AI recommendation for a stock ticker with 1-hour caching
        
        Args:
            stock_ticker: Stock symbol (e.g., "AAPL", "GOOGL")
            current_price: Current stock price (optional)
            
        Returns:
            Dict with 'recommendation' (buy/sell/hold) and 'reason' (concise explanation)
        """
        # Check cache first (1 hour cache)
        cache_key = f"ai_recommendation_{stock_ticker.upper()}"
        cached_recommendation = cache.get(cache_key)
        if cached_recommendation is not None:
            logger.info(f"Using cached AI recommendation for {stock_ticker}")
            return cached_recommendation
        
        if not self.client:
            logger.warning(f"OpenAI client not available for {stock_ticker}")
            return {
                'recommendation': 'HOLD',
                'reason': 'AI analysis temporarily unavailable'
            }
        
        try:
            # Prepare the prompt for GPT
            price_info = f" at ${current_price}" if current_price else ""
            
            prompt = f"""
You are a financial analyst. Provide a brief investment recommendation for {stock_ticker}{price_info}.

Respond with ONLY:
1. One word: BUY, SELL, or HOLD
2. A concise reason (max 40 words explaining key factors)

Format your response exactly as:
RECOMMENDATION: [BUY/SELL/HOLD]
REASON: [detailed reasoning including market conditions, fundamentals, or technical factors]

Example:
RECOMMENDATION: BUY
REASON: Strong quarterly earnings beat expectations, expanding market share in key sectors, and positive analyst sentiment with growing revenue streams

Be professional and specific. Consider current market conditions, company fundamentals, recent performance, and industry trends.
"""

            # Make API call to OpenAI - optimized for lowest cost
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Cheapest chat model
                messages=[
                    {"role": "user", "content": prompt}  # Removed system message to save tokens
                ],
                max_tokens=80,  # Increased for longer reasoning (40 words ~60 tokens)
                temperature=0.1  # Lower temperature for more consistent/cheaper responses
            )
            
            # Parse the response
            content = response.choices[0].message.content.strip()
            result = self._parse_ai_response(content, stock_ticker)
            
            # Cache the result for 1 hour (3600 seconds)
            cache.set(cache_key, result, 3600)
            logger.info(f"Cached AI recommendation for {stock_ticker} for 1 hour")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get AI recommendation for {stock_ticker}: {str(e)}")
            error_result = {
                'recommendation': 'HOLD',
                'reason': 'Analysis temporarily unavailable'
            }
            # Cache error result for 5 minutes to prevent rapid retries
            cache.set(cache_key, error_result, 300)
            return error_result
    
    def _parse_ai_response(self, content: str, stock_ticker: str) -> Dict[str, str]:
        """
        Parse OpenAI response and extract recommendation and reason
        
        Args:
            content: Raw response from OpenAI
            stock_ticker: Stock symbol for fallback messaging
            
        Returns:
            Dict with parsed 'recommendation' and 'reason'
        """
        try:
            lines = content.strip().split('\n')
            recommendation = 'HOLD'
            reason = 'See detailed analysis'
            
            for line in lines:
                line = line.strip()
                if line.startswith('RECOMMENDATION:'):
                    rec_part = line.split(':', 1)[1].strip().upper()
                    if rec_part in ['BUY', 'SELL', 'HOLD']:
                        recommendation = rec_part
                elif line.startswith('REASON:'):
                    reason = line.split(':', 1)[1].strip()
            
            # Ensure reason is not too long
            if len(reason) > 120:
                reason = reason[:117] + '...'
            
            return {
                'recommendation': recommendation,
                'reason': reason
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse AI response for {stock_ticker}: {str(e)}")
            return {
                'recommendation': 'HOLD',
                'reason': 'Analysis parsing error'
            }
    
    def get_multiple_recommendations(self, stock_data: Dict[str, Optional[Decimal]]) -> Dict[str, Dict[str, str]]:
        """
        Get recommendations for multiple stocks
        
        Args:
            stock_data: Dict mapping stock_ticker -> current_price
            
        Returns:
            Dict mapping stock_ticker -> {recommendation, reason}
        """
        recommendations = {}
        
        for ticker, price in stock_data.items():
            try:
                recommendations[ticker] = self.get_stock_recommendation(ticker, price)
            except Exception as e:
                logger.error(f"Failed to get recommendation for {ticker}: {str(e)}")
                recommendations[ticker] = {
                    'recommendation': 'HOLD',
                    'reason': 'Analysis error occurred'
                }
        
        return recommendations