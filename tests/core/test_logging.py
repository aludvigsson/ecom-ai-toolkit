import logging

from core.logging import get_logger


def test_get_logger_returns_logger_instance():
    log = get_logger("test")
    assert isinstance(log, logging.Logger)


def test_get_logger_name_is_namespaced():
    log = get_logger("ecom.test")
    assert log.name == "ecom.test"


def test_get_logger_is_idempotent():
    a = get_logger("dup")
    b = get_logger("dup")
    assert a is b
