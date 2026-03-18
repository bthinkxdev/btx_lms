"""
LMS services: S3 presigned URLs, certificate PDF, QR, email placeholder, payments.
"""
import io
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.files.base import ContentFile

# Presigned URL expiry (seconds)
S3_PRESIGNED_EXPIRY = getattr(settings, "LMS_S3_PRESIGNED_EXPIRY", 300)


def s3_generate_presigned_url(object_key: str, expiry_seconds: int | None = None) -> str | None:
    """
    Generate a presigned URL for a private S3 object.
    Returns None if S3 is not configured or key is empty.
    """
    if not object_key or not object_key.strip():
        return None
    expiry = expiry_seconds if expiry_seconds is not None else S3_PRESIGNED_EXPIRY
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        return None
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    region = getattr(settings, "AWS_S3_REGION_NAME", None)
    if not bucket:
        return None
    client_kwargs = {"region_name": region} if region else {}
    try:
        client = boto3.client("s3", **client_kwargs)
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key.strip()},
            ExpiresIn=expiry,
        )
        return url
    except (ClientError, Exception):
        return None


def certificate_generate_pdf(certificate) -> bool:
    """
    Generate certificate PDF and attach to certificate.pdf_file.
    Returns True if PDF was generated and saved.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm

    if certificate is None:
        return False
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(width / 2, height - 2 * cm, "Certificate of Completion")
        c.setFont("Helvetica", 14)
        c.drawCentredString(width / 2, height - 3.5 * cm, f"This is to certify that")
        c.setFont("Helvetica-Bold", 16)
        name = getattr(certificate.user, "get_full_name", None)
        if callable(name):
            name = name() or getattr(certificate.user, "username", "Student")
        else:
            name = getattr(certificate.user, "username", "Student")
        c.drawCentredString(width / 2, height - 4.5 * cm, str(name))
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, height - 5.5 * cm, f"has completed the course")
        c.setFont("Helvetica-Bold", 14)
        course_title = certificate.course.title if certificate.course else "Course"
        c.drawCentredString(width / 2, height - 6.5 * cm, course_title)
        c.setFont("Helvetica", 10)
        cid = certificate.certificate_id or ""
        c.drawCentredString(width / 2, 2 * cm, f"Certificate ID: {cid}")
        c.showPage()
        c.save()
        buffer.seek(0)
        name = f"certificate_{certificate.certificate_id}.pdf"
        certificate.pdf_file.save(name, ContentFile(buffer.read()), save=True)
        return True
    except Exception:
        return False


def certificate_generate_qr_code(certificate) -> bytes | None:
    """
    Generate QR code image bytes for certificate verification URL.
    Returns None if qrcode is not installed or generation fails.
    """
    if certificate is None:
        return None
    try:
        import qrcode
    except ImportError:
        return None
    base_url = getattr(settings, "LMS_VERIFICATION_BASE_URL", "") or ""
    if not base_url.strip():
        base_url = ""
    cert_id = (certificate.certificate_id or "").strip()
    if not cert_id:
        return None
    path = f"/verify/{cert_id}/"
    url = (base_url.rstrip("/") + path) if base_url else path
    try:
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    except Exception:
        return None


def certificate_send_email(certificate, attachment_pdf: bool = True) -> bool:
    """
    Placeholder: send certificate email (logic only; backend config in settings).
    Returns False; implement with your email backend.
    """
    if certificate is None:
        return False
    email = getattr(certificate.user, "email", None) or ""
    if not email:
        return False
    subject = getattr(settings, "LMS_CERTIFICATE_EMAIL_SUBJECT", "Your Certificate")
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
    # Send mail using django.core.mail.send_mail or EmailMessage
    # when EMAIL_BACKEND is configured. For now, no-op.
    return False


# Razorpay helpers

def _get_razorpay_client():
    """
    Return a configured Razorpay client instance, or None if library/keys missing.
    """
    key_id = getattr(settings, "RZP_CLIENT_ID", None) or ""
    key_secret = getattr(settings, "RZP_CLIENT_SECRET", None) or ""
    if not key_id.strip() or not key_secret.strip():
        return None
    try:
        import razorpay  # type: ignore
    except ImportError:
        return None
    return razorpay.Client(auth=(key_id, key_secret))


def razorpay_create_order(
    amount_paise: int,
    currency: str | None = None,
    receipt: str | None = None,
    notes: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create a Razorpay order for the given amount (in paise).
    Returns the order dict, or None on failure.
    """
    client = _get_razorpay_client()
    if client is None or amount_paise <= 0:
        return None
    data: Dict[str, Any] = {
        "amount": int(amount_paise),
        "currency": currency or getattr(settings, "RZP_CURRENCY", "INR"),
        "payment_capture": 1,
    }
    if receipt:
        data["receipt"] = receipt
    if notes:
        data["notes"] = notes
    try:
        return client.order.create(data=data)  # type: ignore[attr-defined]
    except Exception:
        return None


