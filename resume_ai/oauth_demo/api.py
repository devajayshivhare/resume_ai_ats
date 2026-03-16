# In your Frappe app: oauth_demo/api.py

import frappe
from frappe.integrations.oauth2 import OAuthWebRequestValidator
from oauth2.web.grant import AuthorizationCodeGrant
from oauth2.web import SiteAdapter
from oauth2.datatype import Client
from oauth2.web.wsgi import Request as OAuthRequest
import json
from frappe.utils import get_url
from frappe.core.doctype.user.user import create_contact

# @frappe.whitelist(allow_guest=True)
# def exchange_google_token(code, state=None):
#     """
#     Exchange Google authorization code for Frappe access token
#     """
#     try:
#         # Verify Google token and get user info
#         from frappe.integrations.oauth2_logins import login_via_google
#         from frappe.utils.oauth import get_oauth2_providers
        
#         # Call Frappe's built-in Google handler
#         login_via_google(code=code, state=state)
        
#         # Get current user after successful login
#         if frappe.session.user and frappe.session.user != "Guest":
#             user = frappe.get_doc("User", frappe.session.user)
            
#             # Generate Frappe OAuth token for API access
#             token = frappe.get_doc({
#                 "doctype": "OAuth Bearer Token",
#                 "client": get_oauth_client_id(),  # Your React app client ID
#                 "user": user.name,
#                 "scopes": "openid profile email",
#                 "access_token": frappe.generate_hash(length=32),
#                 "refresh_token": frappe.generate_hash(length=32),
#                 "expires_in": 3600
#             })
#             token.insert(ignore_permissions=True)
#             frappe.db.commit()
            
#             return {
#                 "success": True,
#                 "access_token": token.access_token,
#                 "refresh_token": token.refresh_token,
#                 "expires_in": token.expires_in,
#                 "user": {
#                     "email": user.email,
#                     "full_name": user.full_name,
#                     "user_image": user.user_image
#                 }
#             }
#         else:
#             frappe.throw("Authentication failed")
            
#     except Exception as e:
#         frappe.log_error(f"OAuth token exchange failed: {str(e)}")
#         return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def exchange_google_token(code, state=None):
    """
    Exchange Google authorization code for Frappe access token.
    Auto-register user if not exists.
    """
    try:
        # Step 1: Verify Google token and get user info
        from frappe.integrations.oauth2_logins import login_via_google
        from frappe.utils.oauth import get_oauth2_providers

        # Call Frappe's built-in Google handler
        login_via_google(code=code, state=state)

        # Step 2: Get or create user
        user_email = frappe.session.user
        if not user_email or user_email == "Guest":
            frappe.throw("Authentication failed")

        user = frappe.db.get_value("User", {"email": user_email}, "name")
        if not user:
            # Auto-register user
            user_doc = create_user_from_google(code)
            user = user_doc.name

        # Step 3: Generate OAuth token
        token = frappe.get_doc({
            "doctype": "OAuth Bearer Token",
            "client": get_oauth_client_id(),
            "user": user,
            "scopes": "openid profile email",
            "access_token": frappe.generate_hash(length=32),
            "refresh_token": frappe.generate_hash(length=32),
            "expires_in": 3600
        })
        token.insert(ignore_permissions=True)
        frappe.db.commit()

        user_doc = frappe.get_doc("User", user)
        return {
            "success": True,
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_in": token.expires_in,
            "user": {
                "email": user_doc.email,
                "full_name": user_doc.full_name,
                "user_image": user_doc.user_image
            }
        }

    except Exception as e:
        frappe.log_error(f"OAuth token exchange failed: {str(e)}")
        return {"success": False, "error": str(e)}

def create_user_from_google(code):
    """
    Create a new Frappe user from Google OAuth data.
    """
    # Get user info from Google
    from frappe.utils.oauth import get_oauth2_providers
    provider = get_oauth2_providers().get("google")
    if not provider:
        frappe.throw("Google OAuth provider not configured")

    # Exchange code for access token and get user info
    import requests
    token_data = {
        "client_id": provider.get("client_id"),
        "client_secret": provider.get("client_secret"),
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": get_url("/api/method/frappe.integrations.oauth2_logins.login_via_google")
    }

    token_response = requests.post("https://oauth2.googleapis.com/token", data=token_data)
    token_json = token_response.json()

    if "access_token" not in token_json:
        frappe.throw("Failed to get access token from Google")

    # Get user info
    user_info_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token_json['access_token']}"}
    )
    user_info = user_info_response.json()

    # Create new user
    user = frappe.get_doc({
        "doctype": "User",
        "email": user_info.get("email"),
        "first_name": user_info.get("given_name") or user_info.get("name"),
        "last_name": user_info.get("family_name"),
        "username": frappe.scrub(user_info.get("email").split("@")[0]),
        "user_type": "Website User",
        "send_welcome_email": 1,
        "user_image": user_info.get("picture"),
        "enabled": 1
    })
    user.insert(ignore_permissions=True)
    frappe.db.commit()

    # Create contact
    create_contact(user.name, user.first_name, user.last_name, user.email)

    return user

def get_oauth_client_id():
    """Get OAuth Client ID for React app"""
    return frappe.db.get_value("OAuth Client", {"app_name": "React Demo App"}, "client_id")