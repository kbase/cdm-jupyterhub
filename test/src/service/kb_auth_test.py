from service.kb_auth import AdminPermission


def test_noop():
    assert AdminPermission.NONE != AdminPermission.FULL