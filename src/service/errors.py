"""
Exceptions thrown by the Jupyterhub system.
"""

# mostly copied from https://github.com/kbase/collections

from enum import Enum
from typing import Optional


class ErrorType(Enum):
    """
    The type of an error, consisting of an error code and a brief string describing the type.
    :ivar error_code: an integer error code.
    :ivar error_type: a brief string describing the error type.
    """

    MISSING_PARAMETER = (30000, "Missing input parameter")  # noqa: E222 @IgnorePep8
    """ A required input parameter was not provided. """

    ILLEGAL_PARAMETER = (30001, "Illegal input parameter")  # noqa: E222 @IgnorePep8
    """ An input parameter had an illegal value. """

    def __init__(self, error_code, error_type):
        self.error_code = error_code
        self.error_type = error_type


class JupyterhubError(Exception):
    """
    The super class of all Jupyterhub related errors.
    :ivar error_type: the error type of this error.
    :ivar message: the message for this error.
    """

    def __init__(self, error_type: ErrorType, message: Optional[str] = None):
        '''
        Create a Jupyterhub error.
        :param error_type: the error type of this error.
        :param message: an error message.
        :raises TypeError: if error_type is None
        '''
        if not error_type:  # don't use not_falsy here, causes circular import
            raise TypeError('error_type cannot be None')
        msg = message.strip() if message and message.strip() else None
        super().__init__(msg)
        self.error_type = error_type
        self.message: Optional[str] = message


class MissingParameterError(JupyterhubError):
    """
    An error thrown when a required parameter is missing.
    """

    def __init__(self, message: str = None):
        super().__init__(ErrorType.MISSING_PARAMETER, message)


class IllegalParameterError(JupyterhubError):
    """
    An error thrown when a provided parameter is illegal.
    """

    def __init__(self, message: str = None):
        super().__init__(ErrorType.ILLEGAL_PARAMETER, message)
