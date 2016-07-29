from allocation_source.model.allocation_source import register_new_example, AllocationSource, AllocationSourceRepository
from eventsourcing.application.base import EventSourcingApplication
from eventsourcing.application.with_pythonobjects import EventSourcingWithPythonObjects
from eventsourcing.application.with_sqlalchemy import EventSourcingWithSQLAlchemy
from eventsourcing.infrastructure.event_sourced_repo import EventSourcedRepository
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.base import StoredEventRepository
from eventsourcingtests.test_stored_events import AbstractTestCase


class AllocationSourceRepo(EventSourcedRepository, AllocationSourceRepository):
    """
    Event sourced repository for the AllocationSource domain model entity.
    """
    domain_class = AllocationSource


class AllocationSourceApplication(EventSourcingApplication):
    def __init__(self, **kwargs):
        super(AllocationSourceApplication, self).__init__(**kwargs)
        self.example_repo = AllocationSourceRepo(self.event_store)

    def register_new_example(self, a, b):
        return register_new_example(a=a, b=b)  # This is weird.


class AllocationSourceApplicationWithSQLAlchemy(EventSourcingWithSQLAlchemy, AllocationSourceApplication):
    pass


class AllocationSourceApplicationWithPythonObjects(EventSourcingWithPythonObjects, AllocationSourceApplication):
    pass


class AllocationSourceApplicationTestCase(AbstractTestCase):
    def setUp(self):
        super(AllocationSourceApplicationTestCase, self).setUp()
        self.app = self.create_app()

    def create_app(self):
        raise AllocationSourceApplication()

    def tearDown(self):
        self.app.close()
        super(AllocationSourceApplicationTestCase, self).tearDown()

    def test(self):
        assert isinstance(self.app, AllocationSourceApplication)  # For PyCharm...

        # Check there's a stored event repo.
        self.assertIsInstance(self.app.stored_event_repo, StoredEventRepository)

        # Check there's an event store.
        self.assertIsInstance(self.app.event_store, EventStore)
        self.assertEqual(self.app.event_store.stored_event_repo, self.app.stored_event_repo)

        # Check there's a persistence subscriber.
        self.assertIsInstance(self.app.persistence_subscriber, PersistenceSubscriber)
        self.assertEqual(self.app.persistence_subscriber.event_store, self.app.event_store)

        # Check there's an example repository.
        self.assertIsInstance(self.app.example_repo, AllocationSourceRepo)

        # Register a new example.
        example1 = self.app.register_new_example(a=10, b=20)
        self.assertIsInstance(example1, AllocationSource)

        # Check the example is available in the repo.
        entity1 = self.app.example_repo[example1.id]
        self.assertEqual(10, entity1.a)
        self.assertEqual(20, entity1.b)
        self.assertEqual(example1, entity1)

        # Change attribute values.
        entity1.a = 100

        # Check the new value is available in the repo.
        entity1 = self.app.example_repo[example1.id]
        self.assertEqual(100, entity1.a)


class TestAllocationSourceApplicationWithSQLAlchemy(AllocationSourceApplicationTestCase):
    def create_app(self):
        return AllocationSourceApplicationWithSQLAlchemy(db_uri='sqlite:///:memory:')


class TestAllocationSourceApplicationWithPythonObjects(AllocationSourceApplicationTestCase):
    def create_app(self):
        return AllocationSourceApplicationWithPythonObjects()
