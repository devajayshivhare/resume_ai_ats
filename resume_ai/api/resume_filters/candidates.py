# import frappe
# import json

# @frappe.whitelist(allow_guest=True)
# def search_candidates(filters=None):
#     # return "search_candidates API called with filters: "
#     if isinstance(filters, str):
#         filters = json.loads(filters)
        
#     # ✅ FIX 2: Handle None
#     if not filters:
#         filters = {}

#     resumes = frappe.get_all(
#         "Resume",
#         fields=["name", "parsed_json"]
#     )

#     results = []

#     for r in resumes:
#         if not r.parsed_json:
#             continue

#         data = json.loads(r.parsed_json)

#         # 🔹 Experience Filter
#         exp = data.get("experience_years", 0)
#         if filters.get("min_exp") and exp < filters["min_exp"]:
#             continue
#         if filters.get("max_exp") and exp > filters["max_exp"]:
#             continue

#         # 🔹 Skills Filter
#         if filters.get("skills"):
#             candidate_skills = [s["skill_name"].lower() for s in data.get("skills", [])]

#             if not any(skill.lower() in candidate_skills for skill in filters["skills"]):
#                 continue

#         # 🔹 Degree Filter
#         if filters.get("degree"):
#             degrees = [e["degree"].lower() for e in data.get("education", [])]

#             if not any(filters["degree"].lower() in d for d in degrees):
#                 continue

#         # 🔹 Role Filter
#         if filters.get("role"):
#             roles = [exp["role"].lower() for exp in data.get("experience", [])]

#             if not any(filters["role"].lower() in r for r in roles):
#                 continue

#         results.append({
#             "id": r.name,
#             "name": f"{data.get('first_name', '')} {data.get('last_name', '')}",
#             "experience": exp,
#             "skills": [s["skill_name"] for s in data.get("skills", [])][:6],
#             "current_role": data.get("experience", [{}])[0].get("role", "")
#         })

#     return results

import frappe
import json

@frappe.whitelist(allow_guest=True)
def search_candidates(filters=None):

    import json

    # ✅ Parse filters
    if isinstance(filters, str):
        filters = json.loads(filters)

    if not filters:
        filters = {}

    if "filters" in filters:
        filters = filters["filters"]

    frappe.log_error("RAW FILTERS", str(filters))

    # ✅ Extract values
    min_exp = float(filters.get("min_exp") or 0)
    max_exp = float(filters.get("max_exp") or 100)

    frappe.log_error("FINAL VALUES", f"{min_exp} → {max_exp}")

    # ✅ IMPORTANT: use list filters (NOT between)
    db_filters = [
        ["experience_years", ">=", min_exp],
        ["experience_years", "<=", max_exp]
    ]

    # ✅ Role filter
    if filters.get("role"):
        db_filters.append(
            ["current_role", "like", f"%{filters.get('role')}%"]
        )
    if filters.get("degree"):
        db_filters.append(
            ["degree", "like", f"%{filters.get('degree')}%"]
        )

    # ✅ Skills filter
    # if filters.get("skills"):
    #     db_filters.append(
    #         ["skills", "like", f"%{filters.get('skills')}%"]
    #     )
    skills = filters.get("skills")

    if skills:
        for skill in skills:
            db_filters.append(
                ["skills", "like", f"%{skill}%"]
            )

    return frappe.get_all(
        "Resume",
        filters=db_filters,
        fields=[
            "name",
            "candidate_name",
            "experience_years",
            "skills",
            "current_role",
            "degree",
        ],
        order_by="modified desc"
    )
# @frappe.whitelist(allow_guest=True)
# def search_candidates(filters=None):
#     if isinstance(filters, str):
#         filters = json.loads(filters)

#     if not filters:
#         filters = {}

#     # Safely parse and provide defaults
#     try:
#         min_exp = float(filters.get("min_exp") or 0)
#         max_exp = float(filters.get("max_exp") or 100)
#     except (ValueError, TypeError):
#         min_exp, max_exp = 0, 100

#     # Ensure max is at least 100 if set to 0 by user
#     if max_exp <= 0:
#         max_exp = 100

#     # Swap if user put them in wrong order
#     if min_exp > max_exp:
#         min_exp, max_exp = max_exp, min_exp

#     # Use a tuple for the between range
#     # db_filters = {
#     #     "experience_years": ["between", (min_exp, max_exp)]
#     # }
#     db_filters = {
#         "experience_years": ["=", (min_exp, max_exp)]
#     }
    
