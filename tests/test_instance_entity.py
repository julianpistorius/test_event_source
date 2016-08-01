import StringIO
import csv
import datetime
import unittest

from dateutil.parser import parse

from atmo_eventsourcing.domain.model.instance import register_new_instance, Instance
from atmo_eventsourcing.infrastructure.event_sourced_repos.instance_repo import InstanceRepo
from atmo_eventsourcing.utils.time import datetime_to_timestamp, uuid_from_timestamp
from eventsourcing.domain.model.entity import EntityIDConsistencyError, EntityVersionConsistencyError
from eventsourcing.domain.model.events import DomainEvent, assert_event_handlers_empty, publish
from eventsourcing.infrastructure.event_player import EventPlayer
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.python_objects_stored_events import PythonObjectsStoredEventRepository
from eventsourcing.utils.time import utc_timezone

STATUS_HISTORY_TEST_DATA = '''instance_id,ih_id,start_date,end_date,status,activity,username,size_id,cpu,mem,disk,name
22779,98630,2015-12-14T02:32:18-07:00,2015-12-14T02:32:19.632057-07:00,unknown,,amitj,136,-1,-1,-1,MyInstance1
22779,98631,2015-12-14T02:32:19.632057-07:00,2015-12-14T02:33:22.038840-07:00,build,,amitj,23,1,4096,0,MyInstance1
22779,98632,2015-12-14T02:33:22.038840-07:00,2015-12-14T02:34:22.544317-07:00,networking,,amitj,23,1,4096,0,MyInstance1
22779,98633,2015-12-14T02:34:22.544317-07:00,2015-12-14T02:36:11.560037-07:00,deploying,,amitj,23,1,4096,0,MyInstance1
22779,98634,2015-12-14T02:36:11.560037-07:00,2015-12-17T17:56:44.072222-07:00,active,,amitj,23,1,4096,0,MyInstance1
22779,99681,2015-12-17T17:56:44.072222-07:00,2016-01-27T14:29:27.114551-07:00,suspended,,amitj,23,1,4096,0,MyInstance1
22779,104734,2016-01-27T14:29:27.114551-07:00,2016-01-27T14:30:33.373198-07:00,networking,,amitj,38,4,8192,0,MyInstance2
22779,104736,2016-01-27T14:30:33.373198-07:00,2016-01-27T15:09:07.974776-07:00,deploying,,amitj,38,4,8192,0,MyInstance2
22779,104748,2016-01-27T15:09:07.974776-07:00,2016-01-27T16:23:29.262009-07:00,active,,amitj,38,4,8192,0,MyInstance2
22779,104755,2016-01-27T16:23:29.262009-07:00,2016-04-07T11:06:17.263607-07:00,suspended,,amitj,38,4,8192,0,MyInstance2
'''


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
        self.assertEqual({'mem': '-1', 'disk': '-1', 'cpu': '-1'}, instance1.size)

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
        self.assertTrue(instance1.id)
        self.assertEqual(1, instance1.version)
        self.assertTrue(instance1.created_on)
        self.assertAlmostEqual(instance_created_timestamp, instance1.created_on)

    def test_version_does_not_change_for_spurious_changes(self):
        # TODO: Fix this
        instance1 = register_new_instance(atmo_id=27216, name='Ubuntu 14.04.2 XFCE Base', username='amitj')
        self.assertIsInstance(instance1, Instance)

        # Check the properties of the Instance class.
        self.assertEqual(27216, instance1.atmo_id)
        self.assertEqual('Ubuntu 14.04.2 XFCE Base', instance1.name)
        self.assertEqual(1, instance1.version)
        instance1.name = 'Ubuntu 14.04.2 XFCE Base'
        self.assertEqual(1, instance1.version)
        instance1.name = 'Ubuntu 15.04.2 XFCE Base'
        # TODO: Fix this
        # self.assertEqual(2, instance1.version)

    def test_calculate_usage(self):
        repo = InstanceRepo(self.event_store)
        event_player = EventPlayer(event_store=self.event_store, id_prefix='Instance', mutate_func=Instance.mutate)
        status_history_file_object = StringIO.StringIO(STATUS_HISTORY_TEST_DATA)
        reader = csv.DictReader(status_history_file_object)
        for row in reader:
            print(row)
            atmo_id = row['instance_id']
            instance_status_timestamp = datetime_to_timestamp(parse(row['start_date']))
            domain_event_id = uuid_from_timestamp(instance_status_timestamp)
            most_recent_event = event_player.get_most_recent_event(atmo_id)
            if most_recent_event is None:
                create_event = Instance.Created(entity_id=atmo_id, atmo_id=atmo_id, name=row['name'],
                                                username='amitj',
                                                # domain_event_id=domain_event_id
                                                )
                self.event_store.append(create_event)
                instance_status_timestamp += 1

            instance_size = {'mem': row['mem'], 'disk': row['disk'], 'cpu': row['cpu']}
            new_values = {
                'name': row['name'],
                'status': row['status'],
                'activity': row['activity'],
                'size': instance_size
            }
            instance = event_player.replay_events(atmo_id)
            instance_version = instance.version
            for attribute_name, new_value in new_values.iteritems():
                current_value = getattr(instance, attribute_name, None)
                if new_value == current_value:
                    continue
                domain_event_id = uuid_from_timestamp(instance_status_timestamp)
                instance_status_timestamp += 1
                new_event = Instance.AttributeChanged(name=attribute_name, value=new_value, entity_id=atmo_id,
                                                      entity_version=instance_version,
                                                      # domain_event_id=domain_event_id
                                                      )
                self.event_store.append(new_event)
                instance_version += 1

    def test_not_implemented_error(self):
        # Define an event class.
        class UnsupportedEvent(DomainEvent):
            pass

        # Check we get an error when attempting to mutate on the event.
        self.assertRaises(NotImplementedError, Instance.mutate, Instance, UnsupportedEvent('1', '0'))
