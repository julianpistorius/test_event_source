import datetime
import uuid

from eventsourcing.utils.time import utc_timezone


def datetime_to_timestamp(a_datetime):
    """Generate a Unix timestamp for a datetime.

    :param a_datetime: Datetime for which to get a timestamp. Note: Will probably fail if before 1970.
    :return: float. Seconds since the Epoch
    """
    return (a_datetime - datetime.datetime(1970, 1, 1, tzinfo=utc_timezone)).total_seconds()


def uuid_from_timestamp(unix_timestamp, node=None, clock_seq=None):
    """Generate a UUID from a Unix timestamp, host ID, and sequence number.
    If 'node' is not given, uuid.getnode() is used to obtain the hardware
    address.  If 'clock_seq' is given, it is used as the sequence number;
    otherwise a random 14-bit sequence number is chosen.

    Mostly a copy of uuid.uuid1

    :param unix_timestamp: (float) The time in seconds since the Epoch.
    :param node: If 'node' is not given, uuid.getnode() is used to obtain the hardware address
    :param clock_seq: The sequence number. If not given a random 14-bit sequence number is chosen
    :return: uuid.UUID
    """
    nanoseconds = int(unix_timestamp * 1e9)
    # 0x01b21dd213814000 is the number of 100-ns intervals between the
    # UUID epoch 1582-10-15 00:00:00 and the Unix epoch 1970-01-01 00:00:00.
    timestamp = int(nanoseconds // 100) + 0x01b21dd213814000L
    if clock_seq is None:
        import random
        clock_seq = random.randrange(1 << 14L)  # instead of stable storage
    time_low = timestamp & 0xffffffffL
    time_mid = (timestamp >> 32L) & 0xffffL
    time_hi_version = (timestamp >> 48L) & 0x0fffL
    clock_seq_low = clock_seq & 0xffL
    clock_seq_hi_variant = (clock_seq >> 8L) & 0x3fL
    if node is None:
        node = uuid.getnode()
    return uuid.UUID(fields=(time_low, time_mid, time_hi_version,
                             clock_seq_hi_variant, clock_seq_low, node), version=1)


def uuid_from_datetime(a_datetime):
    return uuid_from_timestamp(datetime_to_timestamp(a_datetime))
