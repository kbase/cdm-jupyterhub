''' User oriented classes and functions. '''

# Copied from https://github.com/kbase/collections

from service.arg_checkers import check_string as _check_string


class UserID:
    '''
    A users's unique name / identifier.
    The ID is expected to be checked against a user registry and so only minimal constraints are
    enforced here.
    :ivar id: the user id.
    '''

    def __init__(self, userid):
        '''
        Create the user id.
        :param id: the user's id, a maximum of 256 unicode characters.
        '''
        self.id = _check_string(userid, 'userid', max_len=256)

    def __str__(self):
        return self.id

    def __repr__(self):
        return f'UserID("{self.id}")'

    def __eq__(self, other):
        if type(self) is type(other):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)