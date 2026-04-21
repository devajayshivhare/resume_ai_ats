from resume.resume.doctype.pdf_upload.pdf_upload import _extract_and_parse_file
from resume_ai.api.resume.resume import (
    calculate_experience_years,
    flatten_resume_data,
    create_resume_from_upload
)
import os
import json
import frappe

@frappe.whitelist(allow_guest=True)
def fetch_email_resumes():

    communications = frappe.get_all(
        "Communication",
        filters={
            "communication_type": "Communication",
            "sent_or_received": "Received",
            # "email_account": "ajayshivhare047@gmail.com"
            "email_account": "Ajayshivhare047"
        },
        fields=["name", "sender", "subject"]
    )
    
    # return {"communications": communications}

    for comm in communications:
        try:
            if frappe.db.get_value("Communication", comm.name, "custom_processed"):
                continue

            files = frappe.get_all(
                "File",
                filters={"attached_to_name": comm.name},
                fields=["name", "file_url", "file_name"]
            )
            
            # frappe.log_error(
            #     title="Email Resume Fetch",
            #     message=f"Processing Communication: {comm.name} with files: {files}"
            # )


            if not files:
                frappe.delete_doc("Communication", comm.name, ignore_permissions=True)
                frappe.db.commit()
                continue

            valid_files = [
                f for f in files
                if f.file_name.lower().endswith((".pdf", ".doc", ".docx"))
            ]

            if not valid_files:
                frappe.delete_doc("Communication", comm.name, ignore_permissions=True)
                frappe.db.commit()
                continue

            for f in valid_files:
                try:
                    # ✅ Get file path
                    file_doc = frappe.get_doc("File", {"file_url": f.file_url})
                    file_path = file_doc.get_full_path()

                    ext = os.path.splitext(file_path)[1].lower()

                    # ✅ Load prompt
                    prompt_path = frappe.get_app_path(
                        "resume", "resume", "doctype", "pdf_upload", "resume_prompt.txt"
                    )
                    with open(prompt_path, "r") as pf:
                        prompt_template = pf.read()

                    api_key = frappe.conf.get("gemini_api_key")

                    # ✅ Parse (same as upload flow)
                    _fu, applicant_data, err = _extract_and_parse_file((
                        file_path,
                        f.file_url,
                        None,
                        None,
                        ext,
                        api_key,
                        prompt_template,
                    ))

                    if isinstance(applicant_data, str):
                        try:
                            applicant_data = json.loads(applicant_data)
                        except:
                            continue

                    if err or not applicant_data:
                        continue

                    # ✅ Normalize fields
                    if "email_id" in applicant_data and "email" not in applicant_data:
                        applicant_data["email"] = applicant_data["email_id"]

                    if "phone_number" in applicant_data and "phone" not in applicant_data:
                        applicant_data["phone"] = applicant_data["phone_number"]

                    applicant_name = (
                        applicant_data.get("applicant_name")
                        or applicant_data.get("name")
                        or applicant_data.get("full_name")
                    )

                    email_value = applicant_data.get("email")

                    if not applicant_name or not email_value:
                        continue

                    # ✅ Duplicate check
                    if frappe.db.exists("Job Applicant", {"email_id": email_value}):
                        continue

                    # ✅ Process data
                    applicant_data["experience_years"] = calculate_experience_years(
                        applicant_data.get("experience", [])
                    )

                    flat_data = flatten_resume_data(applicant_data)

                    # ✅ Create Job Applicant
                    applicant = frappe.get_doc({
                        "doctype": "Job Applicant",
                        "applicant_name": applicant_name,
                        "email_id": email_value,
                        "resume_attachment": f.file_url,
                        "status": "Open",
                        "phone_number": applicant_data.get("phone", ""),
                        "custom_parsed_json": json.dumps(applicant_data),
                        "custom_parse_status": "Parsed",
                        "custom_experience_years": flat_data["experience_years"],
                        # "custom_location": flat_data["location"],
                        "current_location": flat_data["location"],
                        "custom_skills": flat_data["skills"],
                        "custom_current_role": flat_data["current_role"],
                        "custom_degree": flat_data["degree"],
                        "custom_institution": flat_data["institution"],
                    })
                    
                    frappe.log_error(
                        title="Creating Job Applicant",
                        message=f"Creating applicant for {applicant_name} with applicant {applicant}"
                    )
                    
                    # return {"success": True, "applicant": applicant.as_dict()}

                    applicant.insert(ignore_permissions=True)
                    frappe.db.commit()

                    # ✅ Optional: create Resume embeddings (NO Gemini)
                    # create_resume_from_upload(
                    #     applicant_data=applicant_data,
                    #     file_url=f.file_url,
                    #     applicant_doc=applicant
                    # )
                    
                    try:
                        create_resume_from_upload(
                            applicant_data=applicant_data,
                            file_url=f.file_url,
                            applicant_doc=applicant
                        )
                    except Exception:
                        frappe.log_error(
                            message=frappe.get_traceback(),   # ✅ REAL ERROR
                            title=f"Resume Error: {applicant.name}"
                        )

                except Exception:
                    frappe.log_error(
                        title="Resume Processing Failed",
                        message=frappe.get_traceback()
                    )
            frappe.log_error(
                        title="Communication Processed",
                        message=comm.name
                    )
            frappe.db.set_value("Communication", comm.name, "custom_processed", 1)
            frappe.db.commit()

        except Exception:
            frappe.log_error(
                title="Email Resume Fetch Failed",
                message=frappe.get_traceback()
            )