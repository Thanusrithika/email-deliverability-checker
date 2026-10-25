"""
Email Verification Engine
Validates email addresses against syntax, DNS/MX records, disposable lists,
and performs RFC-compliant SMTP handshake probes without sending any emails.
"""

import re
import socket
import smtplib
import concurrent.futures
from typing import Dict, Any, List, Optional, Tuple
import dns.resolver

# Standard RFC 5322 simplified regex for email validation
EMAIL_REGEX = re.compile(
    r"^(?P<local>[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+)@"
    r"(?P<domain>[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+)$"
)

# Common disposable email provider domains
DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com",
    "trashmail.com", "yopmail.com", "sharklasers.com", "getairmail.com",
    "throwawaymail.com", "dispostable.com", "fakeinbox.com", "temp-mail.org",
    "temp-mail.io", "nada.ltd", "dropmail.me", "mohmal.com", "crazymailing.com",
    "byom.de", "generator.email", "inboxkitten.com", "burnermail.io",
    "mytemp.email", "maildrop.cc", "emailondeck.com", "fakemailgenerator.com",
    "guerrillamailblock.com", "guerrillamail.net", "guerrillamail.biz", "spam4.me"
}

# Role-based account prefixes
ROLE_PREFIXES = {
    "admin", "administrator", "hostmaster", "postmaster", "webmaster",
    "root", "info", "support", "sales", "contact", "help", "billing",
    "office", "press", "jobs", "careers", "security", "marketing",
    "team", "noreply", "no-reply", "inquiries", "abuse"
}

# In-memory cache for MX records to avoid redundant DNS lookups
_mx_cache: Dict[str, Tuple[bool, List[str], Optional[str]]] = {}
_catchall_cache: Dict[str, Optional[bool]] = {}


def check_syntax(email: str) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    Validates email syntax.
    Returns (is_valid, message, local_part, domain_part).
    """
    email = email.strip()
    if not email:
        return False, "Empty email address", None, None

    if len(email) > 254:
        return False, "Email address exceeds maximum length of 254 characters (RFC 5321)", None, None

    if ".." in email:
        return False, "Email address contains consecutive dots (..)", None, None

    match = EMAIL_REGEX.match(email)
    if not match:
        return False, "Email format does not conform to RFC 5322 syntax", None, None

    local = match.group("local")
    domain = match.group("domain").lower()

    if len(local) > 64:
        return False, "Local part exceeds maximum length of 64 characters", local, domain

    # TLD validation (must be at least 2 characters and not numeric)
    parts = domain.split(".")
    tld = parts[-1]
    if len(tld) < 2 or tld.isdigit():
        return False, f"Invalid top-level domain (.{tld})", local, domain

    return True, "Valid syntax", local, domain


def get_mx_records(domain: str, timeout: float = 3.5) -> Tuple[bool, List[str], Optional[str]]:
    """
    Resolves MX records for a domain.
    Falls back to A/AAAA record if no MX is defined (RFC 5321 fallback).
    Detects Null MX (RFC 7505).
    Returns (has_mail_server, list_of_hosts, error_or_note).
    """
    if domain in _mx_cache:
        return _mx_cache[domain]

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    # Use reliable public DNS resolvers if local DNS fails
    resolver.nameservers = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]

    try:
        answers = resolver.resolve(domain, "MX")
        # Sort MX records by preference
        sorted_records = sorted(answers, key=lambda r: r.preference)
        hosts = []
        for r in sorted_records:
            host_str = str(r.exchange).rstrip(".")
            # RFC 7505 Null MX detection: preference 0 and exchange "."
            if r.preference == 0 and (host_str == "" or host_str == "."):
                result = (False, [], "Null MX record detected (RFC 7505); domain explicitly refuses all email")
                _mx_cache[domain] = result
                return result
            if host_str:
                hosts.append(host_str)

        if hosts:
            result = (True, hosts, None)
            _mx_cache[domain] = result
            return result

    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        # Fallback to A record per RFC 5321 section 5.1
        try:
            a_answers = resolver.resolve(domain, "A")
            if a_answers:
                result = (True, [domain], "No MX records; fallback to domain A record (RFC 5321)")
                _mx_cache[domain] = result
                return result
        except Exception:
            pass
        result = (False, [], "Domain exists but has no MX or A records to receive email")
        _mx_cache[domain] = result
        return result

    except dns.resolver.NXDOMAIN:
        result = (False, [], "Domain does not exist (NXDOMAIN)")
        _mx_cache[domain] = result
        return result

    except dns.resolver.Timeout:
        result = (False, [], "DNS lookup timed out while resolving MX records")
        _mx_cache[domain] = result
        return result

    except Exception as e:
        result = (False, [], f"DNS resolution error: {str(e)}")
        _mx_cache[domain] = result
        return result

    result = (False, [], "No mail exchanger records found")
    _mx_cache[domain] = result
    return result


def is_port_25_accessible(mx_host: str, timeout: float = 2.5) -> bool:
    """Quick check whether outbound port 25 is accessible to this host."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((mx_host, 25))
        s.close()
        return True
    except Exception:
        return False


