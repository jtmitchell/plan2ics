#!/usr/bin/python

#    netplan2ics.py
#    Convert a netplan file into an iCalendar file.
#
#    Information gathered from:
#    - the Perl script plan2vcs by Bert Bos
#    - the plan manpage (man -S4 plan)
#    - vobject readme file
#    - the dateutil website
#
#    Copyright (c) 2009, James Mitchell
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import re
import optparse
import vobject
import datetime
import uuid
from dateutil.rrule import rruleset, rrulestr
from string import maketrans

import PyICU

import hashlib

datetime_rx = re.compile(r'(?P<date>\d+/\d+/\d+)\s+(?P<time>\d+:\d+:\d+)')
duration_rx = re.compile(
    r'\s+(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)')
exception_rx = re.compile(r'E\s+(?P<date>\d+/\d+/\d+)')
repeat_rx = re.compile(
    r'R\s+(?P<trigger_secs>\d+)\s+(?P<delete_secs>\d+)\s+(?P<weekdaymap>\d+)\s+(?P<monthdaymap>\d+)\s+(?P<yearly>\d)')
note_rx = re.compile(r'N\s+(?P<message>.*)$')
message_rx = re.compile(r'M\s+(?P<message>.*)$')
where_rx = re.compile(r'Where\s*:\s*(?P<location>\w.*)$')
script_rx = re.compile(
    r'S\s+#plan2ics:\s+version=(?P<version>\d+)\s+uuid=(?P<uid>[\w-]+)\s+hash=(?P<hash>\w+)$')
groupmtg_rx = re.compile(r'G\s+')

epoch = datetime.date(1970, 1, 1)
weekday = (
    'SU',
    'MO',
    'TU',
    'WE',
    'TH',
    'FR',
    'SA',
)
weeknumber = (
    '1',
    '2',
    '3',
    '4',
    '5',
    '-1',
)
one_day = datetime.timedelta(days=1)
translate_map = maketrans('\xa0', ' ')


class Event(object):
    _uid = None
    vevent = None   # ICS version of event
    pevent = None   # array containing netplan version of event
    extra = None
    verbose = False

    def __init__(self, vevent, event, verbose=False):
        self.vevent = vevent
        self.pevent = event
        self.verbose = verbose
        self.extra = []
        self._load_plan()

    @property
    def uid(self):
        return str(self._uid)

    @property
    def hash(self):
        return hashlib.md5(self.pevent[0]).hexdigest()

    @property
    def plan(self):
        if self.pevent:
            return "%s%s" % (''.join(self.pevent), '\n'.join(self.extra))
        else:
            return ''

    @property
    def ics(self):
        if self.vevent:
            return self.vevent
        else:
            return ''

    def _escape(self, text):
        """Returns the given text with everything above ASCII 128 removed."""
        text = "".join([x for x in text if ord(x) < 128])
        return text

    def _load_plan(self):
        dt = datetime_rx.match(self.pevent[0])
        dt_start = None
        dt_end = None
        dt_until = None
        time = dt.group('time')
        if time == '99:99:99':
            # there is no alarm trigger time
            # I will treat these as transparent, all-day events
            dt_start = datetime.datetime.strptime('%s' % dt.group('date'),
                                                  '%m/%d/%Y').date()
            self.vevent.add('dtstart').value = dt_start
            dt_end = dt_start + one_day
            self.vevent.add('transp').value = 'TRANSPARENT'
        else:
            # we have a trigger time, and will use it for the end time
            # until something better comes along
            dt_start = datetime.datetime.strptime(
                '%s %s' % (dt.group('date'), time),
                '%m/%d/%Y %H:%M:%S')
            self.vevent.add('dtstart').value = dt_start
            self.vevent.add('transp').value = 'OPAQUE'
        description = []
        rrule_set = None
        location = None
        for line in re.split(r'\n', self.pevent[1]):
            if not line:
                continue
            if line[0] == 'N':
                m = note_rx.match(line)
                if m:
                    self.vevent.add('summary').value = self._escape(
                        m.group('message')
                    )
                    if '@' in m.group('message'):
                        location = m.group('message').split('@', 1)[-1]
            elif line[0] == 'M':
                m = message_rx.match(line)
                if m:
                    description.append(self._escape(m.group('message')))
                    l = where_rx.match(m.group('message'))
                    if l:
                        location = l.group('location')
            elif line[0] == 'R':
                m = repeat_rx.match(line)
                if m:
                    rrlist = []
                    repeat_days = None
                    if not rrule_set:
                        rrule_set = rruleset()
                    if not m.group('delete_secs') == '0':
                        dt_until = epoch + datetime.timedelta(
                            seconds=int(m.group('delete_secs'))
                        )
                        rrlist.append('UNTIL=%s' % dt_until)
                    if not m.group('trigger_secs') == '0':
                        repeat_days = int(m.group('trigger_secs')) / 86400
                        rrlist.append('INTERVAL=%s' % repeat_days)
                    if m.group('yearly') == '1':
                        rrlist.append('FREQ=YEARLY')
                    elif not m.group('monthdaymap') == '0':
                        rrlist.append('FREQ=MONTHLY')
                        monthdaymap = int(m.group('monthdaymap'))
                        daylist = []

                        for i in range(1, 31):
                            if monthdaymap & (1 << i):
                                daylist.append(str(i))

                        # bit 0 is set, so it is the last day of the month
                        if monthdaymap & 1:
                            daylist.append('-1')
                        if daylist:
                            rrlist.append('BYMONTHDAY=%s' % ','.join(daylist))

                    elif not m.group('weekdaymap') == '0':
                        days = []
                        weeks = []
                        weekdaymap = int(m.group('weekdaymap'))
                        for i in range(7):
                            if weekdaymap & (1 << i):
                                days.append(weekday[i])
                        for i in range(8, 14):
                            if weekdaymap & (1 << i):
                                weeks.append(weeknumber[i - 8])
                        if weeks:
                            rrlist.append('FREQ=MONTHLY')
                            if days:
                                rrlist.append('BYDAY=%s' % ','.join(days))
                            if weeks:
                                rrlist.append('BYSETPOS=%s' % ','.join(weeks))
                        else:
                            rrlist.append('FREQ=WEEKLY')
                            if days:
                                rrlist.append('BYDAY=%s' % ','.join(days))
                    else:
                        rrlist.append('FREQ=DAILY')
                    if self.verbose:
                        print "days %s rrlist %s" % ('', ';'.join(rrlist))
                    rrule_set.rrule(rrulestr(';'.join(rrlist)))
            elif line[0] == 'E':
                m = exception_rx.match(line)
                if m:
                    if not rrule_set:
                        rrule_set = rruleset()
                    rrule_set.exdate(datetime.datetime.strptime(
                        '%s' % m.group('date'), '%m/%d/%Y')
                    )
            elif line[0] == 'S':
                s = script_rx.match(line)
                if s:
                    self._uid = s.group('uid')
            elif line[0] == 'G':
                continue
            else:
                m = duration_rx.match(line)
                if m:
                    duration = datetime.timedelta(
                        hours=int(m.group('hours')),
                        minutes=int(m.group('minutes')),
                        seconds=int(m.group('seconds'))
                    )
                    if duration:
                        dt_end = dt_start + duration
        if location:
            self.vevent.add('location').value = location
        if dt_end:
            self.vevent.add('dtend').value = dt_end
        else:
            self.vevent.add('dtend').value = dt_start
        if description:
            self.vevent.add('description').value = ' '.join(description)
        if rrule_set:
            if self.verbose:
                print "plan event %s" % (self.plan)
            self.vevent.rruleset = rrule_set
        if not self._uid:
            # generate a UID and save it in the netplan data
            self._uid = uuid.uuid3(uuid.NAMESPACE_OID,
                                   '%s %s' % (dt_start, ' '.join(description))
                                   )
            self.extra.append('S\t#plan2ics: version=%s uuid=%s hash=%s\n' %
                              (0, self.uid, self.hash))
        return


