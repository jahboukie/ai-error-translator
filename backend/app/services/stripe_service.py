import stripe
import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class StripeService:
    def __init__(self):
        self.is_initialized = False
        try:
            if not settings.STRIPE_SECRET_KEY:
                logger.warning("STRIPE_SECRET_KEY is not set")
                return
                
            stripe.api_key = settings.STRIPE_SECRET_KEY
            # Test the API key by making a simple call
            stripe.Account.retrieve()
            self.is_initialized = True
            logger.info("Stripe service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Stripe service: {str(e)}")
            # Don't crash the service, just log the error
            stripe.api_key = None
            self.is_initialized = False
        
    def create_checkout_session(self, price_id: str, customer_email: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
        """Create a Stripe checkout session for subscription"""
        if not self.is_initialized:
            raise Exception("Stripe service is not properly initialized")
            
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    'product_type': 'subscription'
                }
            )
            return {
                'session_id': session.id,
                'url': session.url
            }
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise Exception(f"Failed to create checkout session: {str(e)}")
    
    def create_portal_session(self, customer_id: str, return_url: str) -> Dict[str, Any]:
        """Create a customer portal session for billing management"""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return {
                'url': session.url
            }
        except Exception as e:
            logger.error(f"Error creating portal session: {str(e)}")
            raise Exception(f"Failed to create portal session: {str(e)}")
    
    def get_customer_subscriptions(self, customer_id: str) -> Dict[str, Any]:
        """Get customer's active subscriptions"""
        try:
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status='active'
            )
            return {
                'subscriptions': [sub for sub in subscriptions.data]
            }
        except Exception as e:
            logger.error(f"Error getting subscriptions: {str(e)}")
            raise Exception(f"Failed to get subscriptions: {str(e)}")
    
    def create_customer(self, email: str, name: str = None) -> Dict[str, Any]:
        """Create a new Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name
            )
            return {
                'customer_id': customer.id,
                'email': customer.email
            }
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            raise Exception(f"Failed to create customer: {str(e)}")
    
    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Verify and process Stripe webhook"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            raise ValueError("Invalid signature")