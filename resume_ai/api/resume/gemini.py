import google.generativeai as genai
import frappe

def get_gemini():
    api_key = frappe.conf.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    # return genai.GenerativeModel("gemini-2.5-flash")
    return genai.GenerativeModel("gemini-2.5-pro")
    # return genai.GenerativeModel("gemini-3-pro-preview")
