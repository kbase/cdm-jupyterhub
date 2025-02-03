from service.kb_user import UserID


def test_noop():
    assert UserID("foo") != UserID("bar")