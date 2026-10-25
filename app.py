"""
Email Deliverability Checker - Web Application Backend
Flask application providing web interface and REST API for bulk email verification.
"""

import os
import re
import socket
from typing import List, Set
from flask import Flask, request, jsonify, render_template, send_file

from verifier import verify_email, verify_emails_batch, is_port_25_accessible

app = Flask(__name__, template_folder="templates", static_folder="static")

# Sample emails illustrating different verification categories
SAMPLE_EMAILS = [
    # Likely deliverable (real deliverable inboxes)
    "thanusrithika@gmail.com",
    "contact@cloudflare.com",
    # Likely to bounce (invalid syntax or non-existent domains/mailboxes)
    "user..double-dot@example.com",
    "missing-at-sign.com",
    "john.doe@thisdomainabsolutelydoesnotexist999888.org",
    "fake_nonexistent_user_998811@gmail.com",
    # Unknown (Catch-all servers, unconfirmed mailboxes, disposable)
    "support@github.com",
    "test_user_temporary@mailinator.com"
]


def extract_emails(raw_input: str) -> List[str]:
    """
    Extracts email addresses from various raw text formats:
    - Newline separated
    - Comma separated
    - Semicolon separated
    - Space or tab separated
    - CSV rows
    """
    if not raw_input:
        return []

    # Replace common delimiters with newlines
    normalized = re.sub(r"[,;\t]+", "\n", raw_input)
    # Also handle space-separated if tokens look like emails
    lines = normalized.split("\n")
    extracted: List[str] = []
    seen: Set[str] = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Split by whitespace in case multiple addresses are on one line
        tokens = line.split()
        for token in tokens:
            token = token.strip().strip("<>(),\"'")
            if token and token not in seen:
                seen.add(token)
                extracted.append(token)

    return extracted


@app.route("/")
def index():
    """Render the main single-page application UI."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """Health check and environment diagnostics."""
    port_25_open = False
    try:
        # Check against a major public MX server
        port_25_open = is_port_25_accessible("aspmx.l.google.com", timeout=2.0)
    except Exception:
        port_25_open = False

    return jsonify({
        "status": "healthy",
        "service": "email-deliverability-checker",
        "version": "1.0.0",
        "diagnostics": {
            "outbound_port_25_accessible": port_25_open,
            "port_25_note": (
                "Direct SMTP mailbox handshake is active."
                if port_25_open
                else "Outbound port 25 is blocked or restricted by the hosting provider/ISP. "
                     "Syntax, domain validation, and MX records work normally, while mailbox-level "
                     "checks default safely to 'Unknown' per RFC guidelines."
            )
        }
    })


@app.route("/api/samples", methods=["GET"])
def samples():
    """Returns sample email addresses for quick demonstration."""
    return jsonify({
        "samples": SAMPLE_EMAILS,
        "raw_text": "\n".join(SAMPLE_EMAILS)
    })


@app.route("/api/verify", methods=["POST"])
def verify():
    """
    Batch verification API endpoint.
    Accepts JSON:
      { "emails": ["a@b.com", "c@d.com"] }
      or
      { "text": "a@b.com\nc@d.com" }
    Also accepts form data: 'emails' or 'text'
    """
    emails: List[str] = []

    if request.is_json:
        data = request.get_json(silent=True) or {}
        if "emails" in data and isinstance(data["emails"], list):
            emails = [str(e).strip() for e in data["emails"] if str(e).strip()]
        elif "text" in data and isinstance(data["text"], str):
            emails = extract_emails(data["text"])
    else:
        # Form data fallback
        raw_text = request.form.get("text") or request.form.get("emails") or ""
        emails = extract_emails(raw_text)

    if not emails:
        return jsonify({
            "success": False,
            "error": "No email addresses provided. Please provide an array of emails or text.",
            "summary": {
                "total": 0,
                "likely_to_be_delivered": 0,
                "likely_to_bounce": 0,
                "unknown": 0
            },
            "results": []
        }), 400

    # Limit maximum batch size to prevent abuse (e.g. max 100 emails per request)
    max_batch = 100
    if len(emails) > max_batch:
        emails = emails[:max_batch]

    results = verify_emails_batch(emails)

    summary = {
        "total": len(results),
        "likely_to_be_delivered": sum(1 for r in results if r.get("category") == "likely_to_be_delivered"),
        "likely_to_bounce": sum(1 for r in results if r.get("category") == "likely_to_bounce"),
        "unknown": sum(1 for r in results if r.get("category") == "unknown")
    }

    return jsonify({
        "success": True,
        "summary": summary,
        "results": results
    })


@app.route("/api/verify-single", methods=["GET", "POST"])
def verify_single():
    """Single email verification endpoint."""
    email = ""
    if request.method == "POST":
        if request.is_json:
            data = request.get_json(silent=True) or {}
            email = data.get("email", "")
        else:
            email = request.form.get("email", "")
    else:
        email = request.args.get("email", "")

    email = email.strip()
    if not email:
        return jsonify({"success": False, "error": "Missing 'email' parameter"}), 400

    result = verify_email(email)
    return jsonify({
        "success": True,
        "result": result
    })


@app.route("/download-pdf", methods=["GET"])
@app.route("/download/pdf", methods=["GET"])
@app.route("/DeliverCheck_Project_Overview.pdf", methods=["GET"])
def download_pdf():
    """Endpoint to download the project overview PDF."""
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DeliverCheck_Project_Overview.pdf")
    if os.path.exists(pdf_path):
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name="DeliverCheck_Project_Overview.pdf",
            mimetype="application/pdf"
        )
    return jsonify({"error": "PDF file not found"}), 404


@app.route("/download-docx", methods=["GET"])
@app.route("/download/docx", methods=["GET"])
@app.route("/DeliverCheck_Project_Overview.docx", methods=["GET"])
def download_docx():
    """Endpoint to download the project overview DOCX."""
    docx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DeliverCheck_Project_Overview.docx")
    if os.path.exists(docx_path):
        return send_file(
            docx_path,
            as_attachment=True,
            download_name="DeliverCheck_Project_Overview.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    return jsonify({"error": "DOCX file not found"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
