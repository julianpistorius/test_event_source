import unittest
from uuid import uuid1

from eventsourcing.domain.model.events import assert_event_handlers_empty
from eventsourcing.domain.model.snapshot import take_snapshot, Snapshot
from eventsourcing.infrastructure.event_player import EventPlayer, entity_from_snapshot
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.python_objects_stored_events import PythonObjectsStoredEventRepository

from atmo_eventsourcing.domain.model.allocation_source import AllocationSource, register_new_allocation_source


class TestAllocationSourceEventPlayer(unittest.TestCase):
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

        # Store Allocation Source events.
        event1 = AllocationSource.Created(entity_id='entity1', a=1, b=2)
        event_store.append(event1)
        event2 = AllocationSource.Created(entity_id='entity2', a=2, b=4)
        event_store.append(event2)
        event3 = AllocationSource.Created(entity_id='entity3', a=3, b=6)
        event_store.append(event3)
        event4 = AllocationSource.Discarded(entity_id='entity3', entity_version=1)
        event_store.append(event4)

        # Check the event sourced entities are correct.
        # - just use a trivial mutate that always instantiates the 'AllocationSource'.
        event_player = EventPlayer(event_store=event_store, id_prefix='AllocationSource',
                                   mutate_func=AllocationSource.mutate)

        # The the reconstituted entity has correct attribute values.
        self.assertEqual('entity1', event_player.replay_events('entity1').id)
        self.assertEqual(1, event_player.replay_events('entity1').a)
        self.assertEqual(2, event_player.replay_events('entity2').a)
        self.assertEqual(None, event_player.replay_events('entity3'))

        # Check entity3 raises KeyError.
        self.assertEqual(event_player.replay_events('entity3'), None)

        # Check it works for "short" entities (should be faster, but the main thing is that it still works).
        # - just use a trivial mutate that always instantiates the 'AllocationSource'.
        event5 = AllocationSource.AttributeChanged(entity_id='entity1', entity_version=1, name='a', value=10)
        event_store.append(event5)

        event_player = EventPlayer(event_store=event_store, id_prefix='AllocationSource',
                                   mutate_func=AllocationSource.mutate)

        self.assertEqual(10, event_player.replay_events('entity1').a)

        event_player = EventPlayer(
            event_store=event_store,
            id_prefix='AllocationSource',
            mutate_func=AllocationSource.mutate,
            is_short=True,
        )
        self.assertEqual(10, event_player.replay_events('entity1').a)

    def test_snapshots(self):
        stored_event_repo = PythonObjectsStoredEventRepository()
        event_store = EventStore(stored_event_repo)
        self.ps = PersistenceSubscriber(event_store)
        event_player = EventPlayer(event_store=event_store, id_prefix='AllocationSource',
                                   mutate_func=AllocationSource.mutate)

        # Create a new entity.
        registered_allocation_source = register_new_allocation_source(a=123, b=234)

        # Take a snapshot.
        snapshot = take_snapshot(registered_allocation_source, uuid1().hex)

        # Replay from this snapshot.
        after = snapshot.at_event_id
        initial_state = entity_from_snapshot(snapshot)
        retrieved_allocation_source = event_player.replay_events(registered_allocation_source.id,
                                                                 initial_state=initial_state, after=after)

        # Check the attributes are correct.
        self.assertEqual(retrieved_allocation_source.a, 123)

        # Remember the time now.
        timecheck1 = uuid1().hex

        # Change attribute value.
        retrieved_allocation_source.a = 999

        # Check the initial state doesn't move.
        self.assertEqual(initial_state.a, 123)

        # Remember the time now.
        timecheck2 = uuid1().hex

        # Change attribute value.
        retrieved_allocation_source.a = 9999

        # Remember the time now.
        timecheck3 = uuid1().hex

        # Check the event sourced entities are correct.
        assert initial_state.a == 123
        retrieved_allocation_source = event_player.replay_events(registered_allocation_source.id)
        self.assertEqual(retrieved_allocation_source.a, 9999)

        # Take another snapshot.
        snapshot2 = take_snapshot(retrieved_allocation_source, uuid1().hex)

        # Check we can replay from this snapshot.
        initial_state2 = entity_from_snapshot(snapshot2)
        after2 = snapshot2.domain_event_id
        retrieved_allocation_source = event_player.replay_events(registered_allocation_source.id,
                                                                 initial_state=initial_state2,
                                                                 after=after2)
        # Check the attributes are correct.
        self.assertEqual(retrieved_allocation_source.a, 9999)

        # Check we can get historical state at timecheck1.
        retrieved_allocation_source = event_player.replay_events(registered_allocation_source.id, until=timecheck1)
        self.assertEqual(retrieved_allocation_source.a, 123)

        # Check we can get historical state at timecheck2.
        retrieved_allocation_source = event_player.replay_events(registered_allocation_source.id, until=timecheck2)
        self.assertEqual(retrieved_allocation_source.a, 999)

        # Check we can get historical state at timecheck3.
        retrieved_allocation_source = event_player.replay_events(registered_allocation_source.id, until=timecheck3)
        self.assertEqual(retrieved_allocation_source.a, 9999)

        # Similarly, check we can get historical state using a snapshot
        retrieved_allocation_source = event_player.replay_events(registered_allocation_source.id,
                                                                 initial_state=initial_state, after=after,
                                                                 until=timecheck2)
        self.assertEqual(retrieved_allocation_source.a, 999)

    def test_take_snapshot(self):
        # Check the EventPlayer's take_snapshot() method.
        stored_event_repo = PythonObjectsStoredEventRepository()
        event_store = EventStore(stored_event_repo)
        self.ps = PersistenceSubscriber(event_store)
        event_player = EventPlayer(event_store=event_store, id_prefix='AllocationSource',
                                   mutate_func=AllocationSource.mutate)

        # Check the method returns None when there are no events.
        snapshot = event_player.take_snapshot('wrong')
        self.assertIsNone(snapshot)

        # Create a new entity.
        allocation_source = register_new_allocation_source(a=123, b=234)

        # Take a snapshot with the entity.
        snapshot1 = event_player.take_snapshot(allocation_source.id)
        self.assertIsInstance(snapshot1, Snapshot)

        # Take another snapshot with the entity.
        snapshot2 = event_player.take_snapshot(allocation_source.id)
        # - should return the previous snapshot
        self.assertIsInstance(snapshot2, Snapshot)
        self.assertEqual(snapshot2.at_event_id, snapshot1.at_event_id)

        # Generate a domain event.
        allocation_source.beat_heart()

        # Take another snapshot with the entity.
        # - should use the previous snapshot and the heartbeat event
        snapshot3 = event_player.take_snapshot(allocation_source.id)
        self.assertNotEqual(snapshot3.at_event_id, snapshot1.at_event_id)
