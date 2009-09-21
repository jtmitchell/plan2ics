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


import sys, re
import vobject
import datetime
from dateutil.rrule import rruleset, rrulestr
from string import maketrans

datetime_rx = re.compile(r'(?P<date>\d+/\d+/\d+)\s+(?P<time>\d+:\d+:\d+)')
duration_rx = re.compile(r'\s+(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)')
exception_rx = re.compile(r'E\s+(?P<date>\d+/\d+/\d+)')
repeat_rx = re.compile(r'R\s+(?P<trigger_secs>\d+)\s+(?P<delete_secs>\d+)\s+(?P<weekdaymap>\d+)\s+(?P<monthdaymap>\d+)\s+(?P<yearly>\d)')
note_rx = re.compile(r'N\s+(?P<message>.*)$')
message_rx = re.compile(r'M\s+(?P<message>.*)$')
script_rx = re.compile(r'S\s+')
groupmtg_rx = re.compile(r'G\s+')
    
epoch = datetime.date(1970,1,1)
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
translate_map = maketrans('\xa0',' ')

class dayplan(object):
    calendar = None
    def __init__(self,input=None):
        self.calendar = vobject.iCalendar()
        if input:
            self._load(input)

    def _load(self,fh):
        if isinstance(fh,str):
            fh = open(fh,mode='r')
        entries = re.split(r'(\d+/\d+/\d+\s+\d+:\d+:\d+)',fh.read())   # split the input file based on the lines that start with a date
        for event in zip(entries[1::2],entries[2::2]):      # now grab each event. That is the date, and the data after it
            vevent = self.calendar.add('vevent')
            self._load_event(vevent,event)

    def _load_event(self,vevent,event):
        dt = datetime_rx.match(event[0])
        dt_start = None
        dt_end = None
        dt_until = None
        time = dt.group('time')
        if time == '99:99:99':
            # there is no alarm trigger time
            # I will treat these as transparent, all-day events
            dt_start = datetime.datetime.strptime('%s' % dt.group('date'),'%m/%d/%Y').date()
            vevent.add('dtstart').value = dt_start
            dt_end = dt_start + one_day
            vevent.add('transp').value = 'TRANSPARENT'
        else:
            # we have a trigger time, and will use it for the end time until something better comes along
            dt_start = datetime.datetime.strptime('%s %s' % (dt.group('date'), time),'%m/%d/%Y %H:%M:%S')
            vevent.add('dtstart').value = dt_start
            vevent.add('transp').value = 'OPAQUE'
        description = []
        rrule_set = None
        for line in re.split(r'\n',event[1]):
            if not line:
                continue
            if line[0] == 'N':
                m = note_rx.match(line)
                if m:
                    vevent.add('summary').value = m.group('message')
            elif line[0] == 'M':
                m = message_rx.match(line)
                if m:
                    description.append(m.group('message'))
            elif line[0] == 'R':
                m = repeat_rx.match(line)
                if m:
                    rrlist = []
                    repeat_days = None
                    if not rrule_set:
                        rrule_set = rruleset()
                    if not m.group('delete_secs') == '0':
                        dt_until = epoch + datetime.timedelta(seconds=int(m.group('delete_secs')))
                        rrlist.append('UNTIL=%s' % dt_until)
                    if not m.group('trigger_secs') == '0':
                        repeat_days = int(m.group('trigger_secs')) / 86400
                        rrlist.append('INTERVAL=%s' % repeat_days)
                    if m.group('yearly') == '1':
                        rrlist.append('FREQ=YEARLY')
                    elif not m.group('monthdaymap') == '0':
                        rrlist.append('FREQ=MONTHLY')
                        map = int(m.group('monthdaymap'))
                        daylist = []
                        for i in range(1,31):
                            if map & (1 << i):
                                daylist.append(str(i))
                        if map & 1:     # bit 0 is set, so it is the last day of the month
                            daylist.append('-1')
                        if daylist:
                            rrlist.append('BYMONTHDAY=%s' % ','.join(daylist))
                    elif not m.group('weekdaymap') == '0':
                        days = []
                        weeks = []
                        map = int(m.group('weekdaymap'))
                        for i in range(7):
                            if map & (1 << i):
                                days.append(weekday[i])
                        for i in range(8,14):
                            if map & (1 << i):
                                weeks.append(weeknumber[i-8])
                        if weeks:
                            rrlist.append('FREQ=MONTHLY')
                            daylist = ['%s%s' %(n,d) for n in weeks for d in days]
                            if daylist:
                                rrlist.append('BYDAY=%s' % ','.join(daylist))
                        else:
                            rrlist.append('FREQ=WEEKLY')
                            if days:
                                rrlist.append('BYDAY=%s' % ','.join(days))
                    else:
                        rrlist.append('FREQ=DAILY')
                    rrule_set.rrule(rrulestr(';'.join(rrlist)))
#                    print rrule_set
            elif line[0] == 'E':
                m = exception_rx.match(line)
                if m:
                    if not rrule_set:
                        rrule_set = rruleset()
                    rrule_set.exdate(datetime.datetime.strptime('%s' % m.group('date'),'%m/%d/%Y'))
            elif line[0] == 'S':
                continue
            elif line[0] == 'G':
                continue
            else:
                m = duration_rx.match(line)
                if m:
                    duration = datetime.timedelta(hours=int(m.group('hours')),minutes=int(m.group('minutes')),seconds=int(m.group('seconds')))
                    if duration:
                        dt_end = dt_start + duration
        if dt_end:
            vevent.add('dtend').value = dt_end
        else:
            vevent.add('dtend').value = dt_start            
        if description:
            vevent.add('description').value = ' '.join(description)
        if rrule_set:
            vevent.rruleset = rrule_set

    def pprint(self):
        return unicode(self.calendar.serialize().translate(translate_map),'utf-8')
    
def main():
    for file in sys.argv[1:]:
        c = dayplan(file)
        print "%s" % c.pprint()

if __name__ == '__main__':
    main()