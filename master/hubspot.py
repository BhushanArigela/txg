import datetime
import html
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

HUBSPOT_API_BASE_URL = "https://api.hubapi.com"
_session = requests.Session()


def _get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get_timeout() -> int:
    return getattr(settings, "HUBSPOT_REQUEST_TIMEOUT", 10)


def search_contact_by_email(email: str, token: str) -> dict | None:
    """
    Search for a HubSpot contact by email address.
    Returns the contact dict if found, otherwise None.
    """
    if not email:
        return None

    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts/search"
    payload = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email.strip().lower(),
                    }
                ]
            }
        ],
        "properties": ["email", "firstname", "lastname", "phone"],
        "limit": 1,
    }

    try:
        response = _session.post(
            url,
            json=payload,
            headers=_get_headers(token),
            timeout=_get_timeout(),
        )
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                return results[0]
            return None
        else:
            logger.error(
                f"HubSpot search contact failed [{response.status_code}]: {response.text}"
            )
            return None
    except requests.RequestException as e:
        logger.error(f"HubSpot search request exception: {e}", exc_info=True)
        return None


def create_contact(contact_data: dict, token: str) -> dict | None:
    """
    Create a new contact in HubSpot CRM.
    Returns the created contact data if successful, otherwise None.
    """
    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts"
    
    properties = {}
    if contact_data.get("email"):
        properties["email"] = contact_data["email"].strip().lower()
    if contact_data.get("first_name"):
        properties["firstname"] = contact_data["first_name"].strip()
    if contact_data.get("last_name"):
        properties["lastname"] = contact_data["last_name"].strip()
    if contact_data.get("phone"):
        properties["phone"] = contact_data["phone"].strip()
    
    properties["hs_lead_status"] = "NEW"

    payload = {"properties": properties}

    try:
        response = _session.post(
            url,
            json=payload,
            headers=_get_headers(token),
            timeout=_get_timeout(),
        )
        if response.status_code in (200, 201):
            return response.json()
        else:
            logger.error(
                f"HubSpot create contact failed [{response.status_code}]: {response.text}"
            )
            return None
    except requests.RequestException as e:
        logger.error(f"HubSpot create contact request exception: {e}", exc_info=True)
        return None


def update_contact(contact_id: str, contact_data: dict, token: str) -> dict | None:
    """
    Update an existing contact in HubSpot CRM by ID.
    Returns the updated contact data if successful, otherwise None.
    """
    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts/{contact_id}"
    
    properties = {}
    if contact_data.get("first_name"):
        properties["firstname"] = contact_data["first_name"].strip()
    if contact_data.get("last_name"):
        properties["lastname"] = contact_data["last_name"].strip()
    if contact_data.get("phone"):
        properties["phone"] = contact_data["phone"].strip()

    if not properties:
        return {"id": contact_id}

    payload = {"properties": properties}

    try:
        response = _session.patch(
            url,
            json=payload,
            headers=_get_headers(token),
            timeout=_get_timeout(),
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(
                f"HubSpot update contact failed [{response.status_code}]: {response.text}"
            )
            return None
    except requests.RequestException as e:
        logger.error(f"HubSpot update contact request exception: {e}", exc_info=True)
        return None


def create_contact_note(contact_id: str, subject: str, message: str, token: str) -> dict | None:
    """
    Create a note engagement associated with a contact in HubSpot CRM.
    """
    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/notes"
    
    safe_subject = html.escape(subject or "General Inquiry")
    safe_message = html.escape(message or "").replace("\n", "<br/>")
    note_body = (
        f"<h3>Website Contact Form Submission</h3>"
        f"<p><b>Subject:</b> {safe_subject}</p>"
        f"<p><b>Message:</b></p>"
        f"<blockquote>{safe_message}</blockquote>"
    )

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    payload = {
        "properties": {
            "hs_timestamp": now_iso,
            "hs_note_body": note_body,
        },
        "associations": [
            {
                "to": {"id": str(contact_id)},
                "types": [
                    {
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 202,
                    }
                ],
            }
        ],
    }

    try:
        response = _session.post(
            url,
            json=payload,
            headers=_get_headers(token),
            timeout=_get_timeout(),
        )

        if response.status_code in (200, 201):
            logger.info(f"HubSpot inquiry note created successfully for contact ID {contact_id}")
            return response.json()
        else:
            logger.error(
                f"HubSpot create note failed [{response.status_code}]: {response.text}"
            )
            return None
    except requests.RequestException as e:
        logger.error(f"HubSpot create note request exception: {e}", exc_info=True)
        return None


def sync_contact_to_hubspot(contact_message) -> dict:
    """
    Orchestrate HubSpot contact sync:
    1. Search contact by email.
    2. Update if exists, Create if doesn't exist.
    3. Store enquiry by creating an associated note on the contact.
    """
    token = getattr(settings, "HUBSPOT_ACCESS_TOKEN", None)
    if not token:
        logger.warning("HUBSPOT_ACCESS_TOKEN is not configured in settings. Skipping HubSpot sync.")
        return {"success": False, "reason": "token_not_configured"}

    email = getattr(contact_message, "email", None)
    if not email:
        logger.info("No email provided in contact submission. Skipping HubSpot sync.")
        return {"success": False, "reason": "no_email"}

    contact_payload = {
        "email": email,
        "first_name": getattr(contact_message, "first_name", ""),
        "last_name": getattr(contact_message, "last_name", ""),
        "phone": getattr(contact_message, "phone", ""),
    }

    try:
        # Step 1: Search HubSpot by email
        existing_contact = search_contact_by_email(email, token)
        
        if existing_contact and existing_contact.get("id"):
            contact_id = existing_contact["id"]
            logger.info(f"Found existing HubSpot contact ID {contact_id} for email {email}. Updating contact.")
            # Step 2a: Update existing contact
            update_contact(contact_id, contact_payload, token)
            action = "updated"
        else:
            logger.info(f"No existing HubSpot contact found for email {email}. Creating new contact.")
            # Step 2b: Create new contact
            created_contact = create_contact(contact_payload, token)
            if not created_contact or not created_contact.get("id"):
                logger.error(f"Failed to create contact in HubSpot for {email}")
                return {"success": False, "reason": "contact_creation_failed"}
            contact_id = created_contact["id"]
            action = "created"

        # Step 3: Store enquiry (create associated note)
        subject = getattr(contact_message, "subject", "")
        message = getattr(contact_message, "message", "")
        create_contact_note(contact_id, subject, message, token)

        logger.info(f"Successfully processed HubSpot enquiry for contact ID {contact_id} ({action})")
        return {
            "success": True,
            "contact_id": contact_id,
            "action": action,
        }
    except Exception as e:
        logger.error(f"Unexpected error syncing contact to HubSpot: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
