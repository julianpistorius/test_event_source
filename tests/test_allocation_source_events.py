import unittest

from eventsourcing.domain.model.events import assert_event_handlers_empty
from eventsourcing.infrastructure.event_player import EventPlayer
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.stored_events.python_objects_stored_events import PythonObjectsStoredEventRepository

from atmo_eventsourcing.domain.model.allocation_source import AllocationSource


class TestEventPlayer(unittest.TestCase):
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
