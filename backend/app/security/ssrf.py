"""SSRF (Server-Side Request Forgery) protection utilities for outbound connections."""

import ipaddress
import logging
import socket
from urllib.parse import urlparse
from app.core.config import settings

logger = logging.getLogger(__name__)

# Trusted external domain whitelist (e.g. datahub public demo, openrouter)
_TRUSTED_DOMAINS = {
    "demo.datahubproject.io",
    "openrouter.ai",
    "api.openai.com",
    "api.together.xyz",
    "api.groq.com",
    "api.mistral.ai",
    "api.deepseek.com",
}


def is_safe_url(url: str, allow_loopback: bool = None) -> bool:
    """Validate if an outbound URL is safe to access, preventing SSRF attacks.
    
    Checks host resolution, private IP ranges (RFC 1918), link-local, and protocols.
    """
    if not url:
        return False
        
    if allow_loopback is None:
        allow_loopback = settings.DEV_MODE

    try:
        parsed = urlparse(url)
        # 1. Enforce protocol whitelist
        if parsed.scheme not in ("http", "https"):
            logger.warning("SSRF check failed: Unsupported URL scheme '%s'", parsed.scheme)
            return False
            
        host = parsed.hostname
        if not host:
            logger.warning("SSRF check failed: No hostname in URL '%s'", url)
            return False
            
        # If it is in the trusted domain list, allow immediately
        if host.lower() in _TRUSTED_DOMAINS:
            return True
            
        # 2. Resolve DNS to get IP addresses
        # This prevents DNS rebinding attacks if validated on resolved IP
        ips = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        resolved_ips = [ip[4][0] for ip in ips]
        
        for ip_str in resolved_ips:
            # Handle IPv6 brackets
            if ip_str.startswith("[") and ip_str.endswith("]"):
                ip_str = ip_str[1:-1]
            # Strip scope id on IPv6 link-local
            ip_str = ip_str.split("%")[0]
            
            ip = ipaddress.ip_address(ip_str)
            
            # 3. Block loopback if configured
            if ip.is_loopback:
                if not allow_loopback:
                    logger.warning("SSRF Blocked loopback IP '%s' for URL '%s'", ip_str, url)
                    return False
                continue
                
            # 4. Block private networks (RFC 1918)
            if ip.is_private:
                logger.warning("SSRF Blocked private IP '%s' for URL '%s'", ip_str, url)
                return False
                
            # 5. Block link-local (169.254.x.x - AWS/Metadata endpoints) and multicast
            if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
                logger.warning("SSRF Blocked system reserved IP '%s' for URL '%s'", ip_str, url)
                return False
                
        return True
    except Exception as e:
        logger.warning("SSRF validation exception for URL '%s': %s", url, e)
        return False
