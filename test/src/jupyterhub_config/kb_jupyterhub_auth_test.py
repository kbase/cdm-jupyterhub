from jupyterhub_config.kb_jupyterhub_auth import kbase_origin


def test_noop():
    assert kbase_origin() == "ci.kbase.us"
