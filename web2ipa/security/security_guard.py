import re
import os
import ipaddress
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

class SSRFProtector:
    """
    Prevents Server-Side Request Forgery (SSRF) when inspecting or converting URLs.
    Blocks private IP spaces, cloud metadata IP (169.254.169.254), and loopback addresses.
    """

    BLOCKED_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}

    @classmethod
    def is_url_safe(cls, url: str) -> Tuple[bool, str]:
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                return False, f"Unsupported scheme: {parsed.scheme}"

            host = (parsed.hostname or "").lower()
            if not host:
                return False, "Empty or invalid hostname"

            if host in cls.BLOCKED_HOSTNAMES:
                return False, f"Blocked target host: {host}"

            # Check if host is an IP address
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return False, f"Access to private/local network address '{host}' is forbidden."
            except ValueError:
                # Not a literal IP, check subdomains for localhost
                if host.endswith(".localhost") or host.endswith(".local"):
                    return False, f"Access to local domain '{host}' is forbidden."

            return True, "URL is safe"
        except Exception as e:
            return False, f"URL parse error: {e}"

class InputSanitizer:
    """
    Sanitizes user input, package/bundle identifiers, file paths, and app titles.
    """
    @classmethod
    def sanitize_bundle_id(cls, bundle_id: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9._-]', '', bundle_id)
        parts = clean.split(".")
        if len(parts) < 2:
            clean = f"com.web2ipa.{clean or 'app'}"
        return clean

    @classmethod
    def sanitize_app_name(cls, app_name: str) -> str:
        clean = re.sub(r'[\r\n\t"\'<>&/\\;]', '', app_name).strip()
        return clean or "iOS App"

    @classmethod
    def is_path_traversal(cls, base_dir: Path, target_path: Path) -> bool:
        try:
            resolved_base = base_dir.resolve()
            resolved_target = target_path.resolve()
            return not str(resolved_target).startswith(str(resolved_base))
        except Exception:
            return True

class VulnerabilityScanner:
    """
    Static Application Security Testing (SAST) Scanner for Web2IPA.
    Audits web assets for OWASP Top 10 vulnerabilities, leaked credentials,
    DOM-based XSS, and insecure WebKit handlers.
    """

    SECRET_PATTERNS = [
        ("CRITICAL", "AWS Access Key ID Leaked", r"AKIA[0-9A-Z]{16}"),
        ("CRITICAL", "Private Cryptographic Key", r"-----BEGIN\s+(?:RSA|OPENSSH|EC|DSA|PRIVATE)\s+KEY-----"),
        ("HIGH", "Stripe Secret Key Leaked", r"sk_(?:live|dummy)_[0-9a-zA-Z]{24}"),
        ("HIGH", "Google API Key Leaked", r"AIza[0-9A-Za-z\-_]{35}"),
        ("HIGH", "GitHub Personal Access Token", r"ghp_[0-9a-zA-Z]{36}"),
        ("MEDIUM", "Hardcoded Secret / API Token", r"(?i)(?:api_key|secret_key|auth_token|client_secret|access_token)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]")
    ]

    DOM_PATTERNS = [
        ("HIGH", "Dangerous Code Execution (eval)", r"\beval\s*\("),
        ("HIGH", "Dynamic Function Constructor Execution", r"\bnew\s+Function\s*\("),
        ("MEDIUM", "Insecure DOM Injection (document.write)", r"\bdocument\.write\s*\("),
        ("MEDIUM", "Unvalidated Cross-Origin Message Listener", r"addEventListener\s*\(\s*['\"]message['\"].*?(?!\.origin)"),
        ("LOW", "Direct innerHTML Assignment (XSS Sink)", r"\.innerHTML\s*=")
    ]

    @classmethod
    def audit_code_snippet(cls, code: str, filename: str = "inline") -> List[Dict[str, Any]]:
        findings = []

        for severity, title, pattern in cls.SECRET_PATTERNS:
            matches = list(re.finditer(pattern, code))
            for m in matches:
                matched_str = m.group(0)
                masked = matched_str[:4] + "*" * (len(matched_str) - 8) + matched_str[-4:] if len(matched_str) > 8 else "***"
                line_no = code[:m.start()].count("\n") + 1
                findings.append({
                    "severity": severity,
                    "title": title,
                    "file": filename,
                    "line": line_no,
                    "evidence": masked,
                    "remediation": "Move secrets to secure server-side environment variables."
                })

        for severity, title, pattern in cls.DOM_PATTERNS:
            matches = list(re.finditer(pattern, code))
            for m in matches:
                line_no = code[:m.start()].count("\n") + 1
                findings.append({
                    "severity": severity,
                    "title": title,
                    "file": filename,
                    "line": line_no,
                    "evidence": m.group(0)[:60],
                    "remediation": "Use safe DOM manipulation APIs (e.g. textContent, structured clones)."
                })

        return findings

    @classmethod
    def audit_directory(cls, dir_path: Path) -> Dict[str, Any]:
        all_findings = []
        files_scanned = 0

        for f in dir_path.glob("**/*"):
            if f.is_file() and f.suffix.lower() in [".html", ".js", ".json", ".ts"]:
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    rel_name = str(f.relative_to(dir_path))
                    findings = cls.audit_code_snippet(content, filename=rel_name)
                    all_findings.extend(findings)
                    files_scanned += 1
                except Exception:
                    pass

        critical_count = sum(1 for f in all_findings if f["severity"] == "CRITICAL")
        high_count = sum(1 for f in all_findings if f["severity"] == "HIGH")
        med_count = sum(1 for f in all_findings if f["severity"] == "MEDIUM")
        low_count = sum(1 for f in all_findings if f["severity"] == "LOW")

        score = 100 - (critical_count * 25 + high_count * 15 + med_count * 8 + low_count * 3)
        score = max(0, min(100, score))
        grade = "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "F"

        return {
            "score": score,
            "grade": grade,
            "files_scanned": files_scanned,
            "total_issues": len(all_findings),
            "critical_issues": critical_count,
            "high_issues": high_count,
            "medium_issues": med_count,
            "low_issues": low_count,
            "findings": all_findings[:50]
        }
