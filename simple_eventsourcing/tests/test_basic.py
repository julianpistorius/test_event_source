import StringIO
import csv
import datetime
import json
import random
import unittest
import uuid
from hashlib import md5

import records
from dateutil.parser import parse
from eventsourcing.utils.time import utc_timezone
from faker import Faker

from simple_eventsourcing.db import QUERY_SELECT_EVENTS, QUERY_INSERT_EVENT, QUERY_CREATE_TABLE, QUERY_DROP_TABLE, \
    QUERY_SELECT_EVENTS_BY_EVENT_DATE
from simple_eventsourcing.tests.test_data import INSTANCE_STATUSES, INSTANCE_STATUS_HISTORY_DATA_01, \
    ALLOCATION_SOURCE_CHANGE_DATA_01
from atmo_eventsourcing.utils.time import datetime_to_timestamp


class BasicTestCase(unittest.TestCase):
    def setUp(self):
        super(BasicTestCase, self).setUp()
        self.fake = Faker()
        self.fake.seed(501337)

        self.db = records.Database('sqlite:////tmp/simple_cqrs.db')
        self.db.query(QUERY_DROP_TABLE)
        self.db.query(QUERY_CREATE_TABLE)

    def tearDown(self):
        super(BasicTestCase, self).tearDown()

    def test_random_data(self):
        # skip('Skip for now')
        for i in xrange(10):
            entity_id = i % 20 + 1000
            event_id = str(uuid.uuid4())
            timestamp = datetime_to_timestamp(datetime.datetime.now(tz=utc_timezone))
            event_topic = 'project.domain.model.instance#Instance.StatusChanged'
            random_status = random.choice(INSTANCE_STATUSES)
            event_attrs = {'entity_id': entity_id, 'status': random_status, 'timestamp': timestamp}
            event_attrs_json = json.dumps(event_attrs)
            self.db.query(QUERY_INSERT_EVENT,
                          entity_id=entity_id,
                          event_id=event_id,
                          timestamp=timestamp,
                          event_date=timestamp,
                          event_topic=event_topic,
                          event_attrs=event_attrs_json)
        rows = self.db.query(QUERY_SELECT_EVENTS)
        print(rows.export('csv'))

    def test_instance_status_history(self):
        load_status_history_data(self.db, INSTANCE_STATUS_HISTORY_DATA_01)
        rows = self.db.query(QUERY_SELECT_EVENTS)
        print(rows.export('csv'))

    def test_allocation_source_change(self):
        load_allocation_source_change_data(self.db, ALLOCATION_SOURCE_CHANGE_DATA_01)
        rows = self.db.query(QUERY_SELECT_EVENTS)
        print(rows.export('csv'))

    def test_instance_status_history_and_allocation_source_change(self):
        load_status_history_data(self.db, INSTANCE_STATUS_HISTORY_DATA_01)
        load_allocation_source_change_data(self.db, ALLOCATION_SOURCE_CHANGE_DATA_01)
        rows = self.db.query(QUERY_SELECT_EVENTS_BY_EVENT_DATE)
        print(rows.export('csv'))


def load_status_history_data(db, status_history_data):
    status_history_file_object = StringIO.StringIO(status_history_data)
    reader = csv.DictReader(status_history_file_object)
    for row in reader:
        entity_id = row['instance_id']
        timestamp = datetime_to_timestamp(datetime.datetime.now(tz=utc_timezone))
        event_date = datetime_to_timestamp(parse(row['start_date']))
        event_topic = 'atmosphere.model.instance#Instance.StatusChanged'
        event_attrs = row
        event_attrs_json = json.dumps(event_attrs)
        hash = md5(event_attrs_json).digest()
        event_id = str(uuid.UUID(bytes=hash[:16], version=3))
        db.query(QUERY_INSERT_EVENT,
                 entity_id=entity_id,
                 event_id=event_id,
                 timestamp=timestamp,
                 event_date=event_date,
                 event_topic=event_topic,
                 event_attrs=event_attrs_json)


def load_allocation_source_change_data(db, allocation_source_change_data):
    allocation_source_change_data_file_object = StringIO.StringIO(allocation_source_change_data)
    reader = csv.DictReader(allocation_source_change_data_file_object)
    for row in reader:
        timestamp = datetime_to_timestamp(datetime.datetime.now(tz=utc_timezone))
        event_date = datetime_to_timestamp(parse(row['event_date']))
        event_topic = 'atmosphere.model.instance#Instance.AllocationSourceChanged'
        event_attrs = row
        event_attrs_json = json.dumps(event_attrs)
        entity_id = row['instance_id']
        hash = md5(event_attrs_json).digest()
        event_id = str(uuid.UUID(bytes=hash[:16], version=3))

        db.query(QUERY_INSERT_EVENT,
                 entity_id=entity_id,
                 event_id=event_id,
                 timestamp=timestamp,
                 event_date=event_date,
                 event_topic=event_topic,
                 event_attrs=event_attrs_json)


if __name__ == '__main__':
    unittest.main()
