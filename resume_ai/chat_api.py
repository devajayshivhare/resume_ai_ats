import frappe
import requests


CHAT_PROMPT = """
You are an AI recruiter assistant.

Answer the user's question using ONLY the resume information provided below.
If the answer is not found in the resumes, say:
"Not found in the uploaded resumes."

Resume Data:
{context}

User Question:
{question}
"""


def chat_with_llm(context, question):
    prompt = CHAT_PROMPT.format(
        context=context,
        question=question
    )

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    res = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=120
    )

    return res.json().get("response", "").strip()


@frappe.whitelist(allow_guest=True)
def chat_query(question):
    """
    Chat over uploaded resumes
    """

    if not question:
        frappe.throw("Question is required")

    from resume_ai.embedder import embed_texts
    from resume_ai.vector_store import search_similar

    # 1️⃣ Embed question
    query_vector = embed_texts([question])[0]

    # 2️⃣ Search relevant resume chunks
    matches = search_similar(query_vector, top_k=5)

    if not matches:
        return {
            "success": True,
            "answer": "No resume data found."
        }

    # 3️⃣ Build context
    context = "\n\n".join(
        f"- {m['text']}" for m in matches
    )

    # 4️⃣ Ask LLM
    answer = chat_with_llm(context, question)

    return {
        "success": True,
        "answer": answer,
        "sources": matches
    }
