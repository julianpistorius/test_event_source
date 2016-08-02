def get_store(uri):
    raise NotImplementedError


def append(store, event):
    raise NotImplementedError


def get_entity_events(db, stored_entity_id, after=None, until=None, limit=None, query_ascending=True,
                      results_ascending=True):
    raise NotImplementedError
    if not query_ascending or not results_ascending:
        # Don't know how to handle this yet
        raise NotImplementedError

    if after or until or limit:
        # Don't know how to handle this yet
        raise NotImplementedError
