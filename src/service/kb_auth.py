"""
A client for the KBase Auth2 server.
"""

# Mostly copied from https://github.com/kbase/collections


import logging
from datetime import datetime, timezone
from enum import IntEnum
from typing import NamedTuple, List, Optional

import aiohttp
from tornado import web

from service.arg_checkers import not_falsy as _not_falsy
from service.kb_user import UserID


class AdminPermission(IntEnum):
    '''
    The different levels of admin permissions.
    '''
    NONE = 1
    # leave some space for potential future levels
    FULL = 10


class KBaseUser(NamedTuple):
    user: UserID
    admin_perm: AdminPermission
    token: str
    expires: Optional[datetime] = None
    mfa_status: Optional[str] = None


async def _get(url, headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as r:
            await _check_error(r)
            return await r.json()


async def _check_error(r):
    if r.status != 200:
        try:
            j = await r.json()
        except Exception:
            err = ('Non-JSON response from KBase auth server, status code: ' +
                   str(r.status))
            logging.getLogger(__name__).info('%s, response:\n%s', err, r.text)
            raise IOError(err)
        # assume that if we get json then at least this is the auth server and we can
        # rely on the error structure.
        if j['error'].get('appcode') == 10020:  # Invalid token
            raise InvalidTokenError('KBase auth server reported token is invalid.')
        # don't really see any other error codes we need to worry about - maybe disabled?
        # worry about it later.
        raise IOError('Error from KBase auth server: ' + j['error']['message'])


class KBaseAuth:
    ''' A client for contacting the KBase authentication server. '''

    def __init__(
            self,
            auth_url: str,
            full_admin_roles: List[str]):
        self._url = auth_url
        self._token_url = self._url + 'api/V2/token'
        self._me_url = self._url + 'api/V2/me'
        self._full_roles = set(full_admin_roles) if full_admin_roles else set()


    async def validate_token(self, token: str) -> KBaseUser:
        '''
        Validate a token and get user information with expiration using auth2/token and auth2/me.
        :param token: The user's token.
        :returns: the user with token expiration information.
        '''
        _not_falsy(token, 'token')

        token_data = await _get(self._token_url, {"Authorization": token})
        me_data = await _get(self._me_url, {"Authorization": token})

        expires_ms = token_data.get('expires')
        expires = None
        if expires_ms:
            expires = datetime.fromtimestamp(expires_ms / 1000.0, tz=timezone.utc)

        roles = me_data.get('customroles', [])
        admin_perm = self._get_role(roles)

        mfa_status = token_data.get('mfa')

        username = me_data.get('user')
        if not username:
            raise InvalidTokenError('Invalid token response - missing username')

        return KBaseUser(UserID(username), admin_perm, token, expires, mfa_status)

    def _get_role(self, roles):
        r = set(roles)
        if r & self._full_roles:
            return AdminPermission.FULL
        return AdminPermission.NONE


class AuthenticationError(web.HTTPError):
    ''' An error thrown from the authentication service. '''

    def __init__(self, status_code=400, log_message=None, *args, **kwargs):
        super().__init__(status_code, log_message or "Authentication error", *args, **kwargs)


class InvalidTokenError(AuthenticationError):
    ''' An error thrown when a token is invalid. '''

    def __init__(self, log_message=None, *args, **kwargs):
        super().__init__(status_code=401, log_message=log_message or "Invalid session token format", *args, **kwargs)


class MissingTokenError(AuthenticationError):
    ''' An error thrown when a token is missing. '''

    def __init__(self, log_message=None, *args, **kwargs):
        super().__init__(status_code=401, log_message=log_message or "Missing session token", *args, **kwargs)
