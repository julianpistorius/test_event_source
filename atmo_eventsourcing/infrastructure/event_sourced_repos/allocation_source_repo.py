from eventsourcing.infrastructure.event_sourced_repo import EventSourcedRepository

from atmo_eventsourcing.domain.model.allocation_source import AllocationSourceRepository, AllocationSource


class AllocationSourceRepo(EventSourcedRepository, AllocationSourceRepository):
    """
    Event sourced repository for the AllocationSource domain model entity.
    """
    domain_class = AllocationSource
