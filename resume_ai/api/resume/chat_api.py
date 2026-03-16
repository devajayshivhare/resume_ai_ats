import frappe
import json
import requests
from resume_ai.api.resume.embedder import embed_texts
from resume_ai.api.resume.vector_store import search_similar
from resume_ai.api.resume.gemini import get_gemini

# CHAT_PROMPT = """
# You are an AI recruiter assistant.

# Answer the user's question using ONLY the resume information provided below.
# If the answer is not found in the resumes, say:
# "Not found in the uploaded resumes."

# Resume Data:
# {context}

# User Question:
# {question}

# """


# def chat_with_llm(context, question):
#     prompt = CHAT_PROMPT.format(
#         context=context,
#         question=question
#     )

#     payload = {
#         "model": "llama3",
#         "prompt": prompt,
#         "stream": False
#     }

#     res = requests.post(
#         "http://localhost:11434/api/generate",
#         json=payload,
#         timeout=120
#     )

#     return res.json().get("response", "").strip()

def chat_with_llm(context, question):
    model = get_gemini()

    prompt = f"""
You are an AI recruiter assistant.

Answer the user's question using ONLY the resume information provided below.
If the answer is not found in the resumes, say:
"Not found in the uploaded resumes."

Context:
{context}

Question:
{question}
"""
#     prompt = f"""
# You are a hiring assistant.

# Only answer using the context below.

# Context:
# {context}

# Question:
# {question}
# """

    result = model.generate_content(prompt)
    return result.text.strip()


# @frappe.whitelist(allow_guest=True)
# def chat_query(question=None):
#     try:
#         if not question:
#             return {
#                 "success": False,
#                 "error": "Question is required"
#             }

#         from resume_ai.api.resume.embedder import embed_texts
#         from resume_ai.api.resume.vector_store import search_similar
        

#         query_vector = embed_texts([question])[0]
#         matches = search_similar(query_vector, top_k=5)

#         if not matches:
#             return {
#                 "success": True,
#                 "answer": "Not found in the uploaded resumes.",
#                 "sources": []
#             }

#         # fetch Resume Chunk text
#         chunk_ids = [m["resume_chunk"] for m in matches]

#         chunks = frappe.get_all(
#             "Resume Chunk",
#             filters={"name": ["in", chunk_ids]},
#             fields=["chunk_text", "candidate"]
#         )

#         context = "\n\n".join(c["chunk_text"] for c in chunks)

#         answer = chat_with_llm(context, question)

#         return {
#             "success": True,
#             "answer": answer,
#             "sources": chunks
#         }

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Chat Query Error")
#         return {
#             "success": False,
#             "error": str(e)
#         }


# import frappe
# import json
# from resume_ai.api.resume.embedder import embed_texts
# from resume_ai.api.resume.vector_store import search_similar
# from resume_ai.api.resume.llm import chat_with_llm   # adjust import if your function lives elsewhere


# @frappe.whitelist(allow_guest=True)
# def chat_query(question=None, filters=None):
#     """
#     Profile-based Resume Chat API

#     Input JSON:
#     {
#       "question": "Who has Jira experience?",
#       "filters": {
#         "skills": ["Jira", "Python"],
#         "min_experience": 3,
#         "max_experience": 6,
#         "status": "Shortlisted"
#       }
#     }
#     """

#     try:
#         # -----------------------------
#         # 1️⃣ Validate input
#         # -----------------------------
#         if not question:
#             return {
#                 "success": False,
#                 "error": "Question is required"
#             }

#         # Frappe may pass filters as JSON string
#         if isinstance(filters, str):
#             filters = json.loads(filters)

#         filters = filters or {}

#         # -----------------------------
#         # 2️⃣ Fetch candidates using structured filters
#         # -----------------------------
#         candidate_filters = {}

#         if filters.get("status"):
#             candidate_filters["status"] = filters["status"]

#         candidates = frappe.get_all(
#             "Candidate",
#             filters=candidate_filters,
#             fields=["name", "skills", "experience_years"]
#         )

#         # -----------------------------
#         # 3️⃣ Apply skill + experience filtering
#         # -----------------------------
#         filtered_candidate_ids = []

#         for c in candidates:
#             # ---- Skills filter ----
#             if filters.get("skills"):
#                 candidate_skills = [
#                     s.strip().lower()
#                     for s in (c.skills or "").split(",")
#                     if s.strip()
#                 ]

