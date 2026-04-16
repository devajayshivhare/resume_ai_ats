import frappe
# import pdfplumber
# import docx
import requests
import json
import re
from resume_ai.api.resume.chunker import chunk_text
from resume_ai.api.resume.embedder import embed_texts
from resume_ai.api.resume.vector_store import add_embeddings
from datetime import datetime
from resume_ai.api.resume.gemini import get_gemini

PROMPT = """
You are an advanced resume parsing engine.
Your task is to extract structured information from a resume.

Return ONLY valid JSON. Do NOT include explanations, markdown blocks, comments, or extra text.
If any field is missing, return an empty string "" or empty array [].

Normalize and clean extracted data:
- Capitalize names properly.
- Remove duplicate skills.
- Format phone numbers in international format (e.g., +919876543210).
- Extract only real technical/hard skills (ignore soft filler words like "Teamwork").
- Infer gender only if clearly identifiable from the name; otherwise leave empty.

Schema:
{
  "first_name": "",
  "last_name": "",
  "gender": "",
  "email": "",
  "phone": "",
  "skills": [
    {
      "skill_name": "",
      "proficiency": "Intermediate" 
    }
  ],
  "education": [
    {
      "degree": "",
      "institution": "",
      "year": ""
    }
  ],
  "experience": [
    {
      "company_name": "",
      "role": "",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "is_current": false,
      "description": ""
    }
  ]
}

Rules:
- For skills, default proficiency to "Intermediate" unless clearly stated otherwise.
- Extract the most recent education and experience first.
- If an experience is current/present, set "is_current" to true and "end_date" to "".
- If exact dates are unknown, use the first day of the month (e.g., "YYYY-MM-01") or year ("YYYY-01-01").
- Do not guess missing details. Do not fabricate data.
"""

from datetime import datetime

def calculate_experience_years(experiences):
    total_months = 0

    for exp in experiences:
        is_current = exp.get("is_current", False)
        start_str = exp.get("start_date", "")
        end_str = exp.get("end_date", "")

        if not start_str:
            continue

        try:
            start = datetime.strptime(start_str, "%Y-%m-%d")
        except ValueError:
            continue

        if is_current or not end_str:
            end = datetime.today()
        else:
            try:
                end = datetime.strptime(end_str, "%Y-%m-%d")
            except ValueError:
                continue

        months = (end.year - start.year) * 12 + (end.month - start.month)
        if months > 0:
            total_months += months

    return round(total_months / 12, 2)

def index_resume(resume_id, resume_text):
    # ✅ Step 1: Delete old chunks ONLY for this specific resume document
    frappe.db.delete("Resume Chunk", {"resume_id": resume_id})
    frappe.db.commit()

    # ✅ Step 2: Create chunks
    chunks = chunk_text(resume_text)
    if not chunks:
        return

    chunk_docs = []
    for i, chunk in enumerate(chunks):
        chunk_doc = frappe.get_doc({
            "doctype": "Resume Chunk",
            "resume_id": resume_id,  # Link directly to the Resume DocType
            "chunk_index": i,
            "chunk_text": chunk
        })
        chunk_doc.insert(ignore_permissions=True)
        chunk_docs.append(chunk_doc)

    frappe.db.commit()

    # ✅ Step 3: Embeddings
    embeddings = embed_texts([d.chunk_text for d in chunk_docs])

    meta = []
    for doc in chunk_docs:
        meta.append({
            "resume_id": resume_id,  # Store the Resume ID in FAISS
            "resume_chunk": doc.name
        })

    add_embeddings(embeddings, meta)



# import base64

# def parse_with_gemini_file(file_path):
#     model = get_gemini()

#     with open(file_path, "rb") as f:
#         pdf_bytes = f.read()

#     prompt = PROMPT

#     response = model.generate_content(
#         [
#             {"mime_type": "application/pdf", "data": pdf_bytes},
#             prompt
#         ]
#     )
    
#     text = response.text.strip()

#     if text.startswith("```"):
#         text = text.replace("```json", "").replace("```", "").strip()

#     return json.loads(text)

# def resume(doc, method=None):
#     """
#     FAST HOOK: Returns instantly to Next.js, pushes heavy AI parsing to the background.
#     """
#     # 1. Set status instantly so frontend knows it is processing
#     doc.db_set("parse_status", "Pending")
    
#     # 2. Trigger your exact logic in the background
#     frappe.enqueue(
#         "resume_ai.api.resume.resume.process_resume_bg",
#         doc_name=doc.name,
#         queue="long",
#         timeout=300
#     )


def flatten_resume_data(parsed):
    return {
        # "candidate_name": f"{parsed.get('first_name', '')} {parsed.get('last_name', '')}".strip(),

        "experience_years": parsed.get("experience_years", 0),
        "location": parsed.get("location", 0),

        "skills": ", ".join([
            s.get("skill_name", "") for s in parsed.get("skills", [])
        ]),

        "current_role": (
            parsed.get("experience", [{}])[0].get("role", "")
            if parsed.get("experience") else ""
        ),

        "degree": (
            parsed.get("education", [{}])[0].get("degree", "")
            if parsed.get("education") else ""
        ),

        "institution": (
            parsed.get("education", [{}])[0].get("institution", "")
            if parsed.get("education") else ""
        )
        
    }
    
