"""
SMTP email backend — same as Django's smtp backend (explicit path for settings).
"""
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend

CustomEmailBackend = SMTPEmailBackend