#                 if not all(
#                     skill.lower() in candidate_skills
#                     for skill in filters["skills"]
#                 ):
#                     continue

#             # ---- Experience filter ----
#             exp = c.experience_years or 0

#             if filters.get("min_experience") is not None:
#                 if exp < filters["min_experience"]:
#                     continue

#             if filters.get("max_experience") is not None:
#                 if exp > filters["max_experience"]:
#                     continue

#             filtered_candidate_ids.append(c.name)

#         # -----------------------------
#         # 4️⃣ No matching profiles
#         # -----------------------------
#         if not filtered_candidate_ids:
#             return {
#                 "success": True,
#                 "answer": "No candidates match the selected profile filters.",
#                 "sources": []
#             }

#         # -----------------------------
#         # 5️⃣ Vector search (FAISS)
#         # -----------------------------
#         query_vector = embed_texts([question])[0]
#         matches = search_similar(query_vector, top_k=10)

#         # Restrict FAISS results to filtered candidates
#         matches = [
#             m for m in matches
#             if m.get("candidate_id") in filtered_candidate_ids
#         ][:5]

#         if not matches:
#             return {
#                 "success": True,
#                 "answer": "No relevant information found in the selected profiles.",
#                 "sources": []
#             }

#         # -----------------------------
#         # 6️⃣ Fetch Resume Chunks from Frappe
#         # -----------------------------
#         chunk_ids = [m["resume_chunk"] for m in matches]

#         chunks = frappe.get_all(
#             "Resume Chunk",
#             filters={"name": ["in", chunk_ids]},
#             fields=["chunk_text", "candidate"]
#         )

#         # context = "\n\n".join(c["chunk_text"] for c in chunks)
        
#         # context = "\n\n".join(
#         # f"Candidate: {c['candidate']}\n{c['chunk_text']}"
#         # for c in chunks
#         # )
#         context = "\n\n".join(
#         f"Candidate: {candidate_map.get(c['candidate'], c['candidate'])}\n{c['chunk_text']}"
#         for c in chunks
#         )
        
#         # 🔁 Deduplicate sources by candidate
#         unique_sources = {}
#         for c in chunks:
#             unique_sources[c["candidate"]] = {
#                 "candidate": candidate_map.get(c["candidate"], c["candidate"])
#             }

#         sources = list(unique_sources.values())

#         # -----------------------------
#         # 7️⃣ Ask LLM (grounded)
#         # -----------------------------
#         answer = chat_with_llm(context, question)

#         return {
#             "success": True,
#             "answer": answer,
#             "sources": sources
#         }

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Profile Based Chat Error")
#         return {
#             "success": False,
#             "error": str(e)
#         }

# @frappe.whitelist(allow_guest=True)
# def chat_query(question=None, filters=None):
#     try:
#         # -----------------------------
#         # 0️⃣ Candidate map (DEFINE FIRST – NEVER FAILS)
#         # -----------------------------
#         candidate_map = {
#             c.name: c.full_name
#             for c in frappe.get_all("Candidate", fields=["name", "full_name"])
#         }

#         # -----------------------------
#         # 1️⃣ Validate input
#         # -----------------------------
#         if not question:
#             return {
#                 "success": False,
#                 "error": "Question is required"
#             }

#         if isinstance(filters, str):
#             filters = json.loads(filters)

#         filters = filters or {}

#         # -----------------------------
#         # 2️⃣ Fetch candidates (structured filtering)
#         # -----------------------------
#         candidate_filters = {}

#         if filters.get("status") and filters["status"] != "Any":
#             candidate_filters["status"] = filters["status"]

#         candidates = frappe.get_all(
#             "Candidate",
#             filters=candidate_filters,
#             fields=["name", "skills", "experience_years"]
#         )

#         # -----------------------------
#         # 3️⃣ Apply skill + experience filtering
#         # -----------------------------
#         filtered_candidate_ids = []

#         for c in candidates:
#             # Skills (ANY match)
#             if filters.get("skills"):
#                 candidate_skills = [
#                     s.strip().lower()
#                     for s in (c.skills or "").split(",")
#                 ]

#                 if not any(
#                     skill.lower() in candidate_skills
#                     for skill in filters["skills"]
#                 ):
#                     continue

