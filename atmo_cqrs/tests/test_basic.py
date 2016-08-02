import datetime
import json
import random
import unittest
import uuid

import records
from eventsourcing.utils.time import utc_timezone
from faker import Faker

from atmo_cqrs.db import QUERY_SELECT_EVENTS, QUERY_INSERT_EVENT, QUERY_CREATE_TABLE, QUERY_DROP_TABLE
from atmo_cqrs.tests.test_data import INSTANCE_STATUSES
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
        for i in xrange(1000):
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
                          event_topic=event_topic,
                          event_attrs=event_attrs_json)
        rows = self.db.query(QUERY_SELECT_EVENTS)
        print(rows.export('csv'))


if __name__ == '__main__':
    unittest.main()
