import unittest

from atmo_eventsourcing.domain.model.instance import register_new_instance, Instance
from atmo_eventsourcing.infrastructure.event_sourced_repos.instance_repo import InstanceRepo
from eventsourcing.domain.model.entity import EntityIDConsistencyError, \
    EntityVersionConsistencyError
from eventsourcing.domain.model.events import DomainEvent, assert_event_handlers_empty
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.python_objects_stored_events import PythonObjectsStoredEventRepository


class TestInstanceEntity(unittest.TestCase):
    def setUp(self):
        # Setup the persistence subscriber.
        self.event_store = EventStore(PythonObjectsStoredEventRepository())
        self.persistence_subscriber = PersistenceSubscriber(event_store=self.event_store)

    def tearDown(self):
        self.persistence_subscriber.close()
        assert_event_handlers_empty()

    def test_entity_lifecycle(self):
        # Check the factory creates an instance.
        instance1 = register_new_instance(atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base')
        self.assertIsInstance(instance1, Instance)

        # Check the properties of the Instance class.
        self.assertEqual(27216, instance1.atmo_id)
        self.assertEqual('Ubuntu 14.04.2 XFCE Base', instance1.name)

        # Check the properties of the EventSourcedEntity class.
        # TODO: Check that entity_id is a UUID hex of the atmo_id
        self.assertTrue(instance1.id)
        self.assertEqual(1, instance1.version)
        self.assertTrue(instance1.created_on)

        # Check a second instance with the same values is not "equal" to the first.
        # TODO: Actually, maybe it will be, and more importantly, _should_ be.
        instance2 = register_new_instance(atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base')
        self.assertNotEqual(instance1, instance2)

        # Setup the repo.
        repo = InstanceRepo(self.event_store)

        # Check the allocation source entities can be retrieved from the allocation source repository.
        entity1 = repo[instance1.id]
        self.assertIsInstance(entity1, Instance)
        self.assertEqual(27216, entity1.atmo_id)
        self.assertEqual('Ubuntu 14.04.2 XFCE Base', entity1.name)

        entity2 = repo[instance2.id]
        self.assertIsInstance(entity2, Instance)
        self.assertEqual(27216, entity2.atmo_id)
        self.assertEqual('Ubuntu 14.04.2 XFCE Base', entity2.name)

        # Check the entity name can be updated, but not the atmo_id
        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            entity1.atmo_id = 27217
        self.assertEqual(27216, repo[entity1.id].atmo_id)

        entity1.name = 'Ubuntu 16.04.1 XFCE Base'
        self.assertEqual('Ubuntu 16.04.1 XFCE Base', repo[entity1.id].name)

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
        self.assertRaises(NotImplementedError, Instance.mutate, Instance, UnsupportedEvent('1', '0'))
