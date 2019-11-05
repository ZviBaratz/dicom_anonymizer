import random
import string

from datetime import datetime


def random_with_n_digits(n: int):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return random.randint(range_start, range_end)


def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def format_date(date_string: str) -> datetime.date:
    return datetime.strptime(date_string, "%Y%m%d").date()


def format_time(time_string: str) -> datetime.time:
    """
    Parses Time (TM) data elements to time objects.
    
    Parameters
    ----------
    element : DataElement
        DICOM Time (TM) data element.
    
    Returns
    -------
    datetime.time
        Native python time object.
    """

    try:
        # Try to parse according to the default time representation
        return datetime.strptime(time_string, "%H%M%S.%f").time()
    except ValueError:
        # If the value is not empty, try to parse with the fractional part
        if time_string:
            try:
                return datetime.strptime(time_string, "%H%M%S").time()
            except ValueError:
                return None

