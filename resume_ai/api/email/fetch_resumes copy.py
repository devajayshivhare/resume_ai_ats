import frappe
from frappe.utils.file_manager import save_file
from urllib.parse import unquote

@frappe.whitelist(allow_guest=True)
def fetch_email_resumes():

    communications = frappe.get_all(
        "Communication",
        filters={
            "communication_type": "Communication",
            "sent_or_received": "Received"
        },
        fields=["name", "sender", "subject"]
    )

    for comm in communications:
        try:
            # ✅ Skip already processed
            if frappe.db.get_value("Communication", comm.name, "custom_processed"):
                continue

            # ✅ Get attachments
            files = frappe.get_all(
                "File",
                filters={"attached_to_name": comm.name},
                fields=["name", "file_url", "file_name"]
            )

            # 🔥 KEY LOGIC: If NO attachment → DELETE EMAIL
            if not files:
                frappe.delete_doc("Communication", comm.name, ignore_permissions=True)
                frappe.db.commit()   # 🔥 IMPORTANT
                continue

            # 🔥 Optional: Only allow resume files
            valid_files = [
                f for f in files
                if f.file_name.lower().endswith((".pdf", ".doc", ".docx"))
            ]

            if not valid_files:
                frappe.delete_doc("Communication", comm.name, ignore_permissions=True)
                frappe.db.commit()   # 🔥 IMPORTANT
                continue

            # ✅ Process valid resumes
            for f in valid_files:

                resume_doc = frappe.get_doc({
                    "doctype": "Resume",
                    "candidate_name": f.file_name,
                    "email": comm.sender,
                    "resume_file": f.file_url,
                    "parse_status": "Pending"
                })

                resume_doc.insert(ignore_permissions=True, ignore_mandatory=True)

                frappe.db.commit()

                frappe.enqueue(
                    "resume_ai.api.resume.resume.process_resume_bg",
                    doc_name=resume_doc.name,
                    queue="long"
                )

            # ✅ Mark processed
            frappe.db.set_value("Communication", comm.name, "custom_processed", 1)

        except Exception:
            frappe.log_error(
                title="Email Resume Fetch Failed",
                message=frappe.get_traceback()
            )