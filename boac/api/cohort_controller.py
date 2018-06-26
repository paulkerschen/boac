"""
Copyright ©2018. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""


from boac.api.errors import BadRequestError, ForbiddenRequestError, ResourceNotFoundError
from boac.api.util import strip_analytics
from boac.lib import util
from boac.lib.berkeley import is_department_member
from boac.lib.http import tolerant_jsonify
from boac.merged import calnet
from boac.merged import student_details
from boac.models.cohort_filter import CohortFilter
from flask import current_app as app, request
from flask_login import current_user, login_required


@app.route('/api/cohorts/all')
@login_required
def all_cohorts():
    if not current_user.is_admin and not is_department_member(current_user, 'UWASC'):
        raise ForbiddenRequestError('You are unauthorized to browse data that is managed by other departments')
    cohorts = {}
    for cohort in CohortFilter.all_cohorts():
        for uid in cohort['owners']:
            if uid not in cohorts:
                cohorts[uid] = []
            cohorts[uid].append(cohort)
    owners = []
    for uid in cohorts.keys():
        owner = calnet.get_calnet_user_for_uid(app, uid)
        owner.update({
            'cohorts': sorted(cohorts[uid], key=lambda c: c['name']),
        })
        owners.append(owner)
    owners = sorted(owners, key=lambda o: (o['firstName'], o['lastName']))
    return tolerant_jsonify(owners)


@app.route('/api/cohorts/my')
@login_required
def my_cohorts():
    cohorts = CohortFilter.all_owned_by(current_user.get_id(), include_alerts=True)
    for cohort in cohorts:
        student_details.merge_external_students_data(cohort['alerts'])
        for data in cohort['alerts']:
            strip_analytics(data)
    return tolerant_jsonify(cohorts)


@app.route('/api/cohort/<cohort_id>')
@login_required
def get_cohort(cohort_id):
    order_by = util.get(request.args, 'orderBy', None)
    offset = util.get(request.args, 'offset', 0)
    limit = util.get(request.args, 'limit', 50)
    cohort = CohortFilter.find_by_id(int(cohort_id), order_by, int(offset), int(limit))
    if not cohort:
        raise ResourceNotFoundError(f'No cohort found with identifier: {cohort_id}')
    student_details.merge_external_students_data(cohort['students'])
    return tolerant_jsonify(cohort)


@app.route('/api/cohort/create', methods=['POST'])
@login_required
def create_cohort():
    params = request.get_json()
    label = util.get(params, 'label', None)
    gpa_ranges = util.get(params, 'gpaRanges')
    group_codes = util.get(params, 'groupCodes')
    levels = util.get(params, 'levels')
    majors = util.get(params, 'majors')
    unit_ranges = util.get(params, 'unitRanges')
    in_intensive_cohort = util.to_bool_or_none(util.get(params, 'inIntensiveCohort'))
    is_inactive_asc = util.get(params, 'isInactiveAsc')
    if not label:
        raise BadRequestError('Cohort creation requires \'label\'')
    asc_authorized = current_user.is_admin or is_department_member(current_user, 'UWASC')
    if not asc_authorized and (in_intensive_cohort is not None or is_inactive_asc is not None):
        raise ForbiddenRequestError('You are unauthorized to access student data managed by other departments')
    cohort = CohortFilter.create(
        uid=current_user.get_id(),
        label=label,
        gpa_ranges=gpa_ranges,
        group_codes=group_codes,
        levels=levels,
        majors=majors,
        unit_ranges=unit_ranges,
        in_intensive_cohort=in_intensive_cohort,
        is_inactive_asc=is_inactive_asc,
    )
    return tolerant_jsonify(cohort)


@app.route('/api/cohort/update', methods=['POST'])
@login_required
def update_cohort():
    params = request.get_json()
    uid = current_user.get_id()
    label = params['label']
    if not label:
        raise BadRequestError('Requested cohort label is empty or invalid')
    cohort = get_cohort_owned_by(params['id'], uid)
    if not cohort:
        raise BadRequestError(f'Cohort does not exist or is not owned by {uid}')
    cohort = CohortFilter.update(cohort_id=cohort['id'], label=label)
    return tolerant_jsonify(cohort)


@app.route('/api/cohort/delete/<cohort_id>', methods=['DELETE'])
@login_required
def delete_cohort(cohort_id):
    if cohort_id.isdigit():
        cohort_id = int(cohort_id)
        uid = current_user.get_id()
        cohort = get_cohort_owned_by(cohort_id, uid)
        if cohort:
            CohortFilter.delete(cohort_id)
            return tolerant_jsonify({'message': f'Cohort deleted (id={cohort_id})'}), 200
        else:
            raise BadRequestError(f'User {uid} does not own cohort_filter with id={cohort_id}')
    else:
        raise ForbiddenRequestError(f'Programmatic deletion of canned cohorts is not allowed (id={cohort_id})')


def get_cohort_owned_by(cohort_filter_id, uid):
    return next((c for c in CohortFilter.all_owned_by(uid) if c['id'] == cohort_filter_id), None)
