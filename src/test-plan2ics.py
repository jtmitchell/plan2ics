# -*- coding: utf-8 -*-

# Tests are run using nose

from nose import with_setup
from nose.tools import assert_equals

from plan2ics import dayplan
from StringIO import StringIO
import datetime
import re

import PyICU
defaultTZ = PyICU.ICUtzinfo.getDefault()


test_calendar = """
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 0 15 0
N    Monthly event - 1,2,3,LAST
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 257 0 0
N    Monthly event - first Sunday
10/5/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    259200 1286323200 0 0 0
N    Daily Event - every 3 days, end 2010
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 8450 2 0
N    Monthly event - first and last Monday, and 1st of the month
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 0 0 1
E    9/11/2010
N    Yearly event
M    This is the text
M    of my
M    YEARLY EVENT
1/1/2001  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 0 0 1
N    New Year's Day
S    #Pilot: 1 J_Mitchell_1349521844 6d314cd8fbc3e89b33abdf330988e979 0 1323214
"""


def loading_test():
    fhandle = StringIO(test_calendar)
    p = dayplan(fhandle)
    i = 0
    for event in p.calendar.getChildren():
        i += 1
    # the timezone information counts as an extra entry
    assert_equals(i, 7, 'Expect 7 entries. Got %s' % i)


def yearly_test():
    plan = """
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 0 0 1
E    9/11/2010
N    Yearly event
M    This is the text
M    of my
M    YEARLY EVENT
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.rrule.value, 'FREQ=YEARLY')


def exception_test():
    plan = """
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 0 0 1
E    9/11/2010
N    Yearly event
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.exdate.value, [datetime.date(2010, 9, 11)])


def until_test():
    plan = """
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 1286323200 0 0 1
E    9/11/2010
N    Yearly event
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert re.search('UNTIL=20101006', p.calendar.vevent.rrule.value)


def daily_test():
    plan = """
10/5/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    259200 1286323200 0 0 0
N    Daily Event - every 3 days, end 2010
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.rrule.value,
                  'FREQ=DAILY;INTERVAL=3;UNTIL=20101006')


def monthly1_test():
    plan = """
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 0 15 0
N    Monthly event - 1,2,3,LAST
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.rrule.value,
                  'FREQ=MONTHLY;BYMONTHDAY=1,2,3,-1')


def monthly2_test():
    plan = """
9/11/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 8963 0 0
N    Monthly event - first, second and last Sunday and Monday
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.rrule.value,
                  'FREQ=MONTHLY;BYDAY=1SU,1MO,2SU,2MO,-1SU,-1MO')


def weekly_test():
    plan = """
7/21/2009  16:0:0  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 4 0 0
N    Weekly event. Tuesday at 4pm
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.rrule.value, 'FREQ=WEEKLY;BYDAY=TU')


def dtend_test():
    plan = """
7/21/2009  16:0:0  0:0:0  0:0:0  0:0:0  ---------- 0 0
N    Event at 4pm
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.dtstart.value,
                  datetime.datetime(2009, 7, 21, 16, 0, tzinfo=defaultTZ))
    assert_equals(p.calendar.vevent.dtend.value,
                  datetime.datetime(2009, 7, 21, 16, 0, tzinfo=defaultTZ))


def duration_test():
    plan = """
7/21/2009  16:0:0  1:30:0  0:0:0  0:0:0  ---------- 0 0
N    Event at 4pm for 1hr 30min
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.dtstart.value,
                  datetime.datetime(2009, 7, 21, 16, 0, tzinfo=defaultTZ))
    assert_equals(p.calendar.vevent.dtend.value,
                  datetime.datetime(2009, 7, 21, 17, 30, tzinfo=defaultTZ))


def allday_test():
    plan = """
7/21/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
N    All day event
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.dtstart.value, datetime.date(2009, 7, 21))
    assert_equals(p.calendar.vevent.dtend.value, datetime.date(2009, 7, 22))


def yearly_allday_test():
    plan = """
7/21/2009  99:99:99  0:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 0 0 0 1
N    All day event, repeat yearly
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.dtstart.value, datetime.date(2009, 7, 21))
    assert_equals(p.calendar.vevent.dtend.value, datetime.date(2009, 7, 22))
    assert_equals(p.calendar.vevent.rrule.value, 'FREQ=YEARLY')


def duration_and_until_test():
    plan = """
2/14/2009  8:30:0  2:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 1238198400 64 0 0
N    Weekly event on Saturday, duration is 2hrs, until 2009/03/28
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    assert_equals(p.calendar.vevent.dtstart.value,
                  datetime.datetime(2009, 2, 14, 8, 30, tzinfo=defaultTZ))
    assert_equals(p.calendar.vevent.dtend.value,
                  datetime.datetime(2009, 2, 14, 10, 30, tzinfo=defaultTZ))
    assert re.search('UNTIL=20090328', p.calendar.vevent.rrule.value)


def ensure_unicode_test():
    # because the Ligthning/Sunbird calendar objects otherwise
    plan = """
2/14/2009  8:30:0  2:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 1238198400 64 0 0
N    Weekly event on Saturday, duration is 2hrs, until 2009/03/28
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    o = p.pprint()
    assert isinstance(o, unicode)


def translate_chars_test():
    plan = """
2/14/2009  8:30:0  2:0:0  0:0:0  0:0:0  ---------- 0 0
R    0 1238198400 64 0 0
N    this event has an 0xa0 char that kills unicode \xa0
    """
    fhandle = StringIO(plan)
    p = dayplan(fhandle)
    print p.pprint()
    o = p.pprint()
    assert isinstance(o, unicode)