#     # db_filters = [
#     #     ["Resume", "experience_years", "between", [min_exp, max_exp]]
#     # ]

#     return frappe.get_all(
#         "Resume",
#         # filters=db_filters,
#         filters=db_filters,
#         # fields=["*"],
#         fields=[
#             "name",
#             "candidate_name",
#             "experience_years",
#             "skills",
#             "current_role"
#         ],
#         order_by="modified desc"
#         # order_by="`tabResume`.`modified` DESC"  # safer
#     )

# @frappe.whitelist(allow_guest=True)
# def search_candidates(filters=None):

#     # ✅ Convert incoming filters
#     if isinstance(filters, str):
#         filters = json.loads(filters)

#     if not filters:
#         filters = {}

#     # ✅ DEBUG (ADD THIS)
#     frappe.log_error("RAW FILTERS", str(filters))

#     # ✅ Extract safely
#     min_exp = float(filters.get("min_exp") or 0)
#     max_exp = float(filters.get("max_exp") or 100)

#     # ✅ FORCE FIX (IMPORTANT)
#     if max_exp is None or max_exp == 0:
#         max_exp = 100

#     if min_exp > max_exp:
#         min_exp, max_exp = max_exp, min_exp

#     # ✅ DEBUG AGAIN
#     frappe.log_error("FINAL VALUES", f"{min_exp} → {max_exp}")

#     # db_filters = {
#     #     "experience_years": ["between", [min_exp, max_exp]]
#     # }
#     # To this:
#     db_filters = {
#         "experience_years": ["between", (min_exp, max_exp)]
#     }
#     # return frappe.get_all(
#     #     "Resume",
#     #     filters=db_filters,
#     #     fields=[
#     #         "name",
#     #         "candidate_name",
#     #         "experience_years",
#     #         "skills",
#     #         "current_role"
#     #     ],
#     #     order_by="`tabResume`.`modified` DESC"  # safer
#     # )
#     return frappe.get_all(
#         "Resume",
#         filters=db_filters,
#         fields=[
#             "name",
#             "candidate_name",
#             "experience_years",
#             "skills",
#             "current_role"
#         ],
#         order_by="modified desc"
#     )

# @frappe.whitelist()
# def search_candidates(filters=None):

#     # ✅ Convert filters safely
#     if isinstance(filters, str):
#         filters = json.loads(filters)

#     if not filters:
#         filters = {}

#     # ✅ Convert numeric filters
#     min_exp = float(filters.get("min_exp") or 0)
#     max_exp = float(filters.get("max_exp") or 100)

#     skills_filter = filters.get("skills") or []
#     degree_filter = (filters.get("degree") or "").lower()
#     role_filter = (filters.get("role") or "").lower()

#     resumes = frappe.get_all(
#         "Resume",
#         fields=["name", "parsed_json"],
#         limit_page_length=200   # ⚡ safety limit
#     )

#     results = []

#     for r in resumes:
#         try:
#             if not r.parsed_json:
#                 continue

#             data = json.loads(r.parsed_json)

#             # ✅ Experience
#             exp = float(data.get("experience_years", 0))

#             if exp < min_exp:
#                 continue
#             if exp > max_exp:
#                 continue

#             # ✅ Skills
#             if skills_filter:
#                 candidate_skills = [
#                     s.get("skill_name", "").lower()
#                     for s in data.get("skills", [])
#                 ]

#                 if not any(skill.lower() in candidate_skills for skill in skills_filter):
#                     continue

#             # ✅ Degree
#             if degree_filter:
#                 degrees = [
#                     e.get("degree", "").lower()
#                     for e in data.get("education", [])
#                 ]

#                 if not any(degree_filter in d for d in degrees):
#                     continue

#             # ✅ Role
#             if role_filter:
#                 roles = [
#                     exp_item.get("role", "").lower()
#                     for exp_item in data.get("experience", [])
#                 ]

#                 if not any(role_filter in r for r in roles):
#                     continue

#             # ✅ Final result object
#             results.append({
#                 "id": r.name,
#                 "name": f"{data.get('first_name', '')} {data.get('last_name', '')}",
#                 "experience": exp,
#                 "skills": [s.get("skill_name") for s in data.get("skills", [])][:6],
#                 "current_role": data.get("experience", [{}])[0].get("role", "")
#             })

#         except Exception as e:
#             frappe.log_error("Candidate Filter Error", str(e))
#             continue

#     return results