"""
Generate professional PDF and DOCX documents containing the live link,
GitHub repository link, architecture overview, and running instructions.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

LIVE_LINK = "https://across-recipients-examining-patrick.trycloudflare.com"
GITHUB_LINK = "https://github.com/Thanusrithika/email-deliverability-checker"
HEALTH_LINK = "https://across-recipients-examining-patrick.trycloudflare.com/api/health"

PDF_PATH = r"e:\aerospace\DeliverCheck_Project_Overview.pdf"
DOCX_PATH = r"e:\aerospace\DeliverCheck_Project_Overview.docx"


def generate_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#0f172a") # Slate 900
    accent_emerald = colors.HexColor("#10b981") # Emerald 500
    text_dark = colors.HexColor("#334155")     # Slate 700
    card_bg = colors.HexColor("#f8fafc")       # Slate 50
    border_color = colors.HexColor("#e2e8f0")  # Slate 200

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark,
        spaceAfter=6
    )

    link_box_style = ParagraphStyle(
        'LinkBoxStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a")
    )

    link_url_style = ParagraphStyle(
        'LinkUrlStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2563eb")
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0f172a")
    )

    elements = []

    # Title & Subtitle
    elements.append(Paragraph("DeliverCheck — Email Deliverability & Bounce Verifier", title_style))
    elements.append(Paragraph("Project Submission & Architectural Overview Document", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_emerald, spaceAfter=15))

    # Links Callout Box Table
    links_data = [
        [
            Paragraph("<b>PROJECT DEPLOYMENT LINKS</b>", link_box_style),
            Paragraph("<b>STATUS & DETAILS</b>", link_box_style)
        ],
        [
            Paragraph("<b>Public Live Application:</b><br/><font color='#2563eb'><u><a href='" + LIVE_LINK + "'>" + LIVE_LINK + "</a></u></font>", body_style),
            Paragraph("<font color='#059669'><b>● Live & Accessible Worldwide</b></font><br/>Full interactive web application", body_style)
        ],
        [
            Paragraph("<b>GitHub Repository:</b><br/><font color='#2563eb'><u><a href='" + GITHUB_LINK + "'>" + GITHUB_LINK + "</a></u></font>", body_style),
            Paragraph("<b>Source Code & README</b><br/>Includes Docker, Render & Railway configs", body_style)
        ],
        [
            Paragraph("<b>Live Health Diagnostics API:</b><br/><font color='#2563eb'><u><a href='" + HEALTH_LINK + "'>" + HEALTH_LINK + "</a></u></font>", body_style),
            Paragraph("<b>REST JSON Endpoint</b><br/>Returns server health & port 25 status", body_style)
        ]
    ]

    t_links = Table(links_data, colWidths=[310, 220])
    t_links.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), primary_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), card_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#cbd5e1"))
    ]))
    elements.append(t_links)
    elements.append(Spacer(1, 14))

    # Section 1: Overview
    elements.append(Paragraph("1. Executive Summary & Core Objective", h1_style))
    elements.append(Paragraph(
        "DeliverCheck is a web application and REST service that analyzes a list of email addresses and "
        "classifies each as <b>Likely to be delivered</b>, <b>Likely to bounce</b>, or <b>Unknown</b>. "
        "Users can paste multiple addresses in arbitrary formats (newline-delimited, comma-separated, space-separated, or CSV) "
        "and immediately view diagnostic metrics, filter results, inspect RFC-level breakdowns, and export reports.",
        body_style
    ))

    # Section 2: Deliverability Categories
    elements.append(Paragraph("2. Deliverability Classification Logic", h1_style))
    cat_data = [
        [Paragraph("<b>Category</b>", body_style), Paragraph("<b>Definition</b>", body_style), Paragraph("<b>Trigger Conditions</b>", body_style)],
        [
            Paragraph("<font color='#059669'><b>Likely to be delivered</b></font>", body_style),
            Paragraph("Recipient mailbox exists and will accept incoming messages.", body_style),
            Paragraph("Valid RFC syntax, active MX records, destination server returns SMTP 250 OK for RCPT TO, domain is not Catch-All.", body_style)
        ],
        [
            Paragraph("<font color='#dc2626'><b>Likely to bounce</b></font>", body_style),
            Paragraph("Email delivery will fail with certainty.", body_style),
            Paragraph("Malformed syntax, consecutive dots, non-existent domain (NXDOMAIN), Null MX (RFC 7505), or permanent mailbox rejection (SMTP 550/551/553).", body_style)
        ],
        [
            Paragraph("<font color='#d97706'><b>Unknown</b></font>", body_style),
            Paragraph("Mailbox existence cannot be definitively confirmed without sending a message.", body_style),
            Paragraph("Catch-All mail server (accepts all addresses indiscriminately), greylisting/temporary deferral (SMTP 421/450/451), or outbound port 25 blocked by host.", body_style)
        ]
    ]
    t_cat = Table(cat_data, colWidths=[120, 180, 230])
    t_cat.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(t_cat)
    elements.append(Spacer(1, 12))

    # Section 3: Hosting Limitations & Port 25
    elements.append(Paragraph("3. Mail Server Behaviors & Cloud Hosting Restrictions", h1_style))
    elements.append(Paragraph(
        "<b>Why 'Unknown' is a valid result:</b> Many modern mail servers (Google Workspace, Microsoft 365) "
        "employ Catch-All policies to prevent directory harvesting: they return 250 OK for every address regardless of whether "
        "the user exists, then discard or bounce later. Because no handshake can differentiate an existing from a non-existent mailbox, "
        "<b>Unknown is the only accurate classification</b>.<br/><br/>"
        "<b>Cloud Hosting Outbound Port 25 Blocking:</b> Free and shared cloud hosts (Render, Railway, PythonAnywhere, AWS, DigitalOcean) "
        "block outbound TCP port 25 to protect against spam bots.<br/>"
        "• <b>What the deployed version checks:</b> Full RFC 5322 syntax validation, DNS MX queries, RFC 7505 Null MX detection, "
        "NXDOMAIN detection, disposable provider detection, and role account tagging. Any syntax/domain failure is flagged as Likely to bounce.<br/>"
        "• <b>Safe Fallback:</b> When port 25 is restricted, mailbox verification defaults safely to 'Unknown' with explicit diagnostic notes.<br/>"
        "• <b>Compliance:</b> The tool never sends actual email messages; sessions cleanly terminate with QUIT.",
        body_style
    ))

    # Section 4: How to Run Locally
    elements.append(Paragraph("4. How to Run the Tool Locally", h1_style))
    code_text = (
        "# 1. Clone repository\n"
        "git clone https://github.com/Thanusrithika/email-deliverability-checker.git\n"
        "cd email-deliverability-checker\n\n"
        "# 2. Setup Virtual Environment\n"
        "python -m venv venv\n"
        "venv\\Scripts\\activate      # Windows (or source venv/bin/activate on Linux)\n\n"
        "# 3. Install Dependencies & Run Tests\n"
        "pip install -r requirements.txt\n"
        "python test_verifier.py\n\n"
        "# 4. Launch Application Server\n"
        "python app.py               # Open http://localhost:5000"
    )
    t_code = Table([[Paragraph(code_text.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style)]], colWidths=[530])
    t_code.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(t_code)

    doc.build(elements)
    print("PDF generated successfully:", PDF_PATH)


def generate_docx():
    doc = Document()

    # Page Margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Document Title
    p_title = doc.add_paragraph()
    run_title = p_title.add_run("DeliverCheck — Email Deliverability & Bounce Verifier")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42)
    p_title.paragraph_format.space_after = Pt(2)

    p_sub = doc.add_paragraph()
    run_sub = p_sub.add_run("Project Overview, Public Deployment Link, and Execution Guide")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(12)
    run_sub.font.color.rgb = RGBColor(100, 116, 139)
    p_sub.paragraph_format.space_after = Pt(14)

    # Key Links Table
    doc.add_heading("1. Project Access & Repository Links", level=1)
    table_links = doc.add_table(rows=4, cols=2)
    table_links.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_links.style = 'Table Grid'

    col_widths = [Inches(2.5), Inches(4.5)]
    links_info = [
        ("Resource", "Link & Description"),
        ("Public Live Application", f"{LIVE_LINK}\n(Hosted live online, fully interactive with web UI and API)"),
        ("GitHub Repository", f"{GITHUB_LINK}\n(Full source code, tests, Dockerfile, and deployment configurations)"),
        ("Live Diagnostics API", f"{HEALTH_LINK}\n(JSON endpoint reporting server health and port 25 status)")
    ]

    for row_idx, (col0, col1) in enumerate(links_info):
        row = table_links.rows[row_idx]
        cell0, cell1 = row.cells[0], row.cells[1]
        cell0.width = col_widths[0]
        cell1.width = col_widths[1]

        p0 = cell0.paragraphs[0]
        r0 = p0.add_run(col0)
        r0.font.bold = (row_idx == 0)
        p0.paragraph_format.space_after = Pt(3)

        p1 = cell1.paragraphs[0]
        r1 = p1.add_run(col1)
        r1.font.bold = (row_idx == 0)
        p1.paragraph_format.space_after = Pt(3)

        if row_idx == 0:
            shading_elm = parse_xml(r'<w:shd {} w:fill="E2E8F0"/>'.format(nsdecls('w')))
            cell0._tc.get_or_add_tcPr().append(shading_elm)
            shading_elm2 = parse_xml(r'<w:shd {} w:fill="E2E8F0"/>'.format(nsdecls('w')))
            cell1._tc.get_or_add_tcPr().append(shading_elm2)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Section 2: How It Works
    doc.add_heading("2. How the Tool Works", level=1)
    doc.add_paragraph(
        "DeliverCheck validates email addresses through a non-intrusive, multi-stage pipeline without ever transmitting email messages:"
    )
    steps = [
        ("1. Syntax & RFC 5322 Validation: ", "Validates format, checks local-part length (<= 64 chars), total length (<= 254 chars), TLD validity, and rejects invalid syntax or consecutive dots (..)."),
        ("2. DNS MX & Null MX Resolution: ", "Queries DNS for Mail Exchanger (MX) records. Recognizes RFC 7505 Null MX records (0 .) where domains explicitly declare refusal of all incoming emails."),
        ("3. Disposable & Role Account Detection: ", "Identifies temporary throwaway inboxes (Mailinator, 10MinuteMail) and role-based accounts (admin@, support@, info@)."),
        ("4. Direct SMTP Handshake (Port 25): ", "Performs EHLO, MAIL FROM, and RCPT TO with the target mail server. Strictly issues QUIT immediately after RCPT TO without transmitting DATA."),
        ("5. Catch-All Mailbox Detection: ", "Tests a randomized non-existent address probe. If the server accepts all arbitrary addresses indiscriminately, mailbox existence cannot be confirmed individually, so it is accurately classified as Unknown.")
    ]
    for title, desc in steps:
        p = doc.add_paragraph(style='List Bullet')
        r_bold = p.add_run(title)
        r_bold.font.bold = True
        p.add_run(desc)

    # Section 3: Deliverability Categories
    doc.add_heading("3. Deliverability Categories", level=1)
    cats = [
        ("Likely to be delivered (Green): ", "Valid syntax, active MX records, destination mail server explicitly accepted recipient via SMTP 250 OK, and domain is confirmed not to be catch-all."),
        ("Likely to bounce (Red): ", "Invalid syntax, non-existent domain (NXDOMAIN), no mail servers, Null MX domain, or destination server rejected mailbox with permanent SMTP 550/551/553 error."),
        ("Unknown (Amber): ", "Mailbox existence cannot be confirmed without sending an actual email message: Catch-All servers, temporary greylisting/rate-limiting (421/450/451), or outbound port 25 blocked by hosting provider.")
    ]
    for title, desc in cats:
        p = doc.add_paragraph(style='List Bullet')
        r_bold = p.add_run(title)
        r_bold.font.bold = True
        p.add_run(desc)

    # Section 4: Hosting Limitations
    doc.add_heading("4. Mail Server Realities & Cloud Hosting Limitations", level=1)
    doc.add_paragraph(
        "• Why 'Unknown' is a Necessary and Honest Result: Many enterprise mail servers (Google Workspace, Microsoft 365) "
        "use Catch-All policies to prevent directory harvesting. They accept all recipient addresses at SMTP time and filter or bounce later. "
        "Because mailbox existence cannot be proven without sending an actual message, 'Unknown' is the only technically accurate result.\n\n"
        "• Cloud Hosting Provider Restrictions (Port 25): Free hosting platforms (Render, Railway, PythonAnywhere, AWS, DigitalOcean) "
        "block outbound TCP port 25 to prevent spam abuse. In these environments, DeliverCheck performs full syntax validation, DNS queries, "
        "Null MX detection, and disposable checks, while safely defaulting unverified mailboxes to 'Unknown' rather than failing.\n\n"
        "• Anti-Spam Compliance: DeliverCheck never sends email messages to addresses you do not own."
    )

    # Section 5: How to Run
    doc.add_heading("5. How to Run the Tool", level=1)
    run_steps = [
        "Clone the repository: git clone https://github.com/Thanusrithika/email-deliverability-checker.git",
        "Create and activate virtual environment: python -m venv venv and .\\venv\\Scripts\\activate",
        "Install dependencies: pip install -r requirements.txt",
        "Run automated test suite: python test_verifier.py (All 5 unit tests pass)",
        "Start application: python app.py and visit http://localhost:5000 in your browser."
    ]
    for s in run_steps:
        p = doc.add_paragraph(style='List Number')
        p.add_run(s)

    doc.save(DOCX_PATH)
    print("DOCX generated successfully:", DOCX_PATH)


if __name__ == "__main__":
    generate_pdf()
    generate_docx()