#             # Experience (only if exists)
#             exp = c.experience_years
#             if exp is not None:
#                 if filters.get("min_experience") is not None and exp < filters["min_experience"]:
#                     continue
#                 if filters.get("max_experience") is not None and exp > filters["max_experience"]:
#                     continue

#             filtered_candidate_ids.append(c.name)

#         if not filtered_candidate_ids:
#             return {
#                 "success": True,
#                 "answer": "No candidates match the selected profile filters.",
#                 "sources": []
#             }

#         # -----------------------------
#         # 4️⃣ Vector search
#         # -----------------------------
#         query_vector = embed_texts([question])[0]
#         matches = search_similar(query_vector, top_k=10)

#         matches = [
#             m for m in matches
#             if m.get("candidate_id") in filtered_candidate_ids
#         ][:5]

#         if not matches:
#             return {
#                 "success": True,
#                 "answer": "No relevant information found in the selected profiles.",
#                 "sources": []
#             }

#         # -----------------------------
#         # 5️⃣ Fetch resume chunks
#         # -----------------------------
#         chunk_ids = [m["resume_chunk"] for m in matches]

#         chunks = frappe.get_all(
#             "Resume Chunk",
#             filters={"name": ["in", chunk_ids]},
#             fields=["chunk_text", "candidate"]
#         )

#         # -----------------------------
#         # 6️⃣ Build grounded context (NO [Name] EVER)
#         # -----------------------------
#         context = "\n\n".join(
#             f"Candidate: {candidate_map.get(c['candidate'], c['candidate'])}\n{c['chunk_text']}"
#             for c in chunks
#         )

#         # -----------------------------
#         # 7️⃣ Deduplicate sources
#         # -----------------------------
#         unique_sources = {}
#         for c in chunks:
#             unique_sources[c["candidate"]] = {
#                 "candidate": candidate_map.get(c["candidate"], c["candidate"])
#             }

#         sources = list(unique_sources.values())

#         # -----------------------------
#         # 8️⃣ Ask LLM
#         # -----------------------------
#         answer = chat_with_llm(context, question)

#         return {
#             "success": True,
#             "answer": answer,
#             "sources": sources
#         }

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Chat Query Error")
#         return {
#             "success": False,
#             "error": str(e)
#         }


import frappe
import json
from resume_ai.api.resume.embedder import embed_texts
from resume_ai.api.resume.vector_store import search_similar
# from resume_ai.api.resume.llm import chat_with_llm


@frappe.whitelist(allow_guest=True)
def chat_query(question=None, filters=None, response_format="text"):
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

        candidates = frappe.get_all(
            "Candidate",
            filters=candidate_filters,
            fields=["name", "full_name", "email", "phone", "skills", "experience_years"]
        )

        # -----------------------------
        # 3️⃣ Apply skill & experience filtering
        # -----------------------------
        filtered_candidates = []

        for c in candidates:
            # Skill filter (ANY match)
            if filters.get("skills"):
                candidate_skills = [
                    s.strip().lower()
                    for s in (c.skills or "").split(",")
                ]

                if not any(
                    skill.lower() in candidate_skills
                    for skill in filters["skills"]
                ):
                    continue

            # Experience filter (only if exists)
            exp = c.experience_years
            if exp is not None:
                if filters.get("min_experience") is not None and exp < filters["min_experience"]:
                    continue
                if filters.get("max_experience") is not None and exp > filters["max_experience"]:
                    continue

            filtered_candidates.append(c)

        if not filtered_candidates:
            return {
                "success": True,
                "answer": "No candidates match the selected profile filters.",
                "sources": []
            }

        # -----------------------------
        # 🔥 TABLE MODE (URGENT CLIENT REQUIREMENT)
        # -----------------------------
        if response_format == "table":
            rows = []

            for c in filtered_candidates:
                rows.append({
                    "name": c.full_name,
                    "email": c.email,
                    "phone": c.phone,
                    "skills": c.skills
                })

            return {
                "success": True,
                "format": "table",
                "columns": ["Name", "Email", "Phone", "Skills"],
                "rows": rows
            }

        # -----------------------------
        # 4️⃣ TEXT MODE (existing AI chat)
        # -----------------------------
        # Build candidate ID map
        candidate_map = {c.name: c.full_name for c in filtered_candidates}

        query_vector = embed_texts([question])[0]
        matches = search_similar(query_vector, top_k=10)

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
