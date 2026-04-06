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

def index_resume(candidate_email, resume_text):
    frappe.log_error(
        title="Indexing Resume",
        message=f"Candidate Email: {candidate_email}"
    )

    # ✅ Step 1: Convert email → candidate name
    candidate_name = frappe.db.get_value(
        "User",
        {"email": candidate_email},
        "name"
    )

    # ✅ Step 2: If not exists → create candidate
    # if not candidate_name:
    #     candidate_doc = frappe.get_doc({
    #         "doctype": "Candidate",
    #         "email": candidate_email,
    #         "candidate_name": candidate_email  # adjust if needed
    #     })
    #     candidate_doc.insert(ignore_permissions=True)
    #     candidate_name = candidate_doc.name

    # ✅ Step 3: Delete old chunks
    frappe.db.delete("Resume Chunk", {"candidate": candidate_name})
    frappe.db.commit()

    # ✅ Step 4: Create chunks
    chunks = chunk_text(resume_text)
    if not chunks:
        return

    chunk_docs = []
    for i, chunk in enumerate(chunks):
        chunk_doc = frappe.get_doc({
            "doctype": "Resume Chunk",
            "candidate": candidate_name,  # ✅ FIXED
            "chunk_index": i,
            "chunk_text": chunk
        })
        chunk_doc.insert(ignore_permissions=True)
        chunk_docs.append(chunk_doc)

    frappe.db.commit()

    # ✅ Step 5: Embeddings
    embeddings = embed_texts([d.chunk_text for d in chunk_docs])

    meta = []
    for doc in chunk_docs:
        meta.append({
            "candidate_id": candidate_name,  # ✅ FIXED
            "resume_chunk": doc.name
        })

    add_embeddings(embeddings, meta)

# def index_resume(candidate_id, resume_text):
#     # 1️⃣ Split resume into chunks
#     chunks = chunk_text(resume_text)

#     if not chunks:
#         return

#     # 2️⃣ Save chunks into Frappe (Resume Chunk DocType)
#     chunk_docs = []
#     for i, chunk in enumerate(chunks):
#         doc = frappe.get_doc({
#             "doctype": "Resume Chunk",
#             "candidate": candidate_id,
#             "chunk_index": i,
#             "chunk_text": chunk
#         })
#         doc.insert(ignore_permissions=True)
#         chunk_docs.append(doc)

#     # 3️⃣ Create embeddings from chunk text
#     embeddings = embed_texts([d.chunk_text for d in chunk_docs])

#     # 4️⃣ Store embeddings in FAISS with Resume Chunk reference
#     meta = []
#     for doc in chunk_docs:
#         meta.append({
#             "candidate_id": candidate_id,
#             "resume_chunk": doc.name  # 🔑 IMPORTANT
#         })

#     add_embeddings(embeddings, meta)

# def parse_with_llm(resume_text):
#     model = get_gemini()

#     prompt = PROMPT + "\n\nRESUME:\n" + resume_text

#     result = model.generate_content(prompt)
#     text = result.text.strip()

#     if text.startswith("```"):
#         text = text.replace("```json", "").replace("```", "").strip()

#     return json.loads(text)


# # ---------------------------------------------------
# # Resume Text Extraction
# # ---------------------------------------------------
# def extract_text(file_path):
#     text = ""

#     if file_path.lower().endswith(".pdf"):
#         with pdfplumber.open(file_path) as pdf:
#             for page in pdf.pages:
#                 text += (page.extract_text() or "") + "\n"

#     elif file_path.lower().endswith(".docx"):
#         doc = docx.Document(file_path)
#         for p in doc.paragraphs:
#             text += p.text + "\n"

#     return text

import base64

def parse_with_gemini_file(file_path):
    model = get_gemini()

    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    prompt = PROMPT

    response = model.generate_content(
        [
            {"mime_type": "application/pdf", "data": pdf_bytes},
            prompt
        ]
    )
    
    # frappe.log_error(title="Resume Parser: Gemini Raw Response", message=f"response: {response}")

    text = response.text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)








# def resume(doc, method=None):
#     """
#     Auto parse resume after insert
#     Errors will appear in Desk → Error Log
#     """

#     logger = frappe.logger("resume_parser", allow_site=True)

#     logger.info("===== RESUME PARSER STARTED =====")
#     logger.info(f"Doc: {doc.name}")
#     logger.info(f"File URL: {doc.resume_file}")

#     try:
#         # ✅ check file attached
#         if not doc.resume_file:
#             logger.warning("No resume file attached.")
#             return

#         # ✅ avoid duplicate parsing
#         if doc.parse_status == "Parsed":
#             logger.info("Already parsed. Skipping.")
#             return

