import frappe
import json
import requests
from resume_ai.api.resume.embedder import embed_texts
from resume_ai.api.resume.vector_store import search_similar
from resume_ai.api.resume.gemini import get_gemini

def chat_with_llm(context, question):
    model = get_gemini()

    prompt = f"""
You are an resume intelligence AI assistant. You help recruiters find and evaluate candidates based on their resumes.

You can answer questions about:
- Candidate skills and experience
- Education and qualifications  
- Work history and roles
- Comparing candidates
- Answer ONLY questions relevant to recruitment decisions (skills, experience, education)
- Do NOT volunteer candidate personal details (email, phone, address) unless explicitly asked
- Do NOT reveal candidate names unless directly asked about a specific person
- If asked for contact details, say: "Please access candidate contact info through the official profile page"
- If the answer is not found in the resumes, say: "Not found in the uploaded resumes."

If the question is not related to the resume data provided, politely explain what types of questions you can answer.
If the answer is not found in the resumes, say: "Not found in the uploaded resumes."

Context:
{context}

Question:
{question}
"""
    result = model.generate_content(prompt)
    return result.text.strip()

import frappe
import json
from resume_ai.api.resume.embedder import embed_texts
from resume_ai.api.resume.vector_store import search_similar

@frappe.whitelist(allow_guest=True)
def chat_query(question=None, filters=None, response_format="text"):
    # Only allow recruiters/admins
    # if frappe.session.user == "Guest":
    #     frappe.throw("Authentication required", frappe.AuthenticationError)
    
    # allowed_roles = ["System Manager", "Recruiter"]  # add your recruiter role
    # user_roles = frappe.get_roles(frappe.session.user)
    
    # if not any(role in user_roles for role in allowed_roles):
    #     frappe.throw("Not permitted", frappe.PermissionError)
    try:
        
        # -----------------------------
        # 0️⃣ Normalize inputs
        # -----------------------------
        if isinstance(filters, str):
            filters = json.loads(filters)

        filters = filters or {}

        # -----------------------------
        # 1️⃣ Validate question
        # -----------------------------
        if not question:
            return {
                "success": False,
                "error": "Question is required"
            }

        # -----------------------------
        # 2️⃣ Fetch candidates (structured filtering)
        # -----------------------------
        candidate_filters = {}

        if filters.get("status") and filters["status"] != "Any":
            candidate_filters["status"] = filters["status"]

        candidates = frappe.get_all("User", fields=["name", "first_name", "last_name"])
        if not candidates:
            return {
                "success": True,
                "answer": "No candidates found.",
                "sources": []
            }
        candidate_map = {
            c["name"]: f"{c['first_name'] or ''} {c['last_name'] or ''}".strip()
            for c in candidates
        }
        
        if response_format == "table":
            rows = []
            for c in candidates:
                parsed = json.loads(c.get("parsed_json") or "{}")
                rows.append({
                    "name": f"{parsed.get('first_name', '')} {parsed.get('last_name', '')}".strip(),
                    "email": parsed.get("email", ""),
                    "phone": parsed.get("phone", ""),
                    "skills": [s["skill_name"] for s in parsed.get("skills", [])]
                })
            return {
                "success": True,
                "format": "table",
                "columns": ["Name", "Email", "Phone", "Skills"],
                "rows": rows
            }

        query_vector = embed_texts([question])[0]
        matches = search_similar(query_vector, top_k=10)
        frappe.log_error(title="Vector Matches Debug", message=f"Matches: {matches}\nCandidate map keys: {list(candidate_map.keys())}")
        matches = [
            m for m in matches
            if m.get("candidate_id") in candidate_map
        ][:5]

        if not matches:
            return {
                "success": True,
                "answer": "No relevant information found in the selected profiles.",
                "sources": []
            }

        chunk_ids = [m["resume_chunk"] for m in matches]

        chunks = frappe.get_all(
            "Resume Chunk",
            filters={"name": ["in", chunk_ids]},
            fields=["chunk_text", "candidate"]
        )

        # Build grounded context
        context = "\n\n".join(
            f"Candidate: {candidate_map.get(c['candidate'], c['candidate'])}\n{c['chunk_text']}"
            for c in chunks
        )

        # Deduplicate sources
        unique_sources = {}
        for c in chunks:
            unique_sources[c["candidate"]] = {
                "candidate": candidate_map.get(c["candidate"], c["candidate"])
            }

        answer = chat_with_llm(context, question)

        return {
            "success": True,
            "answer": answer,
            "sources": list(unique_sources.values())
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Chat API Error")
        return {
            "success": False,
            "error": str(e)
        }
