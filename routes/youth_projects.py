"""Teranga Projet API route registration."""

from flask import jsonify, request


def register_youth_project_route(app, deps):
    require_json_post = deps["require_json_post"]
    sanitize_text = deps["sanitize_text"]
    build_project_brief = deps["build_project_brief"]
    max_message_length = deps.get("max_message_length", 2000)

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