def index_resume_bg(resume_id, resume_text):
    frappe.log_error("Embedding started...")
    index_resume(resume_id, resume_text)
    
def create_resume_from_upload(applicant_data, file_url, job_opening=None, applicant_doc=None):
    # import json

    # ✅ Avoid duplicate resume
    # email = applicant_data.get("email") or applicant_data.get("email_id")
    # if email and frappe.db.exists("Resume", {"email": email}):
    #     return
    
    # ✅ Calculate and inject into parsed JSON
    # applicant_data["experience_years"] = calculate_experience_years(applicant_data.get("experience", []))

    # ✅ Create Resume Doc
    # doc = frappe.get_doc({
    #     "doctype": "Resume",
    #     "candidate_name": applicant_data.get("applicant_name"),
    #     "email": email,
    #     "phone": applicant_data.get("phone_number") or applicant_data.get("phone"),
    #     "resume_file": file_url,

    #     # 🔥 Most important for AI
    #     "parsed_json": json.dumps(applicant_data),

    #     "parse_status": "Parsed"  # already parsed
    # })

    # doc.insert(ignore_permissions=True)
    
    

    # ✅ Flatten data (reuse your logic)
    # flat_data = flatten_resume_data(applicant_data)

    # doc.db_set("experience_years", flat_data["experience_years"])
    # doc.db_set("location", flat_data["location"])
    # doc.db_set("skills", flat_data["skills"])
    # doc.db_set("current_role", flat_data["current_role"])
    # doc.db_set("degree", flat_data["degree"])
    # doc.db_set("institution", flat_data["institution"])

    # ✅ Direct embedding (NO Gemini again)
    resume_text = json.dumps(applicant_data)
    # index_resume(doc.name, resume_text)
    # return resume_text
    
    frappe.enqueue(
        "resume_ai.api.resume.resume.index_resume_bg",
        resume_id=applicant_doc.name,
        resume_text=resume_text,
        queue="long",
        timeout=300
    )

    return applicant_doc.name



# def process_resume_bg(doc_name):
#     """
#     This is your exact original code, just running in the background!
#     """
#     doc = frappe.get_doc("Resume", doc_name)
#     logger = frappe.logger("resume_parser", allow_site=True)

#     logger.info("===== RESUME PARSER STARTED =====")
#     logger.info(f"Doc: {doc.name}")
#     logger.info(f"File URL: {doc.resume_file}")

#     try:
#         if not doc.resume_file:
#             logger.warning("No resume file attached.")
#             return

#         if doc.parse_status == "Parsed":
#             logger.info("Already parsed. Skipping.")
#             return

#         try:
#             file_doc = frappe.get_doc("File", {"file_url": doc.resume_file})
#             file_path = file_doc.get_full_path()
#             logger.info(f"File path: {file_path}")
#         except Exception:
#             frappe.log_error(title="Resume Parser: File Lookup Failed", message=frappe.get_traceback())
#             doc.db_set("parse_status", "File Not Found")
#             return

        
#         logger.info("Sending resume to Gemini for parsing...")

#         logger.info("Parsing with LLM...")
#         parsed = parse_with_gemini_file(file_path)
#         logger.info("Parsing completed")
        
#         # ✅ Calculate and inject into parsed JSON
#         parsed["experience_years"] = calculate_experience_years(parsed.get("experience", []))
        
#         flat_data = flatten_resume_data(parsed)

#         # ✅ Save flattened fields
#         # doc.db_set("candidate_name", flat_data["candidate_name"])
#         doc.db_set("experience_years", flat_data["experience_years"])
#         doc.db_set("skills", flat_data["skills"])
#         doc.db_set("current_role", flat_data["current_role"])
#         doc.db_set("degree", flat_data["degree"])
#         doc.db_set("institution", flat_data["institution"])


#         # Use db_set instead of save() in background jobs to prevent infinite loops
#         doc.db_set("parsed_json", json.dumps(parsed, indent=2))
#         doc.db_set("parse_status", "Parsed")
        
#         # ✅ Index resume into FAISS
#         resume_text = json.dumps(parsed)  # use parsed JSON as text source
#         index_resume(doc.name, resume_text)
#         # frappe.enqueue(
#         #     "resume_ai.api.resume.resume.index_resume_bg",
#         #     resume_id=doc.name,
#         #     resume_text=resume_text,
#         #     queue="long",
#         #     timeout=300
#         # )

#         logger.info("Resume parsed successfully")

#     except Exception as e:
#         frappe.log_error(title=f"Resume Parser Failed: {doc.name}", message=frappe.get_traceback())
#         doc.db_set("parse_status", "Failed")