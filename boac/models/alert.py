import datetime

from boac import db, std_commit
from boac.models import authorized_user
from boac.models.base import Base
from boac.models.db_relationships import AlertView
from sqlalchemy import text


class Alert(Base):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, nullable=False, primary_key=True)
    sid = db.Column(db.String(80), db.ForeignKey('students.sid'), nullable=False)
    alert_type = db.Column(db.String(80), nullable=False)
    key = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    views = db.relationship(
        'AlertView',
        back_populates='alert',
        lazy=True,
    )

    __table_args__ = (db.UniqueConstraint(
        'sid',
        'alert_type',
        'key',
        name='alerts_sid_alert_type_key_unique_constraint',
    ),)

    @classmethod
    def create(cls, sid, alert_type, key=None, message=None, active=True):
        # Alerts must contain a key, unique per SID and alert type, which will allow them to be located
        # and modified on updates to the data that originally generated the alert. The key defaults
        # to a string representation of today's date, but will more often (depending on the alert type)
        # contain a reference to a related resource, such as a course or assignment id.
        if key is None:
            key = datetime.datetime.now().strftime('%Y-%m-%d')
        else:
            # If we get a blank string as key, deliver a stern warning to the code that submitted it.
            key = key.strip()
            if not key:
                raise ValueError('Blank string submitted for alert key')
        alert = cls(sid, alert_type, key, message, active)
        db.session.add(alert)
        std_commit()
        return alert

    def __init__(self, sid, alert_type, key, message=None, active=True):
        self.sid = sid
        self.alert_type = alert_type
        self.key = key
        self.message = message
        self.active = active

    def __repr__(self):
        return f"""<Alert {self.id},
                    sid={self.sid},
                    alert_type={self.alert_type},
                    key={self.key},
                    message={self.message},
                    active={self.active},
                    updated={self.updated_at},
                    created={self.created_at}>
                """

    def add_viewer(self, uid):
        viewer = authorized_user.AuthorizedUser.find_by_uid(uid)
        if viewer:
            db.session.add(AlertView(alert_id=self.id, viewer_id=viewer.id))
            std_commit()

    @classmethod
    def current_alerts(cls, viewer_id):
        query = text("""
            SELECT * FROM students s JOIN (
                SELECT alerts.sid, count(*) as alert_count
                FROM alert_views JOIN alerts
                    ON alert_views.alert_id = alerts.id
                WHERE alert_views.viewer_id = :viewer_id
                    AND alerts.active = true
                    AND alert_views.dismissed_at IS NULL
                GROUP BY alerts.sid
            ) alert_counts
            ON s.sid = alert_counts.sid
            ORDER BY s.last_name
        """)
        results = db.session.execute(query, {'viewer_id': viewer_id})

        def result_to_dict(result):
            return {key: result[key] for key in ['sid', 'uid', 'first_name', 'last_name', 'alert_count']}
        return [result_to_dict(result) for result in results]

    @classmethod
    def current_alerts_for_sid(cls, viewer_id, sid):
        query = AlertView.query.filter_by(viewer_id=viewer_id, dismissed_at=None).join(cls).filter_by(sid=sid, active=True)
        results = query.all()
        return [result.alert.to_api_json() for result in results]

    def deactivate(self):
        self.active = False
        std_commit()

    def to_api_json(self):
        return {
            'id': self.id,
            'alertType': self.alert_type,
            'key': self.key,
            'message': self.message,
        }
