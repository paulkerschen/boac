from boac import db
from flask import current_app as app


def load_canvas_externals(uid):
    from boac.externals import canvas

    success_count = 0
    failures = []

    canvas_user_profile = canvas.get_user_for_uid(uid)
    if canvas_user_profile is None:
        failures.append('canvas.get_user_for_uid failed for UID {}'.format(
            uid,
        ))
    elif canvas_user_profile:
        success_count += 1
        sites = canvas.get_student_courses_in_term(uid)
        if sites:
            success_count += 1
            for site in sites:
                site_id = site['id']
                if not canvas.get_course_sections(site_id):
                    failures.append('canvas.get_course_sections failed for UID {}, site_id {}'.format(
                        uid,
                        site_id,
                    ))
                    continue
                success_count += 1
                if not canvas.get_student_summaries(site_id):
                    failures.append('canvas.get_student_summaries failed for site_id {}'.format(
                        site_id,
                    ))
                    continue
                success_count += 1
    return success_count, failures


def load_sis_externals(sis_term_id, csid):
    from boac.externals import sis_enrollments_api, sis_student_api

    success_count = 0
    failures = []

    if sis_student_api.get_student(csid):
        success_count += 1
    else:
        failures.append('SIS get_student failed for CSID {}'.format(
            csid,
        ))

    enrollments = sis_enrollments_api.get_enrollments(csid, sis_term_id)
    if enrollments:
        success_count += 1
    elif enrollments is None:
        failures.append('SIS get_enrollments failed for CSID {}, sis_term_id {}'.format(
            csid,
            sis_term_id,
        ))
    return success_count, failures


def load_current_term():
    from boac.lib import berkeley
    from boac.models.team_member import TeamMember

    success_count = 0
    failures = []

    term_name = app.config['CANVAS_CURRENT_ENROLLMENT_TERM']
    sis_term_id = berkeley.sis_term_id_for_name(term_name)

    # Currently, all external data is loaded starting from the individuals who belong
    # to one or more Cohorts.
    for csid, uid in db.session.query(TeamMember.member_csid, TeamMember.member_uid).distinct():
        s, f = load_canvas_externals(uid)
        success_count += s
        failures += f
        db.session.commit()
        s, f = load_sis_externals(sis_term_id, csid)
        success_count += s
        failures += f
        db.session.commit()

    print('Complete. Fetched {} external feeds.'.format(success_count))
    if len(failures):
        print('Failed to fetch {} feeds:'.format(len(failures)))
        print(failures)


def refresh_current_term():
    from boac.models import json_cache

    json_cache.clear_current_term()
    load_current_term()
