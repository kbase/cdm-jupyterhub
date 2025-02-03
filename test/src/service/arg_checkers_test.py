from src.service.arg_checkers import not_falsy


def test_noop():
    not_falsy(True, "thing")