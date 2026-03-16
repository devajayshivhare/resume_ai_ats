import frappe
import pdfplumber
import docx
import requests
import json
import re
# from resume_ai.chunker import chunk_text
# from resume_ai.embedder import embed_texts
# from resume_ai.vector_store import add_embeddings


# def index_resume(candidate_id, resume_text):
#     chunks = chunk_text(resume_text)

#     embeddings = embed_texts(chunks)
#     # query_embedding = embed_texts([question])[0]


#     meta = []
#     for i, chunk in enumerate(chunks):
#         meta.append({
#             "candidate_id": candidate_id,
#             "chunk_index": i,
#             "text": chunk
#         })

#     add_embeddings(embeddings, meta)


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


# ---------------------------------------------------
# Helper: Extract JSON safely from LLM output
# ---------------------------------------------------
def _extract_json(text):
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    return match.group(0)


# ---------------------------------------------------
# LLM Parsing (SAFE)
# ---------------------------------------------------
# def parse_with_llm(resume_text):
#     payload = {
#         # "model": "llama3",
#         "model": "phi3:mini",
#         "prompt": PROMPT + "\n\nRESUME:\n" + resume_text,
#         "stream": False
#     }

#     res = requests.post(
#         "http://localhost:11434/api/generate",
#         json=payload,
#         timeout=120
#     )

#     raw = res.json().get("response", "").strip()

#     if not raw:
#         frappe.throw("LLM returned empty response")

#     # Log raw output for debugging
#     frappe.logger().info(f"LLM RAW OUTPUT:\n{raw}")

#     json_text = _extract_json(raw)
#     if not json_text:
#         frappe.throw("Could not extract JSON from LLM response")

#     try:
#         return json.loads(json_text)
#     except json.JSONDecodeError:
#         frappe.throw("Invalid JSON returned by LLM")

def parse_with_llm(resume_text):

    resume_text = resume_text[:6000]

    payload = {
        "model": "phi3:mini",
        "prompt": PROMPT + "\n\nRESUME:\n" + resume_text,
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    res = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=180
    )

    raw = res.json().get("response", "").strip()

    frappe.logger().info(raw)

    json_text = _extract_json(raw)
    if not json_text:
        frappe.throw("Could not extract JSON")

    json_text = repair_json(json_text)

    data = json.loads(json_text)

    if "skills" in data:
        data["skills"] = normalize_skills(data["skills"])

    return data


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
@frappe.whitelist(allow_guest=True)
def resume_parse():
    """
    POST API
    form-data:
      resume: <file>
    """

    try:
        file = frappe.request.files.get("resume")
        if not file:
            frappe.throw("Resume file is required")

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
            
        parsed = parse_with_llm(text)

        # after extracting resume text
        # index_resume(candidate_id="TEMP-ID", resume_text=text)



        return {
            "success": True,
            "data": parsed
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Resume Parse Error")
        return {
            "success": False,
            "error": str(e)
        }


