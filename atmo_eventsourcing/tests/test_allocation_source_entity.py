import unittest

from atmo_eventsourcing.domain.model.allocation_source import register_new_allocation_source, AllocationSource
from atmo_eventsourcing.infrastructure.event_sourced_repos.allocation_source_repo import AllocationSourceRepo
from eventsourcing.domain.model.entity import EntityIDConsistencyError, \
    EntityVersionConsistencyError
from eventsourcing.domain.model.events import DomainEvent, assert_event_handlers_empty
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.python_objects_stored_events import PythonObjectsStoredEventRepository


class TestAllocationSourceEntity(unittest.TestCase):
    def setUp(self):
        # Setup the persistence subscriber.
        self.event_store = EventStore(PythonObjectsStoredEventRepository())
        self.persistence_subscriber = PersistenceSubscriber(event_store=self.event_store)

    def tearDown(self):
        self.persistence_subscriber.close()
        assert_event_handlers_empty()

    def test_entity_lifecycle(self):
        # Check the factory creates an instance.
        allocation_source1 = register_new_allocation_source(a=1, b=2)
        self.assertIsInstance(allocation_source1, AllocationSource)

        # Check the properties of the AllocationSource class.
        self.assertEqual(1, allocation_source1.a)
        self.assertEqual(2, allocation_source1.b)

        # Check the properties of the EventSourcedEntity class.
        self.assertTrue(allocation_source1.id)
        self.assertEqual(1, allocation_source1.version)
        self.assertTrue(allocation_source1.created_on)

        # Check a second instance with the same values is not "equal" to the first.
        allocation_source2 = register_new_allocation_source(a=1, b=2)
        self.assertNotEqual(allocation_source1, allocation_source2)

        # Setup the repo.
        repo = AllocationSourceRepo(self.event_store)

        # Check the allocation source entities can be retrieved from the allocation source repository.
        entity1 = repo[allocation_source1.id]
        self.assertIsInstance(entity1, AllocationSource)
        self.assertEqual(1, entity1.a)
        self.assertEqual(2, entity1.b)

        entity2 = repo[allocation_source2.id]
        self.assertIsInstance(entity2, AllocationSource)
        self.assertEqual(1, entity2.a)
        self.assertEqual(2, entity2.b)

        # Check the entity can be updated.
        entity1.a = 100
        self.assertEqual(100, repo[entity1.id].a)
        entity1.b = -200
        self.assertEqual(-200, repo[entity1.id].b)

        self.assertEqual(0, entity1.count_heartbeats())
        entity1.beat_heart()
        entity1.beat_heart()
        entity1.beat_heart()
        self.assertEqual(3, entity1.count_heartbeats())
        self.assertEqual(3, repo[entity1.id].count_heartbeats())

        # Check the entity can be discarded.
        entity1.discard()

        # Check the repo now raises a KeyError.
        self.assertRaises(KeyError, repo.__getitem__, entity1.id)

        # Check the entity can't be discarded twice.
        self.assertRaises(AssertionError, entity1.discard)

        # Should fail to validate event with wrong entity ID.
        self.assertRaises(EntityIDConsistencyError,
                          entity2._validate_originator,
                          DomainEvent(entity_id=entity2.id + 'wrong', entity_version=0)
                          )
        # Should fail to validate event with wrong entity version.
        self.assertRaises(EntityVersionConsistencyError,
                          entity2._validate_originator,
                          DomainEvent(entity_id=entity2.id, entity_version=0)
                          )
        # Should validate event with correct entity ID and version.
        entity2._validate_originator(
            DomainEvent(entity_id=entity2.id, entity_version=entity2.version)
        )

    def test_not_implemented_error(self):
        # Define an event class.
        class UnsupportedEvent(DomainEvent):
            pass

        # Check we get an error when attempting to mutate on the event.
        self.assertRaises(NotImplementedError, AllocationSource.mutate, AllocationSource, UnsupportedEvent('1', '0'))
