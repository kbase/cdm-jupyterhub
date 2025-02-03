"""
A client for the KBase Auth2 server.
"""

# Mostly copied from https://github.com/kbase/collections


import logging
import time
from enum import IntEnum
from typing import NamedTuple, Self, List

import aiohttp
from cacheout.lru import LRUCache
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

    @classmethod
    async def create(
            cls,
            auth_url: str,
            full_admin_roles: List[str] = None,
            cache_max_size: int = 10000,
            cache_expiration: int = 300
    ) -> Self:
        '''
        Create the client.
        :param auth_url: The root url of the authentication service.
        :param full_admin_roles: The KBase Auth2 roles that imply the user is an administrator.
        :param cache_max_size: the maximum size of the token cache.
        :param cache_expiration: the expiration time for the token cache in
            seconds.
        '''
        if not _not_falsy(auth_url, "auth_url").endswith('/'):
            auth_url += '/'
        j = await _get(auth_url, {'Accept': 'application/json'})
        return KBaseAuth(
            auth_url, full_admin_roles, cache_max_size, cache_expiration, j.get('servicename')
        )

    def __init__(
            self,
            auth_url: str,
            full_admin_roles: List[str],
            cache_max_size: int,
            cache_expiration: int,
            service_name: str):
        self._url = auth_url
        self._me_url = self._url + 'api/V2/me'
        self._full_roles = set(full_admin_roles) if full_admin_roles else set()
        self._cache_timer = time.time
        self._admin_cache = LRUCache(timer=self._cache_timer, maxsize=cache_max_size,
                                     ttl=cache_expiration)

        if service_name != 'Authentication Service':
            raise IOError(f'The service at {self._url} does not appear to be the KBase ' +
                          'Authentication Service')

        # could use the server time to adjust for clock skew, probably not worth the trouble

    async def get_user(self, token: str) -> KBaseUser:
        '''
        Get a username from a token as well as the user's administration status.
        :param token: The user's token.
        :returns: the user.
        '''
        # TODO CODE should check the token for \n etc.
        _not_falsy(token, 'token')

        admin_cache = self._admin_cache.get(token, default=False)
        if admin_cache:
            return KBaseUser(admin_cache[1], admin_cache[0], token)
        j = await _get(self._me_url, {"Authorization": token})
        v = (self._get_role(j['customroles']), UserID(j['user']))
        self._admin_cache.set(token, v)
        return KBaseUser(v[1], v[0], token)

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