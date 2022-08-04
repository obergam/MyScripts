from pytest import mark
from selenium import webdriver

@mark.smoke
@mark.body
class BodyTests:
    def test_can_navigate_to_body_page(self):
        assert True

    def test_bumper(self):
        assert True

    def test_windshield(self):
        assert True