class dayplan(object):
    calendar = None
    timezone = None
    events = None
    verbose = False

    def __init__(self, input=None, date_threshold_delta=None, verbose=False):
        self.events = []
        self.calendar = vobject.iCalendar()
        self.timezone = PyICU.ICUtzinfo.getDefault()
        tz = self.calendar.add('vtimezone')
        tz.settzinfo(self.timezone)
        self.verbose = verbose
        self.date_threshold_delta = date_threshold_delta
        if date_threshold_delta:
            self.date_threshold = datetime.datetime.now(
            ) - date_threshold_delta
        if input:
            self._load(input)

    def _load(self, fh):
        # split the input file based on the lines that start with a date
        entries = re.split(r'(\d+/\d+/\d+\s+\d+:\d+:\d+)', fh.read())

        # now grab each event. That is the date, and the data after it
        for plan_event in zip(entries[1::2], entries[2::2]):
            vevent = self.calendar.add('vevent')
            pevent = Event(vevent, plan_event, self.verbose)
            vevent.add('uid').value = pevent.uid
            self.events.append(pevent)

            if self.date_threshold_delta:
                if vevent.rruleset:
                    # If this is a repeating event,
                    # and there is no valid date after the threshold date,
                    # remove the event.
                    if not vevent.rruleset.after(self.date_threshold):
                        self.calendar.remove(vevent)
                else:
                    # Check if the end date is after the threshold date.
                    vdtend = datetime.datetime.combine(
                        vevent.dtend.value, datetime.time(0)
                    )
                    dtdiff = datetime.datetime.now() - vdtend
                    if dtdiff > self.date_threshold_delta:
                        # remove the event if it is too far in the past
                        self.calendar.remove(vevent)
            # put all the datetimes into the current timezone
            # even if the object has been removed from the calendar.
            if(isinstance(vevent.dtstart.value, datetime.datetime)):
                vevent.dtstart.value = vevent.dtstart.value.replace(
                    tzinfo=self.timezone
                )
            if(isinstance(vevent.dtend.value, datetime.datetime)):
                vevent.dtend.value = vevent.dtend.value.replace(
                    tzinfo=self.timezone
                )

    def save_plan(self, fh):
        for event in self.events:
            fh.write(event.plan)

    def pprint(self):
        return unicode(self.calendar.serialize().translate(translate_map), 'utf-8')


def main():
    usage = "usage: %prog [options] calendar [calendar2 calendar3...]"
    optparser = optparse.OptionParser(usage=usage)
    optparser.add_option('-v', '--verbose', dest='verbose',
                         action="store_true",
                         default=False,
                         help='print info while running [default: %default]')
    optparser.add_option('-w', '--weeks', dest='weeks',
                         default=None,
                         type="int",
                         help='include events since X weeks in the past.')
    optparser.add_option('-s', '--save', dest='do_save',
                         default=False,
                         action="store_true",
                         help='re-save the plan file after processing.')

    (opts, args) = optparser.parse_args()
    date_threshold_delta = None
    if opts.weeks:
        date_threshold_delta = datetime.timedelta(weeks=opts.weeks)

    for file in args:
        with open(file, mode='r') as fh:
            c = dayplan(fh, date_threshold_delta, opts.verbose)
        print(("%s" % c.pprint()))
        if opts.do_save:
            with open(file, mode='w+') as fh:
                c.save_plan(fh)

if __name__ == '__main__':
    main()
