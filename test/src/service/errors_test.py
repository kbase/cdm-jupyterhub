from src.service.errors import ErrorType


def test_noop():
    assert ErrorType.ILLEGAL_PARAMETER != ErrorType.MISSING_PARAMETER