#         # ✅ resolve file path
#         try:
#             file_doc = frappe.get_doc("File", {"file_url": doc.resume_file})
#             file_path = file_doc.get_full_path()
#             logger.info(f"File path: {file_path}")
#         except Exception:
#             frappe.log_error(
#                 title="Resume Parser: File Lookup Failed",
#                 message=frappe.get_traceback()
#             )
#             doc.parse_status = "File Not Found"
#             doc.save(ignore_permissions=True)
#             return

#         # ✅ extract text
#         logger.info("Extracting text...")
#         text = extract_text(file_path)

#         if not text.strip():
#             frappe.log_error(
#                 title="Resume Parser: Text Extraction Failed",
#                 message=f"File: {file_path}"
#             )
#             doc.parse_status = "Extraction Failed"
#             doc.save(ignore_permissions=True)
#             return

#         logger.info(f"Text length: {len(text)}")

#         # ✅ parse via LLM
#         logger.info("Parsing with LLM...")
#         # parsed = parse_with_llm(text)
        
#         parsed = parse_with_gemini_file(file_path)

#         logger.info("Parsing completed")

#         # ✅ save result
#         doc.parsed_json = json.dumps(parsed, indent=2)
#         doc.parse_status = "Parsed"
#         doc.save(ignore_permissions=True)

#         logger.info("Resume parsed successfully")

#     except Exception as e:
#         # 🔴 visible in Desk → Error Log
#         frappe.log_error(
#             title=f"Resume Parser Failed: {doc.name}",
#             message=frappe.get_traceback()
#         )

#         doc.parse_status = "Failed"
#         doc.save(ignore_permissions=True)



#done by kartikey

# Move resume AI parsing to asynchronous background job

# This prevents the Next.js frontend from timing out (500 error) while waiting for the Gemini API to process the document. Replaced doc.save() with db_set() in the worker thread to ensure safe database updates without triggering infinite hook loops.

def resume(doc, method=None):
    """
    FAST HOOK: Returns instantly to Next.js, pushes heavy AI parsing to the background.
    """
    # 1. Set status instantly so frontend knows it is processing
    doc.db_set("parse_status", "Pending")
    
    # 2. Trigger your exact logic in the background
    frappe.enqueue(
        "resume_ai.api.resume.resume.process_resume_bg",
        doc_name=doc.name,
        queue="long",
        timeout=300
    )


def process_resume_bg(doc_name):
    """
    This is your exact original code, just running in the background!
    """
    doc = frappe.get_doc("Resume", doc_name)
    logger = frappe.logger("resume_parser", allow_site=True)

    logger.info("===== RESUME PARSER STARTED =====")
    logger.info(f"Doc: {doc.name}")
    logger.info(f"File URL: {doc.resume_file}")

    try:
        if not doc.resume_file:
            logger.warning("No resume file attached.")
            return

        if doc.parse_status == "Parsed":
            logger.info("Already parsed. Skipping.")
            return

        try:
            file_doc = frappe.get_doc("File", {"file_url": doc.resume_file})
            file_path = file_doc.get_full_path()
            logger.info(f"File path: {file_path}")
        except Exception:
            frappe.log_error(title="Resume Parser: File Lookup Failed", message=frappe.get_traceback())
            doc.db_set("parse_status", "File Not Found")
            return

        # logger.info("Extracting text...")
        # text = extract_text(file_path)

        # if not text.strip():
        #     frappe.log_error(title="Resume Parser: Text Extraction Failed", message=f"File: {file_path}")
        #     doc.db_set("parse_status", "Extraction Failed")
        #     return

        # logger.info(f"Text length: {len(text)}")
        logger.info("Sending resume to Gemini for parsing...")

        logger.info("Parsing with LLM...")
        parsed = parse_with_gemini_file(file_path)
        # frappe.log_error(title="Resume Parser: LLM Parsing Failed", message=f"parsed: {parsed}")
        logger.info("Parsing completed")
        
        # ✅ Calculate and inject into parsed JSON
        parsed["experience_years"] = calculate_experience_years(parsed.get("experience", []))


        # Use db_set instead of save() in background jobs to prevent infinite loops
        doc.db_set("parsed_json", json.dumps(parsed, indent=2))
        doc.db_set("parse_status", "Parsed")
        
        # ✅ Index resume into FAISS
        resume_text = json.dumps(parsed)  # use parsed JSON as text source
        index_resume(doc.profile, resume_text)
        # doc.db_set("vector_indexed", 1)  # Optional flag to indicate indexing done

        logger.info("Resume parsed successfully")

    except Exception as e:
        frappe.log_error(title=f"Resume Parser Failed: {doc.name}", message=frappe.get_traceback())
        doc.db_set("parse_status", "Failed")