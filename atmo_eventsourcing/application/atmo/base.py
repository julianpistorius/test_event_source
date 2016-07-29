from eventsourcing.application.base import EventSourcingApplication

from atmo_eventsourcing.domain.model.allocation_source import register_new_allocation_source
from atmo_eventsourcing.infrastructure.event_sourced_repos.allocation_source_repo import AllocationSourceRepo


class AtmoEventSourcingApplication(EventSourcingApplication):
    def __init__(self, **kwargs):
        super(AtmoEventSourcingApplication, self).__init__(**kwargs)
        self.allocation_source_repo = AllocationSourceRepo(self.event_store)

    def register_new_allocation_source(self, a, b):
        return register_new_allocation_source(a=a, b=b)  # This is weird.
