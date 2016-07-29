import uuid

from eventsourcing.domain.model.entity import EventSourcedEntity, mutableproperty, EntityRepository, entity_mutator, \
    singledispatch
from eventsourcing.domain.model.events import publish, DomainEvent


class AllocationSource(EventSourcedEntity):
    """
    An example event sourced domain model entity.
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

    def __init__(self, a, b, **kwargs):
        super(AllocationSource, self).__init__(**kwargs)
        self._a = a
        self._b = b
        self._count_heartbeats = 0

    @mutableproperty
    def a(self):
        return self._a

    @mutableproperty
    def b(self):
        return self._b

    def beat_heart(self):
        self._assert_not_discarded()
        event = self.Heartbeat(entity_id=self._id, entity_version=self._version)
        self._apply(event)
        publish(event)

    def count_heartbeats(self):
        return self._count_heartbeats

    @staticmethod
    def _mutator(event, initial):
        return example_mutator(event, initial)


@singledispatch
def example_mutator(event, initial):
    return entity_mutator(event, initial)


@example_mutator.register(AllocationSource.Heartbeat)
def heartbeat_mutator(event, self):
    self._validate_originator(event)
    assert isinstance(self, AllocationSource), self
    self._count_heartbeats += 1
    self._increment_version()
    return self


class AllocationSourceRepository(EntityRepository):
    pass


def register_new_example(a, b):
    """
    Factory method for example entities.

    :rtype: AllocationSource
    """
    entity_id = uuid.uuid4().hex
    event = AllocationSource.Created(entity_id=entity_id, a=a, b=b)
    entity = AllocationSource.mutate(event=event)
    publish(event=event)
    return entity
