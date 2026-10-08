import json
import logging
import urllib.request
import urllib.parse
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)

from .forms import ContactForm
from .models import SourceVisit

class HomeView(TemplateView):
    template_name = "master/home.html"

class AboutView(TemplateView):
    template_name = "master/about.html"

class IndustriesView(TemplateView):
    template_name = "master/industries.html"

class ServicesView(TemplateView):
    template_name = "master/services.html"

class ProductsView(TemplateView):
    template_name = "master/products.html"

class TechnologiesView(TemplateView):
    template_name = "master/technologies.html"

class PortfolioView(TemplateView):
    template_name = "master/portfolio.html"

class ContactView(TemplateView):
    template_name = "master/contact.html"

    def get(self, request, *args, **kwargs):
        source = request.GET.get('source', '').strip()
        if source:
            try:
                SourceVisit.objects.create(
                    source=source,
                    page_url=request.path,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    referer=request.META.get('HTTP_REFERER', '')
                )
            except Exception as e:
                logger.error("Failed to record source visit for '%s': %s", source, e)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.conf import settings
        context['turnstile_sitekey'] = getattr(settings, 'TURNSTILE_SITEKEY', '')
        
        raw_source = self.request.GET.get('source', '').strip()
        context['source'] = raw_source

        if raw_source:
            # Format source dynamically: "salar_jung" -> "Salar Jung"
            formatted_source = ' '.join(word.capitalize() for word in raw_source.replace('-', '_').split('_') if word)
            context['formatted_source'] = formatted_source
            context['hero_badge'] = "✨ You Found Us!"
            context['hero_title'] = f'Meet the Creators of <br><span class="bg-clip-text text-transparent bg-gradient-to-r from-[#075da2] to-[#0b75cd]">{formatted_source}</span>'
            context['hero_subtitle'] = f"We love that you peeked behind the curtain to see who crafted the digital experience for {formatted_source}."
        else:
            context['hero_badge'] = 'Get In Touch'
            context['hero_title'] = 'Let\'s Build Something <span class="bg-clip-text text-transparent bg-gradient-to-r from-[#075da2] to-[#0b75cd]">Great Together</span>'
            context['hero_subtitle'] = 'Every successful project starts with a conversation. Share your goals with us, and we\'ll help you explore the best technical path forward.'

        return context



class PrivacyPolicyView(TemplateView):
    template_name = "master/privacy_policy.html"

class RobotsTxtView(TemplateView):
    template_name = "robots.txt"
    content_type = "text/plain"

class LLMTxtView(TemplateView):
    template_name = "llm.txt"
    content_type = "text/plain"

class SitemapView(TemplateView):
    template_name = "master/sitemap.html"


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def verify_turnstile(token, ip_address):
    secret = settings.TURNSTILE_SECRET
    url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    data = urllib.parse.urlencode({
        'secret': secret,
        'response': token,
        'remoteip': ip_address
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data)
        response = urllib.request.urlopen(req, timeout=10)  # 10-second hard limit
        result = json.loads(response.read().decode())
        return result.get('success', False)
    except Exception as e:
        logger.error("Turnstile verification failed: %s", e, exc_info=True)
        return False

@require_POST
def submit_contact_form(request):
    ip_address = get_client_ip(request)
    
    # 1. Rate Limiting (Max 5 requests per hour per IP)
    cache_key = f'contact_form_submissions_{ip_address}'
    submission_count = cache.get(cache_key, 0)
    
    if submission_count >= 5:
        return JsonResponse({
            'success': False,
            'message': 'You have exceeded the maximum number of submissions. Please try again later.'
        }, status=429)

    # Increment Rate Limit Counter for all attempts (prevents brute-force spamming)
    cache.set(cache_key, submission_count + 1, 3600)

    # Parse JSON body
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data.'}, status=400)

    # 2. Verify Cloudflare Turnstile
    turnstile_token = data.get('cf-turnstile-response')
    if not turnstile_token:
        return JsonResponse({'success': False, 'message': 'Please complete the captcha verification.'}, status=400)
        
    is_valid_turnstile = verify_turnstile(turnstile_token, ip_address)
    if not is_valid_turnstile:
        return JsonResponse({'success': False, 'message': 'Captcha verification failed. Please try again.'}, status=400)

    # 3. Form Validation
    form = ContactForm(data)
    if form.is_valid():
        contact_message = form.save(commit=False)
        contact_message.ip_address = ip_address
        contact_message.save()
        
        # 4. Build logo URL & Context
        from django.templatetags.static import static
        logo_url = request.build_absolute_uri(static('img/logo.webp'))
        email_context = {
            'contact_message': contact_message,
            'logo_url': logo_url,
        }

        sender = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None) or 'webmaster@localhost'
        receiver = getattr(settings, 'CONTACT_EMAIL_RECEIVER', None)

        # 5. Send Admin Notification Email
        admin_subject = f"New Contact Request: {contact_message.subject}"
        admin_plain_message = (
            f"New contact request from {contact_message.first_name} {contact_message.last_name}\n"
            f"Email: {contact_message.email or 'Not provided'}\n"
            f"Phone: {contact_message.phone or 'Not provided'}\n"
            f"Subject: {contact_message.subject}\n\n"
            f"Message:\n{contact_message.message}"
        )
        try:
            admin_html_message = render_to_string('emails/admin_email.html', email_context, request=request)
        except Exception as e:
            logger.error(f"Failed to render admin HTML email template: {e}")
            admin_html_message = None

        if receiver:
            try:
                send_mail(
                    admin_subject,
                    admin_plain_message,
                    sender,
                    [receiver],
                    html_message=admin_html_message,
                    fail_silently=False,
                )
                logger.info(f"Admin contact email sent successfully to {receiver}")
            except Exception as e:
                logger.error(f"Failed to send admin contact email: {e}", exc_info=True)
        else:
            logger.warning("CONTACT_EMAIL_RECEIVER is not configured in settings. Admin email not sent.")

        # 6. Send Customer Confirmation Email (if email provided)
        if contact_message.email:
            customer_subject = f"Thank you for contacting Tecnolynx - {contact_message.subject}"
            customer_plain_message = (
                f"Dear {contact_message.first_name} {contact_message.last_name},\n\n"
                f"Thank you for reaching out to Tecnolynx Global. We have received your inquiry regarding '{contact_message.subject}'.\n\n"
                f"Our team will review your message and respond to you as soon as possible.\n\n"
                f"Best regards,\n"
                f"Operations Team\n"
                f"TecnolynxGlobal Pvt. Ltd."
            )
            try:
                customer_html_message = render_to_string('emails/customer_email.html', email_context, request=request)
            except Exception as e:
                logger.error(f"Failed to render customer HTML email template: {e}")
                customer_html_message = None

            try:
                send_mail(
                    customer_subject,
                    customer_plain_message,
                    sender,
                    [contact_message.email],
                    html_message=customer_html_message,
                    fail_silently=False,
                )
                logger.info(f"Customer confirmation email sent successfully to {contact_message.email}")
            except Exception as e:
                logger.error(f"Failed to send customer confirmation email: {e}", exc_info=True)

        return JsonResponse({
            'success': True,
            'message': 'Thank you! Your message has been sent successfully. We will get back to you shortly.'
        })
    else:
        # Return form errors
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = error_list[0]
        return JsonResponse({
            'success': False,
            'message': 'Please correct the errors.',
            'errors': errors
        }, status=400)
