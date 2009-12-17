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
import socket
import MultipartPostHandler
import optparse
import datetime
import pytz
from BeautifulSoup import BeautifulSoup

# class to make required parameters
# from optparse examples/required_1.py
class OptionParser (optparse.OptionParser):
    def check_required (self, opt):
        option = self.get_option(opt)

        # Assumes the option's 'default' is set to None!
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)

def log(msg,verbose=True): 
    if verbose:
        print msg

def submit_ics(url,ical,name,id):
    data = {'path_ics':name, 'ics_file':ical, 'user_no':id, 'submit':'Update'}
    urllib2.urlopen(url, data).read()
def login_ics(url,user,passwd):
    # assuming the site expects 'user' and 'pass' as query params
    login_form = urllib.urlencode( { 'username': user, 'password': passwd } )
    # perform login with params
    f = urllib2.urlopen(url,login_form )
    f.read()
    f.close()
def get_userUrl(url):
    soup = BeautifulSoup(urllib2.urlopen(url))
    href = soup.find(text='My Details').parent['href']
    return (href,href.split('=')[1])
def get_lastModified(url,calendar):
    soup = BeautifulSoup(urllib2.urlopen(url))
    try:
        row = soup.find(text=calendar).parent.parent.parent
    except:
        return None
    date = datetime.datetime.strptime(row.findAll('td')[3].contents[0].split('.')[0],'%Y-%m-%d %H:%M:%S')
    #TODO the split() above is throwing away the TZ info, Should grab this and use it properly...
    return date.replace(tzinfo=None)
def get_fileModified(file):
    epoch = datetime.datetime(1970,1,1,tzinfo=pytz.timezone('UTC'))
    statinfo = os.stat(file)
    date = epoch + datetime.timedelta(seconds=statinfo.st_mtime)
    return date.astimezone(TZ).replace(tzinfo=None)
    
def main():
    usage="usage: %prog [options] calendar [calendar2 calendar3...]"
    optparser = OptionParser(usage=usage)
    optparser.add_option('-v','--verbose',dest='verbose',
        action="store_true",
        default=False,
        help='print info while running [default: %default]')        
    optparser.add_option('-u','--username',dest='username',
        default=None,
        help='username for the DaviCal server')
    optparser.add_option('-p','--password',dest='password',
        default=None,
        help='password for the DaviCal server')
    optparser.add_option('-s','--server',dest='server',
        default='localhost',
        help='name of the DaviCal server [default: %default]')
    optparser.add_option('-f','--force',dest='force',
        action="store_true",
        default=False,
        help='force the upload')
    optparser.add_option('-z','--timezone',dest='tz',
        default='Pacific/Auckland',
        help='set the timezone [default: %default]')

    (opts,args) = optparser.parse_args()
    optparser.check_required('-u')
    optparser.check_required('-p')
    top_level_url = "http://" + opts.server

    global TZ
    TZ=pytz.timezone(opts.tz)

    # set a really long socket timeout in seconds
    socket.setdefaulttimeout(None)
    
    # build opener with HTTPCookieProcessor
    opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(), MultipartPostHandler.MultipartPostHandler )
    urllib2.install_opener( opener )

    login_ics(top_level_url + '/index.php', opts.username, opts.password)
    (userUrl, userId) = get_userUrl(top_level_url + '/users.php')
    editUrl=top_level_url + userUrl +'&edit=1'

    log('Logged into server %s. User is %s, Id is %s' %(opts.server,opts.username,userId),verbose=opts.verbose)

    for file in args:
        cal_name = splitext(basename(file))[0]
        cal_modified = get_lastModified(top_level_url + userUrl, '/'+opts.username+'/'+cal_name+'/')
        file_modified = get_fileModified(file)
        if (not opts.force) and (cal_modified != None) and (file_modified <= cal_modified):   # skip the update if davical was updated more recently than the file
            log('Skipping file %s based on modifications times. File: %s  DaviCal: %s' %(file,file_modified,cal_modified),verbose=opts.verbose)
            continue
        log('Processing file %s' %(file),verbose=opts.verbose)
        calendar = dayplan(file)

        temp = tempfile.mkstemp(suffix=".html")
        os.write(temp[0], calendar.pprint())
        submit_ics(editUrl,open(temp[1], "rb"),cal_name,userId)
        os.remove(temp[1])

if __name__ == '__main__':
    main()
