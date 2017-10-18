from boac.lib import http
from boac.lib.mockingbird import fixture
from flask import current_app as app


@fixture('canvas_course_sections_{course_id}')
def get_course_sections(course_id, mock=None):
    path = f'/api/v1/courses/{course_id}/sections'
    return paged_request(path=path, mock=mock)


@fixture('canvas_user_for_uid_{uid}')
def get_user_for_uid(uid, mock=None):
    url = build_url(f'/api/v1/users/sis_login_id:{uid}')
    with mock(url):
        return authorized_request(url)


@fixture('canvas_user_courses_{uid}')
def get_user_courses(uid, mock=None):
    path = f'/api/v1/users/sis_login_id:{uid}/courses'
    query = {'include': ['term']}
    response = paged_request(path=path, query=query, mock=mock)
    if not response:
        return response

    def include_course(course):
        # For now, keep things simple by including only student enrollments for the current term as defined in app
        # config.
        if course.get('enrollment_term_id') != app.config.get('CANVAS_CURRENT_ENROLLMENT_TERM'):
            return False
        if not course['enrollments'] or not next((e for e in course['enrollments'] if e['type'] == 'student'), None):
            return False
        return True
    return [course for course in response if include_course(course)]


@fixture('canvas_student_summaries_for_course_{course_id}')
def get_student_summaries(course_id, mock=None):
    path = f'/api/v1/courses/{course_id}/analytics/student_summaries'
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
                return response
            results.extend(response.json())
            url = http.get_next_page(response)
    return results
