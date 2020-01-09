"""
Copyright ©2020. The Regents of the University of California (Regents). All Rights Reserved.

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

from boac import std_commit
from boac.merged import calnet
from boac.models.authorized_user import AuthorizedUser
from boac.models.drop_in_advisor import DropInAdvisor
from boac.models.json_cache import insert_row as insert_in_json_cache
from boac.models.university_dept import UniversityDept
from flask import current_app as app
import simplejson as json
from tests.util import override_config

admin_uid = '2040'
asc_advisor_uid = '1081940'
coe_advisor_uid = '1133399'
coe_scheduler_uid = '6972201'
deleted_user_csid = '333333333'
deleted_user_uid = '33333'
l_s_college_scheduler_uid = '19735'
l_s_college_advisor_uid = '188242'
l_s_college_drop_in_advisor_uid = '53791'


class TestUserProfile:
    """User Profile API."""

    @staticmethod
    def _api_my_profile(client, expected_status_code=200):
        response = client.get('/api/profile/my')
        assert response.status_code == expected_status_code
        return response.json

    def test_profile_not_authenticated(self, client):
        """Returns a well-formed response."""
        api_json = self._api_my_profile(client)
        assert api_json['isAuthenticated'] is False
        assert not api_json['uid']

    def test_includes_canvas_profile_if_available(self, client, fake_auth):
        """Includes user profile info from Canvas."""
        fake_auth.login(admin_uid)
        api_json = self._api_my_profile(client)
        assert api_json['isAuthenticated'] is True
        assert api_json['uid'] == admin_uid
        assert 'csid' in api_json
        assert 'firstName' in api_json
        assert 'lastName' in api_json

    def test_user_with_no_dept_membership(self, client, fake_auth):
        """Returns zero or more departments."""
        fake_auth.login(admin_uid)
        api_json = self._api_my_profile(client)
        assert api_json['isAdmin'] is True
        assert not len(api_json['departments'])

    def test_user_with_scheduler_role(self, client, fake_auth):
        """Returns COE scheduler profile."""
        fake_auth.login(coe_scheduler_uid)
        api_json = self._api_my_profile(client)
        assert api_json['isAdmin'] is False
        assert api_json['canAccessCanvasData'] is False
        assert not api_json['dropInAdvisorStatus']
        departments = api_json['departments']
        assert len(departments) == 1
        assert departments[0]['code'] == 'COENG'
        assert departments[0]['name'] == 'College of Engineering'
        assert departments[0]['isAdvisor'] is False
        assert departments[0]['isDirector'] is False
        assert departments[0]['isScheduler'] is True

    def test_non_drop_in_dept_user(self, client, fake_auth):
        """Excludes drop-in status when dept is not configured for drop-in advising."""
        fake_auth.login(coe_advisor_uid)
        api_json = self._api_my_profile(client)
        assert not api_json['dropInAdvisorStatus']

    def test_advisor_with_drop_in_disabled(self, client, fake_auth):
        """Includes drop-in advising status that has been disabled/deleted."""
        dept_code = 'COENG'
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', [dept_code]):
            user = AuthorizedUser.find_by_uid(coe_advisor_uid)
            DropInAdvisor.delete(authorized_user_id=user.id, dept_code=dept_code)
            fake_auth.login(coe_advisor_uid)
            api_json = self._api_my_profile(client)
            assert api_json['dropInAdvisorStatus']
            assert api_json['dropInAdvisorStatus'][0]['deptCode'] == dept_code
            assert api_json['dropInAdvisorStatus'][0]['isEnabled'] is False

    def test_asc_advisor_exclude_cohorts(self, client, fake_auth):
        """Returns Athletic Study Center drop-in advisor."""
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['UWASC']):
            fake_auth.login(asc_advisor_uid)
            api_json = self._api_my_profile(client)
            assert api_json['canAccessCanvasData'] is True
            assert api_json['dropInAdvisorStatus'] == [{'deptCode': 'UWASC', 'isEnabled': True, 'status': 'on_duty_advisor'}]
            departments = api_json['departments']
            assert len(departments) == 1
            assert departments[0]['code'] == 'UWASC'
            assert departments[0]['name'] == 'Athletic Study Center'
            assert departments[0]['isAdvisor'] is True
            assert departments[0]['isDirector'] is False
            assert departments[0]['isScheduler'] is False

    def test_other_user_profile(self, client, fake_auth):
        fake_auth.login(admin_uid)
        response = client.get('/api/profile/6446')
        assert response.json['uid'] == '6446'
        assert 'firstName' in response.json
        assert 'lastName' in response.json

    def test_other_user_profile_not_found(self, client, fake_auth):
        fake_auth.login(admin_uid)
        response = client.get('/api/profile/2549')
        assert response.status_code == 404


class TestCalnetProfileById:
    """Calnet Profile API."""

    def test_user_by_uid_not_authenticated(self, client):
        """Returns 401 when not authenticated."""
        user = AuthorizedUser.find_by_uid(asc_advisor_uid)
        response = client.get(f'/api/user/calnet_profile/by_uid/{user.uid}')
        assert response.status_code == 401

    def test_user_by_uid(self, client, fake_auth):
        """Delivers CalNet profile."""
        fake_auth.login(admin_uid)
        user = AuthorizedUser.find_by_uid(asc_advisor_uid)
        response = client.get(f'/api/user/calnet_profile/by_uid/{user.uid}')
        assert response.status_code == 200
        assert response.json['uid'] == asc_advisor_uid

    def test_user_by_csid_not_authenticated(self, client):
        """Returns 401 when not authenticated."""
        response = client.get(f'/api/user/calnet_profile/by_csid/{81067873}')
        assert response.status_code == 401

    def test_user_by_csid(self, client, fake_auth):
        """Delivers CalNet profile."""
        fake_auth.login(admin_uid)
        response = client.get(f'/api/user/calnet_profile/by_csid/{81067873}')
        assert response.status_code == 200
        assert response.json['csid'] == '81067873'


class TestUserByUid:
    """User by UID API."""

    def test_not_authenticated(self, client):
        """Returns 401 when not authenticated."""
        user = AuthorizedUser.find_by_uid(asc_advisor_uid)
        response = client.get(f'/api/user/by_uid/{user.uid}')
        assert response.status_code == 401

    def test_user_not_found(self, client, fake_auth):
        """404 when user not found."""
        fake_auth.login(admin_uid)
        assert client.get('/api/user/by_uid/99999999999999999').status_code == 404

    def test_deleted_user_not_found(self, client, fake_auth):
        """404 is default if get deleted user by UID."""
        fake_auth.login(admin_uid)
        assert client.get(f'/api/user/by_uid/{deleted_user_uid}').status_code == 404
        assert client.get(f'/api/user/by_uid/{deleted_user_uid}?ignoreDeleted=true').status_code == 404

    def test_get_deleted_user_by_uid(self, client, fake_auth):
        """Get deleted user by UID if specific param is passed."""
        fake_auth.login(admin_uid)
        response = client.get(f'/api/user/by_uid/{deleted_user_uid}?ignoreDeleted=false')
        assert response.status_code == 200
        assert response.json['uid'] == deleted_user_uid

    def test_user_by_csid(self, client, fake_auth):
        """Delivers CalNet profile."""
        fake_auth.login(admin_uid)
        response = client.get('/api/user/by_uid/1133399')
        assert response.status_code == 200
        assert response.json['csid'] == '800700600'
        assert response.json['uid'] == '1133399'


class TestUniversityDeptMember:
    """University Dept Member API."""

    @classmethod
    def _api_add(
            cls,
            client,
            is_advisor=True,
            is_director=False,
            is_scheduler=False,
            automate_membership=False,
            expected_status_code=200,
    ):
        params = {
            'deptCode': 'ZZZZZ',
            'uid': coe_advisor_uid,
            'isAdvisor': is_advisor,
            'isDirector': is_director,
            'isScheduler': is_scheduler,
            'automateMembership': automate_membership,
        }
        response = client.post(
            f'/api/user/dept_membership/add',
            data=json.dumps(params),
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return response.json

    @classmethod
    def _api_update(
            cls,
            client,
            is_advisor=None,
            is_director=None,
            is_scheduler=None,
            automate_membership=None,
            expected_status_code=200,
    ):
        params = {
            'deptCode': 'ZZZZZ',
            'uid': coe_advisor_uid,
            'isAdvisor': is_advisor,
            'isDirector': is_director,
            'isScheduler': is_scheduler,
            'automateMembership': automate_membership,
        }
        response = client.post(
            f'/api/user/dept_membership/update',
            data=json.dumps(params),
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return response.json

    @classmethod
    def _api_delete(cls, client, expected_status_code=200):
        university_dept_id = UniversityDept.find_by_dept_code('ZZZZZ').id
        authorized_user_id = AuthorizedUser.find_by_uid(coe_advisor_uid).id
        response = client.delete(
            f'/api/user/dept_membership/delete/{university_dept_id}/{authorized_user_id}',
        )
        assert response.status_code == expected_status_code
        return response.json

    def test_add_university_dept_membership_not_authenticated(self, client):
        """Returns 401 when unauthenticated user attempts to add."""
        self._api_add(client, expected_status_code=401)

    def test_add_university_dept_membership_not_authorized(self, client, fake_auth):
        """Returns 401 when non-admin attempts to add."""
        fake_auth.login(asc_advisor_uid)
        self._api_add(client, expected_status_code=401)

    def test_add_university_dept_membership(self, client, fake_auth):
        """Creates a UniversityDeptMember record."""
        fake_auth.login(admin_uid)
        membership = self._api_add(client)
        assert membership['universityDeptId'] == UniversityDept.find_by_dept_code('ZZZZZ').id
        assert membership['authorizedUserId'] == AuthorizedUser.find_by_uid(coe_advisor_uid).id
        assert membership['isAdvisor'] is True
        assert membership['isDirector'] is False
        assert membership['automateMembership'] is False

    def test_update_university_dept_membership_not_authenticated(self, client):
        """Returns 401 when unauthenticated user attempts to update."""
        self._api_update(client, expected_status_code=401)

    def test_update_university_dept_membership_not_authorized(self, client, fake_auth):
        """Returns 401 when non-admin attempts to update."""
        fake_auth.login(asc_advisor_uid)
        self._api_update(client, expected_status_code=401)

    def test_update_nonexistant_university_dept_membership(self, client, fake_auth):
        """Returns 404 when attempting to update a nonexistant UniversityDeptMember record."""
        fake_auth.login(admin_uid)
        self._api_update(client, expected_status_code=400)

    def test_update_university_dept_membership(self, client, fake_auth):
        """Updates a UniversityDeptMember record."""
        fake_auth.login(admin_uid)
        self._api_add(client)
        membership = self._api_update(client, is_advisor=False, is_director=True)
        assert membership['universityDeptId'] == UniversityDept.find_by_dept_code('ZZZZZ').id
        assert membership['authorizedUserId'] == AuthorizedUser.find_by_uid(coe_advisor_uid).id
        assert membership['isAdvisor'] is False
        assert membership['isDirector'] is True
        assert membership['automateMembership'] is False

    def test_delete_university_dept_membership_not_authenticated(self, client):
        """Returns 401 when unauthenticated user attempts to delete."""
        self._api_delete(client, 401)

    def test_delete_university_dept_membership_not_authorized(self, client, fake_auth):
        """Returns 401 when non-admin attempts to delete."""
        fake_auth.login(asc_advisor_uid)
        self._api_delete(client, 401)

    def test_delete_nonexistant_university_dept_membership(self, client, fake_auth):
        """Returns 404 when attempting to delete a nonexistant UniversityDeptMember record."""
        fake_auth.login(admin_uid)
        self._api_delete(client, 404)

    def test_delete_university_dept_membership(self, client, fake_auth):
        """Deletes a UniversityDeptMember record."""
        fake_auth.login(admin_uid)
        membership = self._api_add(client)
        university_dept_id = membership['universityDeptId']
        authorized_user_id = membership['authorizedUserId']
        response = self._api_delete(client)
        assert response.get('message') == (
            f'University dept membership deleted: university_dept_id={university_dept_id} authorized_user_id={authorized_user_id}'
        )


class TestUsers:
    """Users API."""

    def test_not_authenticated(self, client):
        """Returns 'unauthorized' response status if user is not authenticated."""
        response = client.post('/api/users')
        assert response.status_code == 401
        response = client.get('/api/users/departments')
        assert response.status_code == 401

    def test_unauthorized(self, client, fake_auth):
        """Returns 'unauthorized' response status if user is not admin."""
        fake_auth.login(coe_advisor_uid)
        response = client.post('/api/users')
        assert response.status_code == 401
        response = client.get('/api/users/departments')
        assert response.status_code == 401

    def test_unauthorized_scheduler(self, client, fake_auth):
        """Returns 'unauthorized' response status if user is a scheduler."""
        fake_auth.login(coe_scheduler_uid)
        response = client.post('/api/users')
        assert response.status_code == 401

    def test_authorized(self, client, fake_auth):
        """Returns a well-formed response including cached, uncached, and deleted users."""
        fake_auth.login(admin_uid)
        response = client.post(
            '/api/users',
            data=json.dumps({
                'deptCode': 'QCADV',
            }),
            content_type='application/json',
        )
        assert response.status_code == 200
        users = response.json['users']
        assert len(users) == 3

    def test_drop_in_advisors_for_dept(self, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_scheduler_uid)
            response = client.get('/api/users/drop_in_advisors/qcadv')
            assert response.status_code == 200
            assert len(response.json) == 1
            assert response.json[0]['dropInAdvisorStatus'][0] == {
                'status': 'on_duty_advisor',
                'deptCode': 'QCADV',
                'isEnabled': True,
            }

    def test_get_departments(self, client, fake_auth):
        """Get all departments."""
        fake_auth.login(admin_uid)
        response = client.get('/api/users/departments')
        assert response.status_code == 200


class TestGetAdminUsers:
    """Get Admin Users API."""

    @classmethod
    def _api_admin_users(
            cls,
            client,
            ignore_deleted,
            sort_by='lastName',
            sort_descending=False,
            expected_status_code=200,
    ):
        params = {
            'ignoreDeleted': ignore_deleted,
            'sortBy': sort_by,
            'sortDescending': sort_descending,
        }
        response = client.post(
            '/api/users/admins',
            data=json.dumps(params),
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return response.json

    def test_not_authenticated(self, client):
        """Returns 'unauthorized' response status if user is not authenticated."""
        self._api_admin_users(client, ignore_deleted=True, expected_status_code=401)

    def test_unauthorized(self, client, fake_auth):
        """Returns 'unauthorized' response status if user is not admin."""
        fake_auth.login(coe_advisor_uid)
        self._api_admin_users(client, ignore_deleted=True, expected_status_code=401)

    def test_get_admin_users(self, client, fake_auth):
        """Get all admin users."""
        fake_auth.login(admin_uid)
        api_json = self._api_admin_users(client, ignore_deleted=False, expected_status_code=200)
        users = api_json['users']
        user_count = len(users)
        assert user_count
        assert user_count == api_json['totalUserCount']
        assert next((u for u in users if u['deletedAt']), None) is not None

    def test_get_admin_users_ignore_deleted(self, client, fake_auth):
        """Get admin users, ignoring deleted users."""
        fake_auth.login(admin_uid)
        api_json = self._api_admin_users(client, ignore_deleted=True, expected_status_code=200)
        users = api_json['users']
        user_count = len(users)
        assert user_count
        assert user_count == api_json['totalUserCount']
        assert next((u for u in users if u['deletedAt']), None) is None


class TestUserSearch:

    @classmethod
    def _api_users_autocomplete(
            cls,
            client,
            snippet=None,
            expected_status_code=200,
    ):
        response = client.post(
            f'/api/users/autocomplete',
            data=json.dumps({'snippet': snippet}),
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return response.json

    def test_not_authenticated(self, client):
        """Deny anonymous user."""
        assert self._api_users_autocomplete(client, 'Jo', expected_status_code=401)

    def test_unauthorized(self, client, fake_auth):
        """Deny non-admin user."""
        assert self._api_users_autocomplete(client, 'Jo', expected_status_code=401)

    def test_user_search_by_uid(self, client, fake_auth):
        """Search users by UID."""
        fake_auth.login(admin_uid)
        assert len(self._api_users_autocomplete(client, '339')) == 2

    def test_search_for_deleted_user_by_uid(self, client, fake_auth):
        """Search for deleted user by UID."""
        fake_auth.login(admin_uid)
        users = self._api_users_autocomplete(client, '3333')
        assert len(users) == 1
        assert users[0]['uid'] == '33333'

    def test_search_for_deleted_user_by_name(self, client, fake_auth):
        """Search for deleted user by name."""
        fake_auth.login(admin_uid)
        calnet_users = list(calnet.get_calnet_users_for_uids(app, ['33333']).values())
        first_name = calnet_users[0]['firstName']
        last_name = calnet_users[0]['lastName']
        api_json = self._api_users_autocomplete(client, f'{first_name[:2]} {last_name[:3]}')
        assert len(api_json) == 1

    def test_space_separated_names_is_required(self, client, fake_auth):
        """When search users, names must be separated by spaces."""
        fake_auth.login(admin_uid)
        calnet_users = list(calnet.get_calnet_users_for_uids(app, ['1081940']).values())
        first_name = calnet_users[0]['firstName']
        last_name = calnet_users[0]['lastName']
        api_json = self._api_users_autocomplete(client, f'{first_name}{last_name}')
        assert len(api_json) == 0

    def test_user_search_by_last_name(self, client, fake_auth):
        """Search users by last name."""
        fake_auth.login(admin_uid)
        calnet_users = list(calnet.get_calnet_users_for_uids(app, ['1081940']).values())
        last_name = calnet_users[0]['lastName']
        api_json = self._api_users_autocomplete(client, f' {last_name[:3]}  ')
        assert len(api_json) == 1
        assert api_json[0]['uid'] == calnet_users[0]['uid']

    def test_user_search_by_name(self, client, fake_auth):
        """Search users by UID."""
        fake_auth.login(admin_uid)
        calnet_users = list(calnet.get_calnet_users_for_uids(app, ['1081940']).values())
        # Case-insensitive search
        first_name = calnet_users[0]['firstName'].lower()
        last_name = calnet_users[0]['lastName'].lower()
        api_json = self._api_users_autocomplete(client, f' {first_name[:2]} {last_name[:3]}  ')
        assert len(api_json) == 1
        assert api_json[0]['uid'] == calnet_users[0]['uid']


class TestDemoMode:

    def test_set_demo_mode_not_authenticated(self, app, client):
        """Require authentication."""
        with override_config(app, 'DEMO_MODE_AVAILABLE', True):
            assert client.post('/api/user/demo_mode').status_code == 401

    def test_demo_mode_unavailable(self, app, client, fake_auth):
        """Return 404 when dev_auth is not enabled."""
        with override_config(app, 'DEVELOPER_AUTH_ENABLED', True):
            # Enable dev_auth to confirm that it is ignored
            with override_config(app, 'DEMO_MODE_AVAILABLE', False):
                fake_auth.login(admin_uid)
                assert client.post('/api/user/demo_mode').status_code == 404

    def test_set_demo_mode(self, app, client, fake_auth):
        """Both admin and advisor can toggle demo mode."""
        with override_config(app, 'DEVELOPER_AUTH_ENABLED', False):
            # Disable dev_auth to confirm that it is ignored
            with override_config(app, 'DEMO_MODE_AVAILABLE', True):
                for uid in admin_uid, coe_advisor_uid:
                    fake_auth.login(uid)
                    for in_demo_mode in [True, False]:
                        response = client.post(
                            '/api/user/demo_mode',
                            data=json.dumps({'demoMode': in_demo_mode}),
                            content_type='application/json',
                        )
                        assert response.status_code == 200
                        assert response.json['inDemoMode'] is in_demo_mode
                        user = AuthorizedUser.find_by_uid(uid)
                        assert user.in_demo_mode is in_demo_mode


class TestDownloadUsers:

    def test_not_authenticated(self, client):
        """Returns 'unauthorized' response status if user is not authenticated."""
        response = client.get('/api/users/csv')
        assert response.status_code == 401

    def test_unauthorized(self, client, fake_auth):
        """Returns 'unauthorized' response status if user is not admin."""
        fake_auth.login(coe_advisor_uid)
        response = client.get('/api/users/csv')
        assert response.status_code == 401

    def test_unauthorized_scheduler(self, client, fake_auth):
        """Returns 'unauthorized' response status if user is a scheduler."""
        fake_auth.login(coe_scheduler_uid)
        response = client.get('/api/users/csv')
        assert response.status_code == 401

    def test_authorized(self, client, fake_auth):
        """Returns a well-formed response."""
        fake_auth.login(admin_uid)
        response = client.get('/api/users/csv')
        assert response.status_code == 200
        assert 'csv' in response.content_type
        assert 'COENG' in str(response.data)


class TestToggleDropInAppointmentStatus:

    def test_not_authenticated(self, app, client):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/off_duty_waitlist')
            assert response.status_code == 401

    def test_denies_non_drop_in_advisor(self, app, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_advisor_uid)
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/off_duty_waitlist')
            assert response.status_code == 401

    def test_denies_scheduler_in_other_department(self, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['COENG', 'QCADV']):
            fake_auth.login(coe_scheduler_uid)
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/off_duty_waitlist')
            assert response.status_code == 403

    def test_denies_advisor_toggling_another_advisor(self, app, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_drop_in_advisor_uid)
            response = client.post(f'/api/user/{asc_advisor_uid}/drop_in_status/UWASC/off_duty_waitlist')
            assert response.status_code == 403

    def test_handles_drop_in_status_not_found(self, app, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_drop_in_advisor_uid)
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/COENG/off_duty_waitlist')
            assert response.status_code == 404

    def test_advisor_can_toggle_own_status(self, app, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_drop_in_advisor_uid)
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/off_duty_waitlist')
            assert response.status_code == 200
            response = client.get('/api/users/drop_in_advisors/QCADV')
            assert len(response.json) == 1
            assert {
                'deptCode': 'QCADV',
                'isEnabled': True,
                'status': 'off_duty_waitlist',
            } in response.json[0]['dropInAdvisorStatus']
            response = client.get('/api/profile/my')
            assert {
                'deptCode': 'QCADV',
                'isEnabled': True,
                'status': 'off_duty_waitlist',
            } in response.json['dropInAdvisorStatus']
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/on_duty_advisor')
            assert response.status_code == 200
            response = client.get('/api/profile/my')
            assert {
                'deptCode': 'QCADV',
                'isEnabled': True,
                'status': 'on_duty_advisor',
            } in response.json['dropInAdvisorStatus']

    def test_scheduler_can_toggle_advisor_status(self, app, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_scheduler_uid)

            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/off_duty_waitlist')
            assert response.status_code == 200

            response = client.get('/api/users/drop_in_advisors/QCADV')
            assert len(response.json) == 1
            assert response.json[0]['status'] == 'off_duty_waitlist'
            assert {
                'deptCode': 'QCADV',
                'isEnabled': True,
                'status': 'off_duty_waitlist',
            } in response.json[0]['dropInAdvisorStatus']

            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/on_duty_advisor')
            assert response.status_code == 200

            response = client.get('/api/users/drop_in_advisors/QCADV')
            assert len(response.json) == 1
            assert response.json[0]['status'] == 'on_duty_advisor'
            assert {
                'deptCode': 'QCADV',
                'isEnabled': True,
                'status': 'on_duty_advisor',
            } in response.json[0]['dropInAdvisorStatus']

    def test_advisor_can_hide_their_own_waitlist(self, app, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_drop_in_advisor_uid)
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/off_duty_no_waitlist')
            assert response.status_code == 200
            response = client.get('/api/users/drop_in_advisors/QCADV')
            assert len(response.json) == 1
            assert {'deptCode': 'QCADV', 'isEnabled': True, 'status': 'off_duty_no_waitlist'} in response.json[0]['dropInAdvisorStatus']
            response = client.get('/api/profile/my')
            assert {'deptCode': 'QCADV', 'isEnabled': True, 'status': 'off_duty_no_waitlist'} in response.json['dropInAdvisorStatus']
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/on_duty_advisor')
            assert response.status_code == 200
            response = client.get('/api/profile/my')
            assert {'deptCode': 'QCADV', 'isEnabled': True, 'status': 'on_duty_advisor'} in response.json['dropInAdvisorStatus']

    def test_scheduler_cannot_hide_advisor_waitlist(self, app, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_scheduler_uid)
            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/off_duty_no_waitlist')
            assert response.status_code == 403

    def test_advisor_assumes_and_relinquishes_supervisor_status(self, app, client, fake_auth):
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(l_s_college_drop_in_advisor_uid)

            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/on_duty_supervisor')
            assert response.status_code == 200
            response = client.get('/api/users/drop_in_advisors/QCADV')
            assert len(response.json) == 1
            assert response.json[0]['status'] == 'on_duty_supervisor'
            assert {'deptCode': 'QCADV', 'isEnabled': True, 'status': 'on_duty_supervisor'} in response.json[0]['dropInAdvisorStatus']

            response = client.post(f'/api/user/{l_s_college_drop_in_advisor_uid}/drop_in_status/QCADV/on_duty_advisor')
            assert response.status_code == 200
            response = client.get('/api/users/drop_in_advisors/QCADV')
            assert len(response.json) == 1
            assert response.json[0]['status'] == 'on_duty_advisor'
            assert {'deptCode': 'QCADV', 'isEnabled': True, 'status': 'on_duty_advisor'} in response.json[0]['dropInAdvisorStatus']


class TestUserUpdate:

    @classmethod
    def _profile_object(
            cls,
            uid,
            authorized_user_id=None,
            is_admin=False,
            is_blocked=False,
            can_access_canvas_data=True,
    ):
        return {
            'uid': uid,
            'id': authorized_user_id,
            'isAdmin': is_admin,
            'isBlocked': is_blocked,
            'canAccessCanvasData': can_access_canvas_data,
        }

    @classmethod
    def _api_create_or_update(
            cls,
            client,
            profile,
            expected_status_code=200,
            roles_per_dept_code=(),
            delete_action=None,
    ):
        response = client.post(
            f'/api/users/create_or_update',
            data=json.dumps({
                'profile': profile,
                'rolesPerDeptCode': roles_per_dept_code,
                'deleteAction': delete_action,
            }),
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return response.json

    def test_not_authenticated(self, client):
        """Authentication required."""
        self._api_create_or_update(
            client,
            profile=self._profile_object(uid='2040'),
            expected_status_code=401,
        )

    def test_unauthorized(self, client, fake_auth):
        """Admin required."""
        fake_auth.login(coe_advisor_uid)
        self._api_create_or_update(
            client,
            profile=self._profile_object(uid='2040'),
            expected_status_code=401,
        )

    def test_unrecognized_uid(self, client, fake_auth):
        """Unrecognized UID."""
        fake_auth.login(admin_uid)
        self._api_create_or_update(
            client,
            profile=self._profile_object(uid='9999999999'),
            expected_status_code=400,
        )

    def test_error_when_add_existing_uid(self, client, fake_auth):
        """Raises error if UID exists."""
        fake_auth.login(admin_uid)
        self._api_create_or_update(
            client,
            profile=self._profile_object(uid=deleted_user_uid),
            expected_status_code=400,
        )

    def test_create_drop_in_advisor(self, client, fake_auth):
        """Admin creates new Drop-in Advisor."""
        fake_auth.login(admin_uid)
        uid = '900000001'
        insert_in_json_cache(
            f'calnet_user_for_uid_{uid}',
            {
                'uid': uid,
                'csid': '100000009',
            },
        )
        user = self._api_create_or_update(
            client,
            profile=self._profile_object(uid=uid),
            roles_per_dept_code=[
                {
                    'code': 'QCADV',
                    'role': 'dropInAdvisor',
                    'automateMembership': True,
                },
                {
                    'code': 'QCADVMAJ',
                    'role': 'scheduler',
                    'automateMembership': False,
                },
            ],
        )
        uid = user['uid']
        assert user['id']
        assert uid
        assert user['isAdmin'] is False
        assert user['isBlocked'] is False
        assert user['canAccessCanvasData'] is True
        assert len(user['departments']) == 2

        assert len(user['dropInAdvisorStatus']) == 1
        assert user['dropInAdvisorStatus'][0]['deptCode'] == 'QCADV'
        assert user['dropInAdvisorStatus'][0]['isEnabled'] is True

        qcadv = next(d for d in user['departments'] if d['code'] == 'QCADV')
        assert qcadv['isAdvisor'] is True
        assert qcadv['isScheduler'] is False
        assert qcadv['automateMembership'] is True

        qcadvmaj = next(d for d in user['departments'] if d['code'] == 'QCADVMAJ')
        assert qcadvmaj['isAdvisor'] is False
        assert qcadvmaj['isScheduler'] is True
        assert qcadvmaj['automateMembership'] is False

        # Clean up
        AuthorizedUser.delete_and_block(uid)

    def test_update_advisor(self, client, fake_auth):
        """Add Advisor to another department, assign Scheduler role."""
        fake_auth.login(admin_uid)
        # First, create advisor
        uid = '9000000002'
        insert_in_json_cache(
            f'calnet_user_for_uid_{uid}',
            {
                'uid': uid,
                'csid': '200000009',
            },
        )
        user = self._api_create_or_update(
            client,
            profile=self._profile_object(uid=uid),
            roles_per_dept_code=[
                {
                    'code': 'QCADV',
                    'role': 'dropInAdvisor',
                    'automateMembership': True,
                },
            ],
        )
        user_id = user['id']
        assert user_id
        assert user['uid'] == uid

        departments = user['departments']
        assert len(departments) == 1
        assert departments[0]['code'] == 'QCADV'
        assert departments[0]['isAdvisor'] is True
        assert departments[0]['automateMembership'] is True

        drop_in_statuses = user['dropInAdvisorStatus']
        assert len(drop_in_statuses) == 1
        assert drop_in_statuses[0]['deptCode'] == 'QCADV'
        assert drop_in_statuses[0]['isEnabled'] is True

        # Next, remove advisor from 'QCADV' and add him to 'QCADVMAJ', as "Scheduler".
        authorized_user_id = AuthorizedUser.get_id_per_uid(uid)
        self._api_create_or_update(
            client,
            profile=self._profile_object(
                uid=uid,
                authorized_user_id=authorized_user_id,
            ),
            roles_per_dept_code=[
                {
                    'code': 'QCADVMAJ',
                    'role': 'scheduler',
                    'automateMembership': False,
                },
            ],
        )
        std_commit(allow_test_environment=True)

        user = AuthorizedUser.find_by_uid(uid)
        assert len(user.drop_in_departments) == 1
        assert user.drop_in_departments[0].deleted_at is not None
        assert len(user.department_memberships) == 1
        assert user.department_memberships[0].university_dept.dept_code == 'QCADVMAJ'
        assert user.department_memberships[0].automate_membership is False

    def test_update_deleted_user(self, client, fake_auth):
        """Update and then un-delete user."""
        fake_auth.login(admin_uid)
        # First, create advisor
        uid = '9000000003'
        insert_in_json_cache(
            f'calnet_user_for_uid_{uid}',
            {
                'uid': uid,
                'csid': '300000009',
            },
        )
        profile = self._profile_object(uid=uid, is_admin=True)
        user = self._api_create_or_update(client, profile=profile, roles_per_dept_code=[])
        profile['id'] = user['id']

        # Next, delete the user.
        self._api_create_or_update(client, profile=profile, delete_action=True)
        std_commit(allow_test_environment=True)

        user = AuthorizedUser.find_by_uid(uid, ignore_deleted=False)
        assert user.deleted_at

        # Finally, un-delete the user.
        self._api_create_or_update(client, profile=profile, delete_action=False)
        std_commit(allow_test_environment=True)

        user = AuthorizedUser.find_by_uid(uid, ignore_deleted=False)
        assert not user.deleted_at


class TestToggleDropInAdvising:

    @classmethod
    def _api_toggle_drop_in_advising(
            cls,
            client,
            dept_code,
            action,
            expected_status_code=200,
    ):
        response = client.post(
            f'/api/user/drop_in_advising/{dept_code}/{action}',
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return response.json

    def test_not_authenticated(self, client):
        """Authentication required."""
        self._api_toggle_drop_in_advising(
            client,
            dept_code='COENG',
            action='enable',
            expected_status_code=401,
        )
        self._api_toggle_drop_in_advising(
            client,
            dept_code='COENG',
            action='disable',
            expected_status_code=401,
        )

    def test_non_drop_in_advisor(self, client, fake_auth):
        """Prevents advisor from toggling for a department they aren't a drop-in advisor for."""
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', ['QCADV']):
            fake_auth.login(coe_advisor_uid)
            self._api_toggle_drop_in_advising(
                client,
                dept_code='QCADV',
                action='enable',
                expected_status_code=401,
            )
            self._api_toggle_drop_in_advising(
                client,
                dept_code='QCADV',
                action='disable',
                expected_status_code=401,
            )

    def test_non_drop_in_dept(self, client, fake_auth):
        """Prevents advisor from toggling when dept is not configured for drop-in advising."""
        fake_auth.login(coe_advisor_uid)
        self._api_toggle_drop_in_advising(
            client,
            dept_code='COENG',
            action='disable',
            expected_status_code=401,
        )
        self._api_toggle_drop_in_advising(
            client,
            dept_code='COENG',
            action='enable',
            expected_status_code=401,
        )

    def test_toggle_drop_in_advising(self, client, fake_auth):
        """Allows advisor to disable and enable their drop-in advising status."""
        dept_code = 'COENG'
        with override_config(app, 'DEPARTMENTS_SUPPORTING_DROP_INS', [dept_code]):
            fake_auth.login(coe_advisor_uid)
            user = AuthorizedUser.find_by_uid(coe_advisor_uid)
            assert user.drop_in_departments[0].deleted_at is None

            response = self._api_toggle_drop_in_advising(
                client,
                dept_code='COENG',
                action='disable',
            )
            assert response == {'deptCode': dept_code, 'isEnabled': False, 'status': 'on_duty_advisor'}
            user = AuthorizedUser.find_by_uid(coe_advisor_uid)
            assert user.drop_in_departments[0].deleted_at is not None

            response = self._api_toggle_drop_in_advising(
                client,
                dept_code=dept_code,
                action='enable',
            )
            assert response == {'deptCode': dept_code, 'isEnabled': True, 'status': 'off_duty_no_waitlist'}
            user = AuthorizedUser.find_by_uid(coe_advisor_uid)
            assert user.drop_in_departments[0].deleted_at is None
