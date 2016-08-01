import datetime
import unittest
import uuid

from atmo_eventsourcing.domain.model.instance import register_new_instance, Instance
from atmo_eventsourcing.infrastructure.event_sourced_repos.instance_repo import InstanceRepo
from eventsourcing.domain.model.entity import EntityIDConsistencyError, EntityVersionConsistencyError
from eventsourcing.domain.model.events import DomainEvent, assert_event_handlers_empty, publish
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.python_objects_stored_events import PythonObjectsStoredEventRepository
from eventsourcing.utils.time import utc_timezone


def datetime_to_timestamp(a_datetime):
    """Generate a Unix timestamp for a datetime.

    :param a_datetime: Datetime for which to get a timestamp. Note: Will probably fail if before 1970.
    :return: float. Seconds since the Epoch
    """
    return (a_datetime - datetime.datetime(1970, 1, 1, tzinfo=utc_timezone)).total_seconds()


def uuid_from_timestamp(unix_timestamp, node=None, clock_seq=None):
    """Generate a UUID from a Unix timestamp, host ID, and sequence number.
    If 'node' is not given, uuid.getnode() is used to obtain the hardware
    address.  If 'clock_seq' is given, it is used as the sequence number;
    otherwise a random 14-bit sequence number is chosen.

    Mostly a copy of uuid.uuid1

    :param unix_timestamp: (float) The time in seconds since the Epoch.
    :param node: If 'node' is not given, uuid.getnode() is used to obtain the hardware address
    :param clock_seq: The sequence number. If not given a random 14-bit sequence number is chosen
    :return: uuid.UUID
    """
    nanoseconds = int(unix_timestamp * 1e9)
    # 0x01b21dd213814000 is the number of 100-ns intervals between the
    # UUID epoch 1582-10-15 00:00:00 and the Unix epoch 1970-01-01 00:00:00.
    timestamp = int(nanoseconds // 100) + 0x01b21dd213814000L
    if clock_seq is None:
        import random
        clock_seq = random.randrange(1 << 14L)  # instead of stable storage
    time_low = timestamp & 0xffffffffL
    time_mid = (timestamp >> 32L) & 0xffffL
    time_hi_version = (timestamp >> 48L) & 0x0fffL
    clock_seq_low = clock_seq & 0xffL
    clock_seq_hi_variant = (clock_seq >> 8L) & 0x3fL
    if node is None:
        node = uuid.getnode()
    return uuid.UUID(fields=(time_low, time_mid, time_hi_version,
                             clock_seq_hi_variant, clock_seq_low, node), version=1)


def uuid_from_datetime(a_datetime):
    return uuid_from_timestamp(datetime_to_timestamp(a_datetime))


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
        instance1 = register_new_instance(atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base', username='amitj')
        self.assertIsInstance(instance1, Instance)

        # Check the properties of the Instance class.
        self.assertEqual(27216, instance1.atmo_id)
        self.assertEqual('Ubuntu 14.04.2 XFCE Base', instance1.name)
        self.assertEqual('amitj', instance1.username)
        self.assertEqual('unknown', instance1.status)
        self.assertEqual('', instance1.activity)
        self.assertEqual({-1, -1, -1}, instance1.size)

        # Check the properties of the Instance class.
        self.assertTrue(instance1.id)
        self.assertEqual(1, instance1.version)
        self.assertTrue(instance1.created_on)

        # Check a second instance with the same values is not "equal" to the first.
        # TODO: Actually, maybe it will be, and more importantly, _should_ be.
        instance2 = register_new_instance(atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base', username='amitj')
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

        # Check the mutable properties can be updated, but not the immutable ones:
        # Immutable:
        # - atmo_id
        # - username
        #
        # Mutable:
        # - name
        # - status
        # - activity
        # - size
        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            entity1.atmo_id = 27217
        self.assertEqual(27216, repo[entity1.id].atmo_id)
        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            entity1.username = 'someotheruser'
        self.assertEqual('amitj', repo[entity1.id].username)

        entity1.name = 'Ubuntu 16.04.1 XFCE Base'
        self.assertEqual('Ubuntu 16.04.1 XFCE Base', repo[entity1.id].name)
        entity1.status = 'pending'
        self.assertEqual('pending', repo[entity1.id].status)
        entity1.activity = 'networking'
        self.assertEqual('networking', repo[entity1.id].activity)
        entity1.size = {'mem': '65536', 'disk': '0', 'cpu': '16'}
        self.assertEqual({'mem': '65536', 'disk': '0', 'cpu': '16'}, repo[entity1.id].size)

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

    def test_entity_created_date(self):
        instance_created_timestamp = datetime_to_timestamp(datetime.datetime(2016, 1, 1, tzinfo=utc_timezone))
        domain_event_id = uuid_from_timestamp(instance_created_timestamp)
        event = Instance.Created(entity_id='instance1', atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base',
                                 username='amitj', domain_event_id=domain_event_id)
        instance1 = Instance.mutate(event=event)
        publish(event=event)

        self.assertIsInstance(instance1, Instance)

        # Check the properties of the Instance class.
        self.assertEqual(27216, instance1.atmo_id)
        self.assertEqual('Ubuntu 14.04.2 XFCE Base', instance1.name)

        # Check the properties of the Instance class.
        self.assertTrue(instance1.id)
        self.assertEqual(1, instance1.version)
        self.assertTrue(instance1.created_on)
        self.assertAlmostEqual(instance_created_timestamp, instance1.created_on)

    def test_not_implemented_error(self):
        # Define an event class.
        class UnsupportedEvent(DomainEvent):
            pass

        # Check we get an error when attempting to mutate on the event.
        self.assertRaises(NotImplementedError, Instance.mutate, Instance, UnsupportedEvent('1', '0'))
