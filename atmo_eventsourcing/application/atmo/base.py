from atmo_eventsourcing.domain.model.allocation_source import register_new_allocation_source
from atmo_eventsourcing.domain.model.instance import register_new_instance
from atmo_eventsourcing.infrastructure.event_sourced_repos.allocation_source_repo import AllocationSourceRepo
from atmo_eventsourcing.infrastructure.event_sourced_repos.instance_repo import InstanceRepo
from eventsourcing.application.base import EventSourcingApplication


class AtmoEventSourcingApplication(EventSourcingApplication):
    def __init__(self, **kwargs):
        super(AtmoEventSourcingApplication, self).__init__(**kwargs)
        self.allocation_source_repo = AllocationSourceRepo(self.event_store)
        self.instance_repo = InstanceRepo(self.event_store)

    def register_new_allocation_source(self, a, b):
        return register_new_allocation_source(a=a, b=b)

    def register_new_instance(self, atmo_id, name, username):
        return register_new_instance(atmo_id=atmo_id, name=name, username=username)
