import unittest
from uuid import uuid1

from eventsourcing.domain.model.events import assert_event_handlers_empty
from eventsourcing.domain.model.snapshot import take_snapshot, Snapshot
from eventsourcing.infrastructure.event_player import EventPlayer, entity_from_snapshot
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.python_objects_stored_events import PythonObjectsStoredEventRepository

from atmo_eventsourcing.domain.model.instance import Instance, register_new_instance


class TestInstanceEventPlayer(unittest.TestCase):
    def setUp(self):
        assert_event_handlers_empty()
        self.ps = None

    def tearDown(self):
        if self.ps is not None:
            self.ps.close()
        assert_event_handlers_empty()

    def test_get_entity(self):
        # Setup an event store, using Python objects.
        event_store = EventStore(stored_event_repo=PythonObjectsStoredEventRepository())

        # Store Instance events.
        event1 = Instance.Created(entity_id='entity1', atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base')
        event_store.append(event1)
        event2 = Instance.Created(entity_id='entity2', atmo_id=27217, name='Ubuntu 15.04.2 XFCE Base')
        event_store.append(event2)
        event3 = Instance.Created(entity_id='entity3', atmo_id=27218, name='Ubuntu 16.04.2 XFCE Base')
        event_store.append(event3)
        event4 = Instance.Discarded(entity_id='entity3', entity_version=1)
        event_store.append(event4)

        # Check the event sourced entities are correct.
        # - just use a trivial mutate that always instantiates the 'Instance'.
        event_player = EventPlayer(event_store=event_store, id_prefix='Instance',
                                   mutate_func=Instance.mutate)

        # The the reconstituted entity has correct attribute values.
        self.assertEqual('entity1', event_player.replay_events('entity1').id)
        self.assertEqual(27216, event_player.replay_events('entity1').atmo_id)
        self.assertEqual(27217, event_player.replay_events('entity2').atmo_id)
        self.assertEqual(None, event_player.replay_events('entity3'))

        # Check entity3 raises KeyError.
        self.assertEqual(event_player.replay_events('entity3'), None)

        # Check it works for "short" entities (should be faster, but the main thing is that it still works).
        # - just use a trivial mutate that always instantiates the 'Instance'.
        # TODO: Fix this. This is broken.
        # It does not throw an error, even though `a` is not an attribute off `Instance`.
        # See: eventsourcing/domain/model/entity.py:138
        event5 = Instance.AttributeChanged(entity_id='entity1', entity_version=1, name='a', value=10)
        event_store.append(event5)

        event_player = EventPlayer(event_store=event_store, id_prefix='Instance',
                                   mutate_func=Instance.mutate)

        self.assertEqual(10, event_player.replay_events('entity1').a)

        event_player = EventPlayer(
            event_store=event_store,
            id_prefix='Instance',
            mutate_func=Instance.mutate,
            is_short=True,
        )
        self.assertEqual(10, event_player.replay_events('entity1').a)

    def test_snapshots(self):
        stored_event_repo = PythonObjectsStoredEventRepository()
        event_store = EventStore(stored_event_repo)
        self.ps = PersistenceSubscriber(event_store)
        event_player = EventPlayer(event_store=event_store, id_prefix='Instance',
                                   mutate_func=Instance.mutate)

        # Create a new entity.
        registered_instance = register_new_instance(atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base')

        # Take a snapshot.
        snapshot = take_snapshot(registered_instance, uuid1().hex)

        # Replay from this snapshot.
        after = snapshot.at_event_id
        initial_state = entity_from_snapshot(snapshot)
        retrieved_instance = event_player.replay_events(registered_instance.id,
                                                        initial_state=initial_state, after=after)

        # Check the attributes are correct.
        self.assertEqual(retrieved_instance.atmo_id, 27216)
        self.assertEqual(retrieved_instance.name, 'Ubuntu 14.04.2 XFCE Base')

        # Remember the time now.
        timecheck1 = uuid1().hex

        # Try changing a read-only attribute value. Should fail.
        with self.assertRaises(AttributeError):
            retrieved_instance.atmo_id = 27217
        retrieved_instance.name = 'Ubuntu 15.04.2 XFCE Base'

        # Check the initial state doesn't move.
        self.assertEqual(initial_state.atmo_id, 27216)
        self.assertEqual(initial_state.name, 'Ubuntu 14.04.2 XFCE Base')

        # Remember the time now.
        timecheck2 = uuid1().hex

        # Change attribute value.
        retrieved_instance.name = 'Ubuntu 16.04.2 XFCE Base'

        # Remember the time now.
        timecheck3 = uuid1().hex

        # Check the event sourced entities are correct.
        assert initial_state.name == 'Ubuntu 14.04.2 XFCE Base'
        retrieved_instance = event_player.replay_events(registered_instance.id)
        self.assertEqual(retrieved_instance.name, 'Ubuntu 16.04.2 XFCE Base')

        # Take another snapshot.
        snapshot2 = take_snapshot(retrieved_instance, uuid1().hex)

        # Check we can replay from this snapshot.
        initial_state2 = entity_from_snapshot(snapshot2)
        after2 = snapshot2.domain_event_id
        retrieved_instance = event_player.replay_events(registered_instance.id,
                                                        initial_state=initial_state2,
                                                        after=after2)
        # Check the attributes are correct.
        self.assertEqual(retrieved_instance.name, 'Ubuntu 16.04.2 XFCE Base')

        # Check we can get historical state at timecheck1.
        retrieved_instance = event_player.replay_events(registered_instance.id, until=timecheck1)
        self.assertEqual(retrieved_instance.name, 'Ubuntu 14.04.2 XFCE Base')

        # Check we can get historical state at timecheck2.
        retrieved_instance = event_player.replay_events(registered_instance.id, until=timecheck2)
        self.assertEqual(retrieved_instance.name, 'Ubuntu 15.04.2 XFCE Base')

        # Check we can get historical state at timecheck3.
        retrieved_instance = event_player.replay_events(registered_instance.id, until=timecheck3)
        self.assertEqual(retrieved_instance.name, 'Ubuntu 16.04.2 XFCE Base')

        # Similarly, check we can get historical state using a snapshot
        retrieved_instance = event_player.replay_events(registered_instance.id,
                                                        initial_state=initial_state, after=after,
                                                        until=timecheck2)
        self.assertEqual(retrieved_instance.name, 'Ubuntu 15.04.2 XFCE Base')

    def test_take_snapshot(self):
        # Check the EventPlayer's take_snapshot() method.
        stored_event_repo = PythonObjectsStoredEventRepository()
        event_store = EventStore(stored_event_repo)
        self.ps = PersistenceSubscriber(event_store)
        event_player = EventPlayer(event_store=event_store, id_prefix='Instance',
                                   mutate_func=Instance.mutate)

        # Check the method returns None when there are no events.
        snapshot = event_player.take_snapshot('wrong')
        self.assertIsNone(snapshot)

        # Create a new entity.
        instance = register_new_instance(atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base')

        # Take a snapshot with the entity.
        snapshot1 = event_player.take_snapshot(instance.id)
        self.assertIsInstance(snapshot1, Snapshot)

        # Take another snapshot with the entity.
        snapshot2 = event_player.take_snapshot(instance.id)
        # - should return the previous snapshot
        self.assertIsInstance(snapshot2, Snapshot)
        self.assertEqual(snapshot2.at_event_id, snapshot1.at_event_id)

        # Generate a domain event.
        instance.beat_heart()

        # Take another snapshot with the entity.
        # - should use the previous snapshot and the heartbeat event
        snapshot3 = event_player.take_snapshot(instance.id)
        self.assertNotEqual(snapshot3.at_event_id, snapshot1.at_event_id)
