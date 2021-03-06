import boac.externals.sis_student_api as student_api
from boac.lib.mockingbird import MockResponse, register_mock
import pytest


class TestSisStudentApi:
    """SIS student API query"""

    def test_get_student(self, app):
        """returns unwrapped data"""
        student = student_api.get_student(11667051)
        assert student['academicStatuses'][0]['cumulativeGPA']['average'] == pytest.approx(3.8, 0.01)
        assert student['academicStatuses'][0]['currentRegistration']['academicLevel']['level']['description'] == 'Junior'
        assert student['academicStatuses'][0]['currentRegistration']['athlete'] is True
        assert student['academicStatuses'][0]['studentPlans'][0]['academicPlan']['plan']['description'] == 'English BA'
        assert student['emails'][0]['emailAddress'] == 'oski@berkeley.edu'

    def test_inner_get_student(self, app):
        """returns fixture data"""
        oski_response = student_api._get_student(11667051)
        assert oski_response
        assert oski_response.status_code == 200
        students = oski_response.json()['apiResponse']['response']['any']['students']
        assert len(students) == 1

    def test_user_not_found(self, app, caplog):
        """logs 404 for unknown user and returns informative message"""
        response = student_api._get_student(9999999)
        assert 'HTTP/1.1" 404' in caplog.text
        assert not response
        assert response.raw_response.status_code == 404
        assert response.raw_response.json()['message']

    def test_server_error(self, app, caplog):
        """logs unexpected server errors and returns informative message"""
        api_error = MockResponse(500, {}, '{"message": "Internal server error."}')
        with register_mock(student_api._get_student, api_error):
            response = student_api._get_student(11667051)
            assert 'HTTP/1.1" 500' in caplog.text
            assert not response
            assert response.raw_response.status_code == 500
            assert response.raw_response.json()['message']
