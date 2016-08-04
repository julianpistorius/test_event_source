QUERY_SELECT_EVENTS = 'SELECT * FROM simple_events'
QUERY_SELECT_EVENTS_BY_EVENT_DATE = 'SELECT * FROM simple_events ORDER BY event_date'
QUERY_INSERT_EVENT = '''
INSERT INTO simple_events (
  entity_id,
  event_id,
  timestamp,
  event_date,
  event_topic,
  event_attrs)
VALUES (
  :entity_id,
  :event_id,
  :timestamp,
  :event_date,
  :event_topic,
  :event_attrs
)'''
QUERY_CREATE_TABLE = '''
CREATE TABLE simple_events (
  id             INTEGER PRIMARY KEY,
  entity_id      TEXT,
  event_id       TEXT,
  timestamp      FLOAT,
  event_date     FLOAT,
  event_topic    TEXT,
  event_attrs    TEXT
)'''
QUERY_DROP_TABLE = '''DROP TABLE IF EXISTS simple_events'''