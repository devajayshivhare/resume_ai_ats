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

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_date(text):
    text = text.lower()

    if "present" in text or "current" in text:
        return datetime.today()

    # match like "Nov 24", "Dec 2021"
    match = re.search(r'([a-zA-Z]+)\s*(\d{2,4})', text)
    if not match:
        return None

    month_str = match.group(1).lower()
    year_str = match.group(2)

    month = MONTHS.get(month_str[:3])
    if not month:
        return None

    year = int(year_str)
    if year < 100:
        year += 2000

    return datetime(year, month, 1)


def calculate_experience_years(experiences):
    total_months = 0

    for exp in experiences:
        duration = exp.get("duration", "")

        if "-" not in duration:
            continue

        start_str, end_str = duration.split("-", 1)

        start = parse_date(start_str)
        end = parse_date(end_str)

        if not start or not end:
            continue

        months = (end.year - start.year) * 12 + (end.month - start.month)
        if months > 0:
            total_months += months

    return round(total_months / 12, 2)


def index_resume(candidate_id, resume_text):
    # 1️⃣ Split resume into chunks
    chunks = chunk_text(resume_text)

    if not chunks:
        return

    # 2️⃣ Save chunks into Frappe (Resume Chunk DocType)
    chunk_docs = []
    for i, chunk in enumerate(chunks):
        doc = frappe.get_doc({
            "doctype": "Resume Chunk",
            "candidate": candidate_id,
            "chunk_index": i,
            "chunk_text": chunk
        })
        doc.insert(ignore_permissions=True)
        chunk_docs.append(doc)

    # 3️⃣ Create embeddings from chunk text
    embeddings = embed_texts([d.chunk_text for d in chunk_docs])

    # 4️⃣ Store embeddings in FAISS with Resume Chunk reference
    meta = []
    for doc in chunk_docs:
        meta.append({
            "candidate_id": candidate_id,
            "resume_chunk": doc.name  # 🔑 IMPORTANT
        })

    add_embeddings(embeddings, meta)


PROMPT = """
You are a resume parser.

Extract information and return ONLY valid JSON.
Do not add explanations.

Schema:
{
  "first_name": "",
  "last_name": "",
  "gender": "",
  "email": "",
  "phone": "",
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
"""


# ---------------------------------------------------
# Helper: Extract JSON safely from LLM output
# ---------------------------------------------------
def _extract_json(text):
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    return match.group(0)


def parse_with_llm(resume_text):
    model = get_gemini()

    prompt = PROMPT + "\n\nRESUME:\n" + resume_text

    result = model.generate_content(prompt)
    text = result.text.strip()

    # Gemini sometimes wraps JSON in ```json
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


# ---------------------------------------------------
# Resume Text Extraction
# ---------------------------------------------------
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


# ---------------------------------------------------
# API Endpoint
# ---------------------------------------------------
# @frappe.whitelist(allow_guest=True)

@frappe.whitelist(allow_guest=True)
def parse_resume():
    
    """
    POST API
    form-data:
      resume: <file>
    """
    user = frappe.session.user
    
    candidate_name = frappe.db.get_value("Candidates", {"user_id": user}, "name")
    if not candidate_name:
        return {"status": "error", "message": "Profile not found"}

    try:
        file = frappe.request.files.get("resume")
        if not file:
            frappe.throw("Resume file is required")

        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

        file_size = len(file.read())
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            frappe.throw("Resume file size must be less than or equal to 5 MB")
            
        ALLOWED_EXTENSIONS = (".pdf", ".docx", ".doc")

        if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
            frappe.throw("Only PDF or DOCX files are allowed")



        from frappe.utils.file_manager import save_file

        saved = save_file(
            file.filename,
            file.read(),
            None,
            None,
            is_private=True
        )

        file_path = frappe.get_site_path(
            "private", "files", saved.file_name
        )

        text = extract_text(file_path)
        if not text.strip():
            frappe.throw("Could not extract text from resume")
        
        # parsed = parse_with_llm(text)
        try:
            parsed = parse_with_llm(text)
            
        except Exception as e:
            frappe.throw("Resume parsing failed. Please upload a different file.")
            # frappe.log_error(
            #     "Parsed Resume JSON",
            #     frappe.get_traceback()
            # )
            # return

        experience_years = calculate_experience_years(parsed.get("experience", []))
    
        candidate = frappe.get_doc("Candidates", candidate_name)

        # -----------------------------
        # Update normal fields
        # -----------------------------
        candidate.first_name = parsed.get("first_name")
        candidate.last_name = parsed.get("last_name")
        candidate.gender = parsed.get("gender")
        candidate.email = parsed.get("email")
        candidate.phone = parsed.get("phone")
        candidate.skills = json.dumps(parsed.get("skills", []))
        candidate.education_new = json.dumps(parsed.get("education", []))
        candidate.college_name = parsed.get("education", [])[0].get("institution")
        candidate.degree_studying = parsed.get("education", [])[0].get("degree")
        candidate.joined_year = parsed.get("education", [])[0].get("year")
        candidate.experience_summary = json.dumps(parsed.get("experience", []))
        # candidate.raw_resume_text = frappe.as_json(parsed)
        candidate.resume_parsed_json = json.dumps(parsed)
        candidate.resume = saved.file_url
        candidate.experience_years = experience_years
        candidate.vector_indexed = 0

        # -----------------------------
        # 🔥 CHILD TABLE: skill_detail
        # -----------------------------
        candidate.set("skill_detail", [])  # clear existing skills

        for skill in parsed.get("skills", []):
            candidate.append("skill_detail", {
                "skill_name": skill,
                "proficiency": "Beginner"  # default
            })
            
        candidate.set("education_table", [])  # clear existing skills

        for education in parsed.get("education", []):
            candidate.append("education_table", {
                "degree": education.get("degree"),
                "institution": education.get("institution"),
                "year": education.get("year")
            })
            
        # -----------------------------
        # 🔥 CHILD TABLE: experience_table (NORMALIZED)
        # -----------------------------
        
        def normalize_duration(text: str) -> str:
            if not text:
                return ""

            return (
                text.replace("’", " ")
                    .replace("‘", " ")
                    .replace("–", "-")
                    .replace("—", "-")
                    .replace("to", "-")
                    .strip()
            )

        candidate.set("experience_table", [])  # clear existing experience

        for exp in parsed.get("experience", []):
            # duration = exp.get("duration", "")
            raw_duration = exp.get("duration", "")
            duration = normalize_duration(raw_duration)

            start_date = None
            end_date = None
            is_current = 0

            if "-" in duration:
                start_str, end_str = duration.split("-", 1)

                start_dt = parse_date(start_str.strip())
                end_dt = parse_date(end_str.strip())

                if start_dt:
                    start_date = start_dt.date()

                if end_dt:
                    if "present" in end_str.lower() or "current" in end_str.lower():
                        is_current = 1
                        end_date = None
                    else:
                        end_date = end_dt.date()

            candidate.append("experience_table", {
                "company_name": exp.get("company"),
                "role": exp.get("role"),
                "start_date": start_date,
                "end_date": end_date,
                "is_current": is_current,
                "description": ""  # optional, can fill via LLM later
            })


        candidate.save(ignore_permissions=True)
        frappe.db.commit()

        # return {"status": "success", "message": "Resume parsed successfully!"}
        frappe.response["message"] = {
            "status": "success",
            "message": "Resume parsed successfully!"
        }


    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Resume Parse Error")
        return {
            "success": False,
            "error": str(e)
        }
        