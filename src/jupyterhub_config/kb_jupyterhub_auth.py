import logging
import os

from jupyterhub.auth import Authenticator
from traitlets import Unicode, List

from service.kb_auth import KBaseAuth, MissingTokenError, MFARequiredError, AdminPermission

logger = logging.getLogger(__name__)


def kbase_origin() -> str:
    """
    Get the KBase origin based on the KB_ENV environment variable.

    Returns:
        str: The KBase origin. (default: ci.kbase.us)
    """
    kb_env = os.getenv("KB_ENV", "ci").lower()
    return "kbase.us" if kb_env == "prod" else f"{kb_env}.kbase.us"


class KBaseAuthenticator(Authenticator):
    """
    Custom JupyterHub Authenticator for KBase.
    Authenticates users by verifying the 'kbase_session' cookie
    against the KBase Auth2 API.

    For custom authenticators, refer to the JupyterHub documentation:
    https://jupyterhub.readthedocs.io/en/latest/reference/authenticators.html#authenticators
    """

    SESSION_COOKIE_NAME = "kbase_session"

    kbase_auth_url = Unicode(
        default_value=f"https://{kbase_origin()}/services/auth/",
        config=True,
        help="KBase Auth2 API URL (e.g., https://ci.kbase.us/services/auth/)"
    )

    auth_full_admin_roles = List(
        default_value=[
            role.strip() for role in os.getenv("AUTH_FULL_ADMIN_ROLES", "").split(",") if role.strip()
        ],
        config=True,
        help="Comma-separated list of KBase roles with full administrative access to JupyterHub."
    )

    async def authenticate(self, handler, data=None) -> dict:
        """
        Authenticate user using KBase session cookie and API validation
        """
        session_token = handler.get_cookie(self.SESSION_COOKIE_NAME)

        if not session_token:
            raise MissingTokenError(f"Authentication required - missing {self.SESSION_COOKIE_NAME} cookie.")

        kb_auth = KBaseAuth(self.kbase_auth_url, self.auth_full_admin_roles)
        kb_user = await kb_auth.get_user(session_token)

        # Check MFA requirement
        if kb_user.mfa_authenticated is False or kb_user.mfa_authenticated is None:
            raise MFARequiredError()

        logger.info(f"Authenticated user: {kb_user.user}")
        return {
            "name": str(kb_user.user),
            "admin": kb_user.admin_perm == AdminPermission.FULL,
            "auth_state": {
                "kbase_token": session_token,
            }
        }

    async def pre_spawn_start(self, user, spawner) -> None:
        """
        Pass KBase authentication token to spawner environment
        """
        auth_state = await user.get_auth_state() or {}
        kbase_auth_token = auth_state.get("kbase_token")

        if not kbase_auth_token:
            raise MissingTokenError("Missing KBase authentication token in auth state")

        spawner.environment["KBASE_AUTH_TOKEN"] = kbase_auth_token
