#!/usr/bin/python

#    upload2davical.py
#    Convert a netplan calendar to ICS and upload into DaviCal
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

from plan2ics import dayplan
import os
from os.path import basename,splitext
import tempfile
import urllib, urllib2
import MultipartPostHandler
import optparse

# class to make required parameters
# from optparse examples/required_1.py
class OptionParser (optparse.OptionParser):
    def check_required (self, opt):
        option = self.get_option(opt)

        # Assumes the option's 'default' is set to None!
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)
 

def submit_ics(url,ical,name,id):
    data = {'path_ics':name, 'ics_file':ical, 'user_no':str(id), 'submit':'Update'}
    urllib2.urlopen(url, data).read()
    
def main():
    usage="usage: %prog [options] calendar [calendar2 calendar3...]"
    optparser = OptionParser(usage=usage)
    optparser.add_option('-u','--username',dest='username',
        default=None,
        help='username for the DaviCal server')
    optparser.add_option('-i','--userid',dest='userid',
        default=None, type='int',
        help='user ID for the DaviCal server')
    optparser.add_option('-p','--password',dest='password',
        default=None,
        help='password for the DaviCal server')
    optparser.add_option('-s','--server',dest='server',
        default='localhost',
        help='name of the DaviCal server [default: %default]')

    (opts,args) = optparser.parse_args()
    optparser.check_required('-u')
    optparser.check_required('-i')
    optparser.check_required('-p')
    top_level_url = "http://" + opts.server
    url=top_level_url + '/usr.php?user_no='+str(opts.userid)+'&edit=1'

    # build opener with HTTPCookieProcessor
    opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(), MultipartPostHandler.MultipartPostHandler )
    urllib2.install_opener( opener )
    
    # assuming the site expects 'user' and 'pass' as query params
    login_form = urllib.urlencode( { 'username': opts.username, 'password': opts.password } )
    
    # perform login with params
    f = opener.open( top_level_url + '/index.php',  login_form )
    f.read()
    f.close()
    
    for file in args:
        calendar = dayplan(file)
        cal_name = splitext(basename(file))[0]

        temp = tempfile.mkstemp(suffix=".html")
        os.write(temp[0], calendar.pprint())
        submit_ics(url,open(temp[1], "rb"),cal_name,opts.userid)
        os.remove(temp[1])

if __name__ == '__main__':
    main()
