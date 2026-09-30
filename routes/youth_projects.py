"""Teranga Projet API route registration."""

from flask import jsonify, render_template, request


def register_youth_project_route(app, deps):
    require_json_post = deps["require_json_post"]
    sanitize_text = deps["sanitize_text"]
    build_project_brief = deps["build_project_brief"]
    advance_project_stage = deps["advance_project_stage"]
    find_project_partners = deps.get("find_project_partners", lambda category="", city="": [])
    max_message_length = deps.get("max_message_length", 2000)

    @app.get("/partners")
    def youth_project_partners():
        category = sanitize_text(request.args.get("category", ""), max_len=40).strip()
        city = sanitize_text(request.args.get("city", ""), max_len=80).strip()
        return render_template(
            "partners.html",
            partners=find_project_partners(category, city),
            selected_category=category,
            selected_city=city,
        )

    @app.post("/api/projects/plan")
    @require_json_post
    def youth_project_plan():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Requête invalide."}), 400

        idea = sanitize_text(payload.get("idea", ""), max_len=max_message_length).strip()
        if not idea:
            return jsonify({"error": "Décris ton idée de projet."}), 400

        brief = build_project_brief(
            idea=idea,
            city=sanitize_text(payload.get("city", ""), max_len=80).strip(),
            budget_fcfa=payload.get("budget_fcfa"),
            skills=sanitize_text(payload.get("skills", ""), max_len=200).strip(),
            available_time=sanitize_text(payload.get("available_time", ""), max_len=100).strip(),
            goal_fcfa=payload.get("goal_fcfa"),
            category=sanitize_text(payload.get("category", ""), max_len=40).strip(),
        )
        return jsonify({"project": brief})


    @app.post("/api/projects/advance")
    @require_json_post
    def youth_project_advance():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Requête invalide."}), 400
        project = payload.get("project")
        if not isinstance(project, dict):
            return jsonify({"error": "Projet invalide."}), 400
        return jsonify({"project": advance_project_stage(project, payload.get("stage"))})
