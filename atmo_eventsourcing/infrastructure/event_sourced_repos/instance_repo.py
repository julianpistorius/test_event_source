from eventsourcing.infrastructure.event_sourced_repo import EventSourcedRepository

from atmo_eventsourcing.domain.model.instance import InstanceRepository, Instance


class InstanceRepo(EventSourcedRepository, InstanceRepository):
    """
    Event sourced repository for the Instance domain model entity.
    """
    domain_class = Instance
