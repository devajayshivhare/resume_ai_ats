import frappe
import pdfplumber
import docx
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

Return ONLY valid JSON.
Do NOT include explanations, comments, or extra text.

If any field is missing, return an empty string "" or empty array [].

Normalize and clean extracted data:
- Capitalize names properly.
- Remove duplicate skills.
- Format phone numbers in international format if possible.
- Extract only real skills (ignore soft filler words).
- Parse education and experience even if formatting is inconsistent.
- Infer gender only if clearly identifiable from the name; otherwise leave empty.

Extract data even if:
- formatting is broken
- sections are unordered
- headings are missing
- bullet points are inconsistent
- information appears in paragraphs

Schema:
{
  "first_name": "",
  "last_name": "",
  "gender": "",
  "email": "",
  "phone": "",
  "address": "",
  "skills": [],
  "education": [
    {
      "degree": "",
      "institution": "",
      "year": ""
    }
  ],
  "experience": [
    {
      "company": "",
      "role": "",
      "duration": ""
    }
  ]
}

Rules:
- Extract the most recent education first.
- Extract the most recent experience first.
- Skills must be concise keywords.
- Do not guess missing details.
- Do not fabricate data.
"""

def parse_with_llm(resume_text):
    model = get_gemini()

    prompt = PROMPT + "\n\nRESUME:\n" + resume_text

    result = model.generate_content(prompt)
    text = result.text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


# # ---------------------------------------------------
# # Resume Text Extraction
# # ---------------------------------------------------
def extract_text(file_path):
    text = ""

    if file_path.lower().endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"

    elif file_path.lower().endswith(".docx"):
        doc = docx.Document(file_path)
        for p in doc.paragraphs:
            text += p.text + "\n"

    return text

def resume(doc, method=None):
    """
    Auto parse resume after insert
    Errors will appear in Desk → Error Log
    """

    logger = frappe.logger("resume_parser", allow_site=True)

    logger.info("===== RESUME PARSER STARTED =====")
    logger.info(f"Doc: {doc.name}")
    logger.info(f"File URL: {doc.resume_file}")

    try:
        # ✅ check file attached
        if not doc.resume_file:
            logger.warning("No resume file attached.")
            return

        # ✅ avoid duplicate parsing
        if doc.parse_status == "Parsed":
            logger.info("Already parsed. Skipping.")
            return

        # ✅ resolve file path
        try:
            file_doc = frappe.get_doc("File", {"file_url": doc.resume_file})
            file_path = file_doc.get_full_path()
            logger.info(f"File path: {file_path}")
        except Exception:
            frappe.log_error(
                title="Resume Parser: File Lookup Failed",
                message=frappe.get_traceback()
            )
            doc.parse_status = "File Not Found"
            doc.save(ignore_permissions=True)
            return

        # ✅ extract text
        logger.info("Extracting text...")
        text = extract_text(file_path)

        if not text.strip():
            frappe.log_error(
                title="Resume Parser: Text Extraction Failed",
                message=f"File: {file_path}"
            )
            doc.parse_status = "Extraction Failed"
            doc.save(ignore_permissions=True)
            return

        logger.info(f"Text length: {len(text)}")

        # ✅ parse via LLM
        logger.info("Parsing with LLM...")
        parsed = parse_with_llm(text)

        logger.info("Parsing completed")

        # ✅ save result
        doc.parsed_json = json.dumps(parsed, indent=2)
        doc.parse_status = "Parsed"
        doc.save(ignore_permissions=True)

        logger.info("Resume parsed successfully")

    except Exception as e:
        # 🔴 visible in Desk → Error Log
        frappe.log_error(
            title=f"Resume Parser Failed: {doc.name}",
            message=frappe.get_traceback()
        )

        doc.parse_status = "Failed"
        doc.save(ignore_permissions=True)