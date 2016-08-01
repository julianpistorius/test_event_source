import uuid

from atmo_eventsourcing.utils.time import uuid_from_timestamp
from eventsourcing.domain.model.entity import EventSourcedEntity, mutableproperty, EntityRepository, entity_mutator, \
    singledispatch
from eventsourcing.domain.model.events import publish, DomainEvent


class Instance(EventSourcedEntity):
    """
    An event sourced domain model entity for Instances
    """

    __page_size__ = 1000  # Needed to get an event history longer than 10000 in Cassandra.

    class Created(EventSourcedEntity.Created):
        pass

    class AttributeChanged(EventSourcedEntity.AttributeChanged):
        pass

    class Discarded(EventSourcedEntity.Discarded):
        pass

    class Heartbeat(DomainEvent):
        pass

    def __init__(self, atmo_id, name, username, **kwargs):
        super(Instance, self).__init__(**kwargs)
        self._atmo_id = atmo_id
        self._name = name
        self._username = username

        self._status = 'unknown'
        self._activity = ''
        self._size = {'mem': '-1', 'disk': '-1', 'cpu': '-1'}
        self._count_heartbeats = 0

    @property
    def atmo_id(self):
        return self._atmo_id

    @mutableproperty
    def name(self):
        return self._name

    @property
    def username(self):
        return self._username

    @mutableproperty
    def status(self):
        return self._status

    @mutableproperty
    def activity(self):
        return self._activity

    @mutableproperty
    def size(self):
        return self._size

    def beat_heart(self):
        self._assert_not_discarded()
        event = self.Heartbeat(entity_id=self._id, entity_version=self._version)
        self._apply(event)
        publish(event)

    def count_heartbeats(self):
        return self._count_heartbeats

    @staticmethod
    def _mutator(event, initial):
        return instance_mutator(event, initial)

    @staticmethod
    def change_attribute_conditional(entity, name, value, timestamp=None):
        """Change an attribute, but only if it's different than the current value.

        :param entity: Instance entity to change
        :param name: Name of the attribute to change
        :param value: New value of the attribute
        :param timestamp: (Optional) The timestamp at which to register the change event.
        :return: None
        """
        current_value = getattr(entity, name, None)
        if value == current_value:
            return entity
        domain_event_id = None
        if timestamp:
            domain_event_id = uuid_from_timestamp(timestamp)
        event = Instance.AttributeChanged(name=name, value=value, entity_id=entity.id, entity_version=entity.version,
                                          domain_event_id=domain_event_id)
        new_instance = Instance.mutate(event=event)
        publish(event)
        return new_instance


@singledispatch
def instance_mutator(event, initial):
    return entity_mutator(event, initial)


@instance_mutator.register(Instance.Heartbeat)
def heartbeat_mutator(event, self):
    self._validate_originator(event)
    assert isinstance(self, Instance), self
    self._count_heartbeats += 1
    self._increment_version()
    return self


class InstanceRepository(EntityRepository):
    pass


def register_new_instance(atmo_id, name, username):
    """
    Factory method for Instance entities.

    :rtype: Instance
    """
    # Instead of generating a random entity_id, maybe we should generate a UUID from the atmo_id passed in?
    # entity_id = uuid.UUID(int=atmo_id, version=4).hex
    entity_id = uuid.uuid4().hex
    event = Instance.Created(entity_id=entity_id, atmo_id=atmo_id, name=name, username=username)
    entity = Instance.mutate(event=event)
    publish(event=event)
    return entity