def probe_smtp_mailbox(
    email: str,
    domain: str,
    mx_hosts: List[str],
    timeout: float = 4.0
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Performs RFC-compliant SMTP handshake probe up to RCPT TO.
    Never sends DATA or message bodies.
    Detects catch-all configurations.
    Returns (category, reason, details).
    Category is one of: 'likely_to_be_delivered', 'likely_to_bounce', 'unknown'.
    """
    if not mx_hosts:
        return (
            "likely_to_bounce",
            "No mail servers found for domain",
            {"smtp_checked": False, "error": "No MX hosts"}
        )

    last_error = ""
    smtp_code = None
    banner_received = False
    details: Dict[str, Any] = {
        "smtp_checked": False,
        "mx_used": None,
        "is_catch_all": None,
        "smtp_code": None,
        "smtp_response": None
    }

    # Try up to top 2 MX hosts
    for mx in mx_hosts[:2]:
        smtp = None
        try:
            details["mx_used"] = mx
            smtp = smtplib.SMTP(timeout=timeout)
            # Connect to port 25
            code, resp = smtp.connect(mx, 25)
            banner_received = True

            if code >= 400:
                details["smtp_code"] = code
                details["smtp_response"] = resp.decode(errors="ignore") if isinstance(resp, bytes) else str(resp)
                if code >= 500:
                    return (
                        "likely_to_bounce",
                        f"Mail server rejected connection banner (SMTP {code})",
                        details
                    )
                return (
                    "unknown",
                    f"Mail server deferred connection banner (SMTP {code}: {details['smtp_response']})",
                    details
                )

            # EHLO / HELO
            try:
                smtp.ehlo_or_helo_if_needed()
            except Exception as e:
                last_error = f"HELO failed: {str(e)}"
                continue

            # MAIL FROM: use null sender or probe sender
            # Using bounce probe <verify-probe@domain> or <>
            probe_sender = f"verify-probe@{domain}"
            try:
                mail_code, mail_resp = smtp.mail(probe_sender)
                if mail_code >= 400:
                    # Retry with null sender
                    mail_code, mail_resp = smtp.mail("<>")
                if mail_code >= 400:
                    details["smtp_code"] = mail_code
                    details["smtp_response"] = str(mail_resp)
                    return (
                        "unknown",
                        f"Mail server rejected probe sender during MAIL FROM (SMTP {mail_code})",
                        details
                    )
            except Exception as e:
                last_error = f"MAIL FROM failed: {str(e)}"
                continue

            # Check for Catch-All domain (if not cached)
            is_catch_all = _catchall_cache.get(domain)
            if is_catch_all is None:
                random_user = "probe_catchall_x7z9q1w3e5r7t"
                random_email = f"{random_user}@{domain}"
                try:
                    rand_code, rand_resp = smtp.rcpt(random_email)
                    if rand_code in (250, 251):
                        is_catch_all = True
                    else:
                        is_catch_all = False
                    _catchall_cache[domain] = is_catch_all
                except Exception:
                    # If random test fails, reset state
                    try:
                        smtp.rset()
                        smtp.mail(probe_sender)
                    except Exception:
                        pass

            details["is_catch_all"] = is_catch_all

            # Now probe the actual target email
            rcpt_code, rcpt_resp = smtp.rcpt(email)
            resp_str = rcpt_resp.decode(errors="ignore") if isinstance(resp_resp := rcpt_resp, bytes) else str(rcpt_resp)
            details["smtp_checked"] = True
            details["smtp_code"] = rcpt_code
            details["smtp_response"] = resp_str

            # Finish session cleanly
            try:
                smtp.quit()
            except Exception:
                pass

            # Interpret RCPT TO response
            if rcpt_code in (250, 251):
                if is_catch_all:
                    return (
                        "unknown",
                        "Server accepted recipient, but domain is a Catch-All (accepts all addresses; mailbox existence cannot be confirmed)",
                        details
                    )
                return (
                    "likely_to_be_delivered",
                    f"Recipient address was verified and accepted by mail server (SMTP {rcpt_code} OK)",
                    details
                )
            elif rcpt_code in (550, 551, 552, 553, 554, 501, 503):
                return (
                    "likely_to_bounce",
                    f"Mailbox rejected by destination server (SMTP {rcpt_code}: {resp_str.strip()})",
                    details
                )
            elif rcpt_code in (421, 450, 451, 452):
                return (
                    "unknown",
                    f"Destination server temporarily deferred recipient check (SMTP {rcpt_code}: {resp_str.strip()}; greylisting or rate-limit)",
                    details
                )
            else:
                return (
                    "unknown",
                    f"Unexpected SMTP response code {rcpt_code}: {resp_str.strip()}",
                    details
                )

        except (socket.timeout, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, ConnectionRefusedError, OSError) as e:
            last_error = str(e)
            if smtp:
                try:
                    smtp.close()
                except Exception:
                    pass
            continue
        except Exception as e:
            last_error = str(e)
            if smtp:
                try:
                    smtp.close()
                except Exception:
                    pass
            continue

    # If we couldn't connect or complete handshake
    if not banner_received:
        return (
            "unknown",
            "Valid MX records exist, but outbound connection to mail server failed (Port 25 blocked by host/ISP or mail server timed out)",
            {
                "smtp_checked": False,
                "error": "Connection timed out or outbound port 25 blocked",
                "details": last_error
            }
        )

    return (
        "unknown",
        f"SMTP handshake incomplete on available mail servers ({last_error or 'Connection reset'})",
        {"smtp_checked": False, "error": last_error}
    )


def verify_email(email: str) -> Dict[str, Any]:
    """
    Main verification pipeline for a single email address.
    Categorizes as:
    - 'likely_to_be_delivered'
    - 'likely_to_bounce'
    - 'unknown'
    """
    raw_email = email.strip()

    # Step 1: Syntax Validation
    syntax_ok, syntax_msg, local_part, domain_part = check_syntax(raw_email)
    if not syntax_ok:
        return {
            "email": raw_email,
            "category": "likely_to_bounce",
            "category_label": "Likely to bounce",
            "reason": syntax_msg,
            "syntax_valid": False,
            "domain": domain_part or "",
            "mx_records": [],
            "is_disposable": False,
            "is_role_account": False,
            "is_catch_all": None,
            "smtp_checked": False,
            "details": {"syntax_error": syntax_msg}
        }

    domain = domain_part.lower()
    local = local_part.lower()

    # Step 2: Disposable Check
    is_disposable = domain in DISPOSABLE_DOMAINS

    # Step 3: Role Account Check
    is_role = local in ROLE_PREFIXES or any(local.startswith(f"{r}.") or local.startswith(f"{r}-") for r in ROLE_PREFIXES)

    # Step 4: MX & DNS Check
    has_mx, mx_hosts, mx_err = get_mx_records(domain)
    if not has_mx:
        return {
            "email": raw_email,
            "category": "likely_to_bounce",
            "category_label": "Likely to bounce",
            "reason": mx_err or "Domain does not have valid MX or address records",
            "syntax_valid": True,
            "domain": domain,
            "mx_records": [],
            "is_disposable": is_disposable,
            "is_role_account": is_role,
            "is_catch_all": None,
            "smtp_checked": False,
            "details": {"dns_error": mx_err}
        }

    # Step 5: SMTP Direct Verification
    category, reason, smtp_details = probe_smtp_mailbox(raw_email, domain, mx_hosts)

    category_labels = {
        "likely_to_be_delivered": "Likely to be delivered",
        "likely_to_bounce": "Likely to bounce",
        "unknown": "Unknown"
    }

    return {
        "email": raw_email,
        "category": category,
        "category_label": category_labels.get(category, "Unknown"),
        "reason": reason,
        "syntax_valid": True,
        "domain": domain,
        "mx_records": mx_hosts,
        "is_disposable": is_disposable,
        "is_role_account": is_role,
        "is_catch_all": smtp_details.get("is_catch_all"),
        "smtp_checked": smtp_details.get("smtp_checked", False),
        "details": smtp_details
    }


def verify_emails_batch(emails: List[str], max_workers: int = 8) -> List[Dict[str, Any]]:
    """
    Verifies a batch of email addresses concurrently.
    Filters out duplicates while preserving order.
    """
    cleaned: List[str] = []
    seen = set()
    for e in emails:
        e_clean = e.strip()
        if e_clean and e_clean not in seen:
            seen.add(e_clean)
            cleaned.append(e_clean)

    if not cleaned:
        return []

    # Map each email to its index to preserve input order
    results = [None] * len(cleaned)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {executor.submit(verify_email, email): i for i, email in enumerate(cleaned)}
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                results[idx] = {
                    "email": cleaned[idx],
                    "category": "unknown",
                    "category_label": "Unknown",
                    "reason": f"Internal verification error: {str(exc)}",
                    "syntax_valid": False,
                    "domain": "",
                    "mx_records": [],
                    "is_disposable": False,
                    "is_role_account": False,
                    "is_catch_all": None,
                    "smtp_checked": False,
                    "details": {"exception": str(exc)}
                }

    return results
