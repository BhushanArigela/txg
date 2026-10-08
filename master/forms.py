import re
from django import forms
from django.utils.html import strip_tags
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False, max_length=20)

    class Meta:
        model = ContactMessage
        fields = ['first_name', 'last_name', 'email', 'phone', 'subject', 'message']

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')

        if not email and not phone:
            raise forms.ValidationError("Please provide either an email address or a phone number so we can contact you.")
        return cleaned_data

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '')
        if not first_name.strip():
            raise forms.ValidationError("First name is required.")
        return strip_tags(first_name).strip()

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '')
        if not last_name.strip():
            raise forms.ValidationError("Last name is required.")
        return strip_tags(last_name).strip()

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone:
            # Simple regex to allow +, spaces, digits, dashes, and parentheses
            phone_pattern = re.compile(r'^[0-9\+\-\s\(\)]+$')
            if not phone_pattern.match(phone):
                raise forms.ValidationError("Please enter a valid phone number.")
            if len(phone) < 8 or len(phone) > 20:
                raise forms.ValidationError("Phone number must be between 8 and 20 characters.")
        return strip_tags(phone).strip()

    def clean_subject(self):
        subject = self.cleaned_data.get('subject', '')
        if not subject or not subject.strip():
            raise forms.ValidationError("Subject is required.")
        if len(subject) > 100:
            raise forms.ValidationError("Subject is too long. Maximum 100 characters allowed.")
        return strip_tags(subject).strip()

    def clean_message(self):
        message = self.cleaned_data.get('message', '')
        if not message.strip():
            raise forms.ValidationError("Message is required.")
        
        if len(message) > 2000:
            raise forms.ValidationError("Message is too long. Maximum 2000 characters allowed.")
            
        # Strip HTML tags to sanitize input
        return strip_tags(message).strip()
