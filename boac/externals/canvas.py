from boac.lib import http
from boac.lib.mockingbird import fixture
from boac.models.json_cache import stow
from flask import current_app as app


@stow('canvas_course_sections_{course_id}', for_term=True)
def get_course_sections(course_id):
    return _get_course_sections(course_id)


@fixture('canvas_course_sections_{course_id}')
def _get_course_sections(course_id, mock=None):
    path = '/api/v1/courses/{course_id}/sections'.format(course_id=course_id)
    return paged_request(path=path, mock=mock)


@stow('canvas_user_for_uid_{uid}')
def get_user_for_uid(uid):
    """If the user is not found, returns False (which can be cached).
    For any other error response, returns None (which will not be cached).
    """
    response = _get_user_for_uid(uid)
    if response and hasattr(response, 'json'):
        return response.json()
    else:
        if hasattr(response, 'raw_response') and response.raw_response.status_code == 404:
            return False
        else:
            return None


@fixture('canvas_user_for_uid_{uid}')
def _get_user_for_uid(uid, mock=None):
    url = build_url('/api/v1/users/sis_login_id:{uid}'.format(uid=uid))
    with mock(url):
        return authorized_request(url)


def get_student_courses_in_term(uid):
    term_name = app.config['CANVAS_CURRENT_ENROLLMENT_TERM']
    all_canvas_courses = get_all_user_courses(uid)
    # The paged_request wrapper returns either a list of course sites or None to signal HTTP request failure.
    # An empty list should be handled by higher-level logic even though it's falsey.
    if all_canvas_courses is None:
        return None

    def include_course(course):
        if course.get('term', {}).get('name') == term_name and course['enrollments']:
            if next((e for e in course['enrollments'] if e['type'] == 'student'), None):
                return True
        return False

    return [course for course in all_canvas_courses if include_course(course)]


@stow('canvas_user_courses_{uid}')
def get_all_user_courses(uid):
    return _get_all_user_courses(uid)


@fixture('canvas_user_courses_{uid}')
def _get_all_user_courses(uid, mock=None):
    path = '/api/v1/users/sis_login_id:{uid}/courses'.format(uid=uid)
    query = {'include': ['term']}
    return paged_request(path=path, query=query, mock=mock)


@stow('canvas_student_summaries_for_course_{course_id}', for_term=True)
def get_student_summaries(course_id):
    return _get_student_summaries(course_id)


@fixture('canvas_student_summaries_for_course_{course_id}')
def _get_student_summaries(course_id, mock=None):
    path = '/api/v1/courses/{course_id}/analytics/student_summaries'.format(course_id=course_id)
    return paged_request(path=path, mock=mock)


def build_url(path, query=None):
    working_url = app.config['CANVAS_HTTP_URL'] + path
    return http.build_url(working_url, query)


def authorized_request(url):
    auth_headers = {'Authorization': 'Bearer {}'.format(app.config['CANVAS_HTTP_TOKEN'])}
    return http.request(url, auth_headers)


def paged_request(path, mock, query=None):
    if query is None:
        query = {}
    query['per_page'] = 100
    url = build_url(
        path,
        query,
    )
    results = []
    while url:
        with mock(url):
            response = authorized_request(url)
            if not response:
                return None
            results.extend(response.json())
            url = http.get_next_page(response)
    return results
