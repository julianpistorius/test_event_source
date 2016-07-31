from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.base import StoredEventRepository
from eventsourcingtests.test_stored_events import AbstractTestCase

from atmo_eventsourcing.application.atmo.base import AtmoEventSourcingApplication
from atmo_eventsourcing.application.atmo.with_pythonobjects import AtmoEventSourcingApplicationWithPythonObjects
from atmo_eventsourcing.application.atmo.with_sqlalchemy import AtmoEventSourcingApplicationWithSQLAlchemy
from atmo_eventsourcing.domain.model.allocation_source import AllocationSource
from atmo_eventsourcing.infrastructure.event_sourced_repos.allocation_source_repo import AllocationSourceRepo


class AtmoEventSourcingApplicationTestCase(AbstractTestCase):
    def setUp(self):
        super(AtmoEventSourcingApplicationTestCase, self).setUp()
        self.app = self.create_app()

    def create_app(self):
        raise AtmoEventSourcingApplication()

    def tearDown(self):
        self.app.close()
        super(AtmoEventSourcingApplicationTestCase, self).tearDown()

    def test_allocation_source(self):
        assert isinstance(self.app, AtmoEventSourcingApplication)  # For PyCharm...

        # Check there's a stored event repo.
        self.assertIsInstance(self.app.stored_event_repo, StoredEventRepository)

        # Check there's an event store.
        self.assertIsInstance(self.app.event_store, EventStore)
        self.assertEqual(self.app.event_store.stored_event_repo, self.app.stored_event_repo)

        # Check there's a persistence subscriber.
        self.assertIsInstance(self.app.persistence_subscriber, PersistenceSubscriber)
        self.assertEqual(self.app.persistence_subscriber.event_store, self.app.event_store)

        # Check there's an Allocation Source repository.
        self.assertIsInstance(self.app.allocation_source_repo, AllocationSourceRepo)

        # Register a new Allocation Source.
        allocation_source1 = self.app.register_new_allocation_source(a=10, b=20)
        self.assertIsInstance(allocation_source1, AllocationSource)

        # Check the Allocation Source is available in the repo.
        entity1 = self.app.allocation_source_repo[allocation_source1.id]
        self.assertEqual(10, entity1.a)
        self.assertEqual(20, entity1.b)
        self.assertEqual(allocation_source1, entity1)

        # Change attribute values.
        entity1.a = 100

        # Check the new value is available in the repo.
        entity1 = self.app.allocation_source_repo[allocation_source1.id]
        self.assertEqual(100, entity1.a)


class TestAtmoEventSourcingApplicationWithSQLAlchemy(AtmoEventSourcingApplicationTestCase):
    def create_app(self):
        return AtmoEventSourcingApplicationWithSQLAlchemy(db_uri='sqlite:///:memory:')


class TestAtmoEventSourcingApplicationWithPythonObjects(AtmoEventSourcingApplicationTestCase):
    def create_app(self):
        return AtmoEventSourcingApplicationWithPythonObjects()
