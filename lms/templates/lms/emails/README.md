# LMS transactional emails

| Template | Used for |
|----------|----------|
| `base_email.html` | Shared layout (header, footer, colors). Extend for new mails. |
| `otp_login.html` / `.txt` | Email OTP login code. |
| `followup_generic.html` / `.txt` | Lead & checkout follow-ups (context-driven). |

**Sending:** `lms/emailing.py` → `send_branded_email()` / `send_branded_email_safe()`.

**Links in emails:** Set `LMS_PUBLIC_BASE_URL` in `.env` (e.g. `https://yourdomain.com`) so CTAs and “Visit site” work when the request object isn’t available (e.g. background tasks).

**Brand:** `LMS_EMAIL_BRAND_NAME`, `LMS_IDENTITY_LABEL` in settings.
