"""Security utilities for input validation."""
import ipaddress
import socket
from urllib.parse import urlparse


def validate_url_no_ssrf(url: str) -> str:
    """Validate URL and prevent SSRF attacks by blocking internal/private IPs."""
    parsed = urlparse(url)
    
    # Only allow http/https
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS URLs are allowed")
    
    # Extract hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")
    
    # Block localhost and common internal hostnames
    blocked_hostnames = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}
    if hostname.lower() in blocked_hostnames:
        raise ValueError("Access to internal addresses is not allowed")
    
    # Resolve hostname and check IP
    try:
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)
        
        # Block private, loopback, link-local, and reserved IPs
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
            raise ValueError("Access to internal/private addresses is not allowed")
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    
    return url