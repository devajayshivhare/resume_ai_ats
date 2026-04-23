import frappe
import subprocess
import shutil

def after_install():
    # setup_defaults()
    set_site_config_defaults()                                          
    try_setup_ollama()
    check_gemini_config()               


# def setup_defaults():
#     # ✅ Default config
#     frappe.db.set_default("ai_mode", "hybrid")
#     frappe.db.set_default("ollama_model", "gemma4:e2b")
#     frappe.db.set_default("ollama_host", "http://localhost:11434")
#     frappe.db.set_default("email_account", "YOUR_EMAIL_ACCOUNT")  # <-- Set your default email account here

#     frappe.db.commit()

#     frappe.log_error("Setup", "Default AI config applied")

def set_site_config_defaults():
    config_updates = {
        "ai_mode": "hybrid",
        "ollama_model": "gemma4:e2b",
        "ollama_host": "http://localhost:11434",
        "email_account": "YOUR_EMAIL_ACCOUNT"
    }

    for key, value in config_updates.items():
        # Only set if not already present
        if not frappe.conf.get(key):
            frappe.utils.set_site_config(key, value)

    frappe.log_error("Setup", "AI config added to site_config.json")

def try_setup_ollama():
    """
    Safe Ollama setup (non-blocking, no crash)
    """

    # ✅ Step 1: Check if ollama exists in system PATH
    if not shutil.which("ollama"):
        frappe.log_error(
            title="Ollama Not Found",
            message="Ollama is not installed. Skipping setup."
        )
        return False

    try:
        # ✅ Step 2: Check version (safe)
        subprocess.run(["ollama", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # ✅ Step 3: Pull model (async, non-blocking)
        subprocess.Popen(
            ["ollama", "pull", "gemma4:e2b"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        frappe.log_error(
            title="Ollama Setup",
            message="Ollama detected. Model pull started."
        )

        return True

    except Exception as e:
        frappe.log_error(
            title="Ollama Setup Failed",
            message=str(e)
        )
        return False


def check_gemini_config():
    if not frappe.conf.get("gemini_api_key"):
        frappe.log_error(
            "Gemini Setup",
            "Gemini API key missing. Please add in site_config.json"
        )