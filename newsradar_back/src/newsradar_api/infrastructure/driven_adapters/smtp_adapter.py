"""SMTP adapter — sends newsletter emails for vigilancia subscriptions.

Connects to an SMTP server to deliver periodic vigilancia
bulletins to subscribed users.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SMTPAdapter:
    """SMTP adapter for sending vigilancia newsletter emails.

    Parameters
    ----------
    host : str
        SMTP server hostname.
    port : int
        SMTP server port.
    """

    def __init__(self, host: str = "localhost", port: int = 587) -> None:
        self._host = host
        self._port = port

    async def send_newsletter(
        self, to_email: str, subject: str, html_body: str
    ) -> bool:
        """Send a newsletter email to a subscriber.

        Parameters
        ----------
        to_email : str
            Recipient email address.
        subject : str
            Email subject line.
        html_body : str
            HTML content of the newsletter.

        Returns
        -------
        bool
            True if sent successfully, False otherwise.
        """
        # TODO: Implement SMTP email sending
        raise NotImplementedError("TODO: implement SMTP newsletter sending")
