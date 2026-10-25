# DeliverCheck — Email Deliverability & Bounce Predictor

**DeliverCheck** is a web application and REST API that verifies a list of email addresses and categorizes each as:
- **Likely to be delivered** (green)
- **Likely to bounce** (red)
- **Unknown** (amber)

Users can paste a batch of email addresses in any standard format (newline, comma, semicolon, space, or CSV), inspect real-time progress, filter results, view detailed diagnostic breakdowns for each address, and export the analysis to CSV or JSON.

---

## Live Public Deployment

- **Live URL**: [https://across-recipients-examining-patrick.trycloudflare.com](https://across-recipients-examining-patrick.trycloudflare.com)
- **Local URL**: `http://localhost:5000`
- **Health & Diagnostics Endpoint**: [https://across-recipients-examining-patrick.trycloudflare.com/api/health](https://across-recipients-examining-patrick.trycloudflare.com/api/health)

---

## Key Features

1. **Flexible Input Handling**: Accepts lists separated by newlines, commas, semicolons, tabs, spaces, or CSV files. Automatically strips quotes, angle brackets (`<user@domain.com>`), and deduplicates input while preserving order.
2. **Multi-Stage Verification Pipeline**:
   - **RFC 5322 Syntax Check**: Validates structure, characters, local-part length (&le; 64 characters), overall length (&le; 254 characters), and TLD formatting.
   - **DNS & MX Resolution**: Looks up Mail Exchanger (MX) records, handles RFC 5321 A-record fallbacks, and detects RFC 7505 **Null MX** records (`0 .`) which explicitly declare that a domain rejects all email.
   - **Disposable Email Detection**: Flags temporary/throwaway inboxes (Mailinator, 10MinuteMail, GuerrillaMail, etc.).
   - **Role-based Account Detection**: Identifies shared addresses (`admin@`, `support@`, `sales@`, `info@`, etc.).
   - **Non-Intrusive SMTP Handshake**: Connects to the destination MX server on port 25, issues `EHLO`, `MAIL FROM`, and `RCPT TO`.
3. **Catch-All Mailbox Detection**: Tests against a randomized address probe. If the server accepts all arbitrary addresses indiscriminately, the mailbox existence cannot be confirmed individually, so it is accurately classified as **Unknown**.
4. **Interactive Dashboard**:
   - Live summary metrics (Total, Likely Delivered, Likely Bounce, Unknown).
   - Instant filtering tabs and search query box.
   - Accordion drawer for each address showing raw MX hosts, SMTP response codes, and diagnostic reasons.
   - 1-click **Export to CSV** and **Export to JSON**.
5. **Full REST API**: Clean endpoints for single and batch verification.

---

## Deliverability Categories Explained

| Category | Meaning | Common Scenarios |
|---|---|---|
| <span style="color: #22c55e; font-weight: bold;">Likely to be delivered</span> | The address conforms to RFC standards, the domain has active MX servers, and the destination mail server explicitly accepted the recipient via SMTP `250 OK` (and the domain is confirmed not to be a catch-all). | Active, existing personal or corporate mailboxes on servers that confirm recipient validity. |
| <span style="color: #ef4444; font-weight: bold;">Likely to bounce</span> | The address will fail delivery with certainty or near-certainty. | Invalid syntax (`user..name@`, missing `@`), non-existent domains (`NXDOMAIN`), domains without MX/A records, Null MX domains (RFC 7505), or mailboxes explicitly rejected by destination servers with permanent `550 / 551 / 553 User unknown` errors. |
| <span style="color: #f59e0b; font-weight: bold;">Unknown</span> | Mailbox existence cannot be definitively confirmed without sending an actual email message. | **Catch-all domains** (servers that accept all incoming addresses indiscriminately), **Greylisting / rate-limiting** (temporary `421 / 450 / 451` codes), or environments where **outbound port 25 is blocked**. |

---

## Important: Mail Server Behaviors & Hosting Provider Restrictions

### 1. Why "Unknown" is a Valid and Necessary Result
Many modern mail servers (e.g. Microsoft Office 365, Google Workspace, custom corporate relays) intentionally **refuse to confirm whether a mailbox exists** at SMTP handshake time:
- **Catch-All (Accept-All) Policies**: The server responds with `250 OK` to *any* address (even non-existent ones) to prevent malicious actors from harvesting valid employee usernames through dictionary attacks. The mail is accepted at the gateway and bounced or silently discarded later.
- **Greylisting**: Mail servers intentionally defer connections from first-time probe senders with temporary `4xx` error codes (`451`, `450`), asking the sender to retry in 5–15 minutes.
- In both cases, **"Unknown" is the only honest and accurate assessment**. Claiming that a catch-all address is 100% deliverable is technically false.

### 2. Hosting Provider Outbound Port 25 Blocking
Most cloud and free hosting providers (including **Render**, **Railway**, **PythonAnywhere**, **AWS EC2**, **DigitalOcean**, and **Google Cloud**) **strictly block outbound TCP port 25** by default to prevent their shared IP ranges from being used by spam bots.

#### What the Application CAN and CANNOT Check:
- **What works in all environments (including port 25-restricted cloud hosting)**:
  - Full RFC 5322 syntax validation and length checks.
  - DNS resolution and MX record queries.
  - RFC 7505 Null MX detection (domains explicitly refusing mail).
  - Domain non-existence detection (NXDOMAIN).
  - Disposable email domain detection.
  - Role-based account detection.
  - Accurate classification: Any syntax or domain failure is accurately classified as **Likely to bounce**.
- **What requires an unblocked port 25**:
  - The direct TCP port 25 socket connection for the `RCPT TO` handshake.
- **Graceful Fallback**:
  - When port 25 is blocked by the host network or times out, DeliverCheck detects the network limitation immediately and **safely categorizes the addresses as "Unknown"** with an informative explanation (`"Valid MX records exist, but outbound connection to mail server failed: Port 25 blocked by host/ISP"`), rather than throwing an internal server error or making false guesses.
  - The live UI displays a status indicator pill in the header showing whether Direct SMTP probing is active or operating in safe fallback mode.

### 3. Strict Compliance Policy
> **RFC Compliance & Privacy Guarantee**: DeliverCheck **never sends actual email messages** to any address. Handshakes are strictly read-only and terminate cleanly with `QUIT` after the `RCPT TO` command.

---

## Local Setup & Development

### Prerequisites
- Python 3.9+ (Python 3.11, 3.12, or 3.13 supported)

### Installation
1. Clone or download this repository:
   ```bash
   cd e:\aerospace
   ```
2. Create and activate a virtual environment:
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the unit tests:
   ```bash
   python test_verifier.py
   ```
5. Start the web application:
   ```bash
   python app.py
   ```
6. Open your browser and navigate to `http://localhost:5000`.

---

## Deployment Instructions

### Deploy to Render
1. Push this repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** &rarr; **Web Service**.
3. Select your GitHub repository.
4. Render will automatically detect `render.yaml` or use the following settings:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`
   - **Plan**: Free

### Deploy to Railway
1. Push this repository to GitHub.
2. In [Railway](https://railway.app), click **New Project** &rarr; **Deploy from GitHub repo**.
3. Railway automatically detects `railway.json` and `Procfile` and builds the project via Nixpacks.

### Deploy to PythonAnywhere
1. Create a free account on [PythonAnywhere](https://www.pythonanywhere.com).
2. Open a Bash console and clone your repo or upload files to `/home/<username>/delivercheck`.
3. Create a virtual environment and install `requirements.txt`:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 delivercheck-venv
   pip install -r requirements.txt
   ```
4. In the **Web** tab:
   - Add a new Web App (select Manual Configuration / Flask).
   - Set the virtualenv path to `/home/<username>/.virtualenvs/delivercheck-venv`.
   - In the **WSGI configuration file**, point to `wsgi.py`:
     ```python
     import sys
     path = '/home/<username>/delivercheck'
     if path not in sys.path:
         sys.path.insert(0, path)
     from app import app as application
     ```
   - Click **Reload**.

### Deploy via Docker
```bash
docker build -t delivercheck .
docker run -p 5000:5000 delivercheck
```

---

## REST API Documentation

### 1. Batch Verification
- **Endpoint**: `POST /api/verify`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "emails": [
      "thanusrithika@gmail.com",
      "user..invalid@syntax.com",
      "nonexistent@thisdomaindoesnotexist999888.com",
      "support@github.com"
    ]
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "summary": {
      "total": 4,
      "likely_to_be_delivered": 1,
      "likely_to_bounce": 2,
      "unknown": 1
    },
    "results": [
      {
        "email": "thanusrithika@gmail.com",
        "category": "likely_to_be_delivered",
        "category_label": "Likely to be delivered",
        "reason": "Recipient address was verified and accepted by mail server (SMTP 250 OK)",
        "syntax_valid": true,
        "domain": "gmail.com",
        "mx_records": ["gmail-smtp-in.l.google.com"],
        "is_disposable": false,
        "is_role_account": false,
        "is_catch_all": false,
        "smtp_checked": true,
        "details": {
          "smtp_code": 250,
          "smtp_response": "2.1.5 OK"
        }
      },
      {
        "email": "user..invalid@syntax.com",
        "category": "likely_to_bounce",
        "category_label": "Likely to bounce",
        "reason": "Email address contains consecutive dots (..)",
        "syntax_valid": false,
        "domain": "",
        "mx_records": [],
        "is_disposable": false,
        "is_role_account": false,
        "is_catch_all": null,
        "smtp_checked": false
      }
    ]
  }
  ```

### 2. Single Email Verification
- **Endpoint**: `GET /api/verify-single?email=user@example.com` or `POST /api/verify-single`

### 3. Health & Diagnostic Check
- **Endpoint**: `GET /api/health`
- **Response**:
  ```json
  {
    "service": "email-deliverability-checker",
    "status": "healthy",
    "version": "1.0.0",
    "diagnostics": {
      "outbound_port_25_accessible": false,
      "port_25_note": "Outbound port 25 is blocked or restricted by the hosting provider/ISP..."
    }
  }
  ```

---

## License
MIT License. Open source and free for commercial and educational use.
