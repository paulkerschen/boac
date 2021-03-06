import csv
import os
from scriptpath import scriptify


os.environ['FIXTURE_OUTPUT_PATH'] = os.path.expanduser('~/tmp/fixtures')


@scriptify.in_app
def main(app):
    from boac.externals import canvas
    request_ctx = app.test_request_context('/')
    request_ctx.push()

    failures = {
        'user_for_uid': [],
        'user_courses': [],
        'student_summaries': [],
    }

    with open(os.path.expanduser('~/tmp/fixtures/cohorts.csv')) as f:
        reader = csv.reader(f)
        headers = next(reader)
        uid_index = headers.index('member_uid')
        for row in reader:
            uid = row[uid_index]

            user_for_uid = canvas._get_user_for_uid(uid)
            if not user_for_uid:
                failures['user_for_uid'].append(uid)

            user_courses = canvas._get_all_user_courses(uid)
            if not user_courses:
                failures['user_courses'].append(uid)
                continue

            for course in user_courses:
                if os.path.isfile('{path}/canvas_student_summaries_for_course_{id}.json'.format(path=os.environ['FIXTURE_OUTPUT_PATH'], id=course['id'])):
                    print('Fixture already present for course {id}, skipping'.format(id=course['id']))
                else:
                    student_summaries = canvas._get_student_summaries(course['id'])
                    if not student_summaries:
                        failures['student_summaries'].append(course['id'])

    print('Complete. Failures below:')
    print(failures)


main()
