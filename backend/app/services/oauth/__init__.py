"""External-identity (OAuth / OIDC) provider integrations.

Currently houses the Google flow under ``google.py``. Future providers
(GitHub, Microsoft) plug in by adding a sibling module and reusing the
:class:`app.services.oauth.google.GoogleUserInfo` shape.
"""
