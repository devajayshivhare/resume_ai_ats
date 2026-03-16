# import frappe
# import requests
# from frappe.utils import get_url

# @frappe.whitelist(allow_guest=True)
# def google_login(code):
#     # return "ok"
#     token_url = "https://oauth2.googleapis.com/token"

#     payload = {
#         "client_id": frappe.conf.google_client_id,
#         "client_secret": frappe.conf.google_client_secret,
#         "code": code,
#         "grant_type": "authorization_code",
#         "redirect_uri": get_url("/google-callback")
#     }
    
    
#     frappe.logger().info(payload, "google oauth")
#     frappe.throw("Unable to retrieve user information from Google")
#     token = requests.post(token_url, data=payload).json()
#     access_token = token.get("access_token")

#     if not access_token:
#         frappe.throw("Google token error")

#     userinfo = requests.get(
#         "https://www.googleapis.com/oauth2/v2/userinfo",
#         headers={"Authorization": f"Bearer {access_token}"}
#     ).json()

#     email = userinfo["email"]
#     name = userinfo["name"]

#     if not frappe.db.exists("User", email):
#         frappe.get_doc({
#             "doctype": "User",
#             "email": email,
#             "first_name": name,
#             "enabled": 1
#         }).insert(ignore_permissions=True)

#     frappe.local.login_manager.authenticate(email, None)
#     frappe.local.login_manager.post_login()

#     return {"success": True}