def razorpay_verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verify Razorpay payment signature. Returns True if valid.
    """
    client = _get_razorpay_client()
    if client is None:
        return False
    if not order_id or not payment_id or not signature:
        return False
    try:
        params = {
            "razorpay_order_id": str(order_id).strip(),
            "razorpay_payment_id": str(payment_id).strip(),
            "razorpay_signature": str(signature).strip(),
        }
        if not all(params.values()):
            return False
        client.utility.verify_payment_signature(params)  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


def razorpay_verify_enrollment_payment(
    order_id: str,
    payment_id: str,
    signature: str,
    *,
    course_slug: str,
    user_id: int,
) -> tuple[bool, str]:
    """
    After HMAC verification, confirm payment + order amounts and embedded notes
    match the course checkout (prevents tampered client amounts).
    Returns (success, error_code).
    """
    order_id = (order_id or "").strip()
    payment_id = (payment_id or "").strip()
    signature = (signature or "").strip()
    course_slug = (course_slug or "").strip()
    if not razorpay_verify_signature(order_id, payment_id, signature):
        return False, "signature"
    client = _get_razorpay_client()
    if client is None:
        return False, "client"
    try:
        payment = client.payment.fetch(payment_id)
    except Exception:
        return False, "payment_fetch"
    if (payment.get("order_id") or "") != order_id:
        return False, "order_mismatch"
    status = (payment.get("status") or "").lower()
    if status not in ("captured", "authorized"):
        return False, "payment_status"
    try:
        order = client.order.fetch(order_id)
    except Exception:
        return False, "order_fetch"
    notes = order.get("notes") or {}
    if str(notes.get("user_id", "")) != str(user_id):
        return False, "user_mismatch"
    if (notes.get("course_slug") or "").strip() != course_slug:
        return False, "course_mismatch"
    o_amt = int(order.get("amount") or 0)
    p_amt = int(payment.get("amount") or 0)
    if o_amt < 100 or o_amt != p_amt:
        return False, "amount_mismatch"
    exp_note = notes.get("expected_amount_paise")
    if exp_note is not None and str(exp_note).strip() != "":
        try:
            expected = int(str(exp_note).strip())
        except (ValueError, TypeError):
            return False, "order_notes"
        if expected < 100 or o_amt != expected:
            return False, "amount_mismatch"
    # Legacy orders: only course_slug + user_id in notes; amount still bound to server-created order
    return True, ""


def generate_s3_presigned_url(object_key: str, expiration: int = None) -> str:
    """
    Generate a presigned URL for S3 objects (videos, files, etc.).
    
    Usage for hero video in views.py:
        hero_video_url = generate_s3_presigned_url('videos/hero-video.mp4')
        context['hero_video_url'] = hero_video_url
    
    Args:
        object_key: S3 object key (e.g., 'videos/hero-video.mp4')
        expiration: URL expiration time in seconds (default from settings)
    
    Returns:
        Presigned URL string or empty string if AWS not configured
    
    Setup Required:
        1. Install boto3: pip install boto3
        2. Configure settings.py with AWS credentials
        3. Uncomment the implementation below
    """
    # TODO: Uncomment when AWS S3 is configured
    # import boto3
    # from botocore.exceptions import ClientError
    # 
    # if not all([
    #     getattr(settings, 'AWS_ACCESS_KEY_ID', ''),
    #     getattr(settings, 'AWS_SECRET_ACCESS_KEY', ''),
    #     getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
    # ]):
    #     return ''
    # 
    # if expiration is None:
    #     expiration = getattr(settings, 'LMS_S3_PRESIGNED_EXPIRY', 300)
    # 
    # try:
    #     s3_client = boto3.client(
    #         's3',
    #         aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    #         aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    #         region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
    #     )
    #     
    #     presigned_url = s3_client.generate_presigned_url(
    #         'get_object',
    #         Params={
    #             'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
    #             'Key': object_key
    #         },
    #         ExpiresIn=expiration
    #     )
    #     return presigned_url
    # 
    # except ClientError as e:
    #     print(f"Error generating presigned URL: {e}")
    #     return ''
    
    return ''  # Return empty string when not configured
