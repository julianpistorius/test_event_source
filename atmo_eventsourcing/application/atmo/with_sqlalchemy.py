from eventsourcing.application.with_sqlalchemy import EventSourcingWithSQLAlchemy

from atmo_eventsourcing.application.atmo.base import AtmoEventSourcingApplication


class AtmoEventSourcingApplicationWithSQLAlchemy(EventSourcingWithSQLAlchemy, AtmoEventSourcingApplication):
    pass
