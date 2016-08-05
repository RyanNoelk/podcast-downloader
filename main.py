#!/usr/bin/env python

# PodGrab - A Python command line audio/video podcast downloader for RSS XML feeds.
# Supported RSS item file types: MP3, M4V, OGG, FLV, MP4, MPG/MPEG, WMA, WMV, WEBM
# Version: 1.1.1 - 25/08/2011
# Jonathan Baker 
# jon@the-node.org (http://the-node.org)
# http://joshua14.homelinux.org/downloads/PodGrab.py

# Do with this code what you will, it's "open source". As a courtesy,
# I would appreciate credit if you base your code on mine. If you find
# a bug or think the code sucks balls, please let me know :-) 

# Outstanding issues:-
# - Video podcasts which which are not direct URLs and are modified by PodGrab
#   in order to be grabbed won't display their size as the filenames haven't 
#   been stripped of their garbage URL info yet. It'll say 0 bytes, but don't 
#   worry, they've downloaded. 


import sys
import argparse
import urllib2
import xml.dom.minidom
import datetime
from time import gmtime, strftime, strptime, mktime
import shutil
import smtplib
import httplib
import platform
import traceback
import socket

from code.settings import *
from code.db import *


def main(argv):
    mode = MODE_NONE
    has_error = 0
    num_podcasts = 0
    error_string = ""
    feed_url = ""
    feed_name = ""
    mail_address = ""
    message = ""
    mail = ""
    current_directory = os.path.realpath(os.path.dirname(sys.argv[0]))
    download_directory = DOWNLOAD_DIRECTORY
    global total_items
    global total_size
    total_items = 0
    total_size = 0
    data = ""

    parser = argparse.ArgumentParser(description='A command line Podcast downloader for RSS XML feeds')
    parser.add_argument('-s', '--subscribe', action="store", dest="sub_feed_url", help='Subscribe to the following XML feed and download latest podcast')
    parser.add_argument('-d', '--download', action="store", dest="dl_feed_url", help='Bulk download all podcasts in the following XML feed or file')
    parser.add_argument('-un', '--unsubscribe', action="store", dest="unsub_url", help='Unsubscribe from the following Podcast feed')
    parser.add_argument('-ma', '--mail-add', action="store", dest="mail_address_add", help='Add a mail address to mail subscription updates to')
    parser.add_argument('-md', '--mail-delete', action="store", dest="mail_address_delete", help='Delete a mail address')

    parser.add_argument('-l', '--list', action="store_const", const="ALL", dest="list_subs", help='Lists current Podcast subscriptions')
    parser.add_argument('-u', '--update', action="store_const", const="UPDATE", dest="update_subs", help='Updates all current Podcast subscriptions')
    parser.add_argument('-ml', '--mail-list', action="store_const", const="MAIL", dest="list_mail", help='Lists all current mail addresses')

    arguments = parser.parse_args()
    
    if arguments.sub_feed_url:
        feed_url = arguments.sub_feed_url
        data = open_datasource(feed_url)
        if not data:
            error_string = "Not a valid XML file or URL feed!"
            has_error = 1
        else:
            print "XML data source opened\n"
            mode = MODE_SUBSCRIBE
    elif arguments.dl_feed_url:
        feed_url = arguments.dl_feed_url
        data = open_datasource(feed_url)
        if not data:
            error_string = "Not a valid XML file or URL feed!"
            has_error = 1 
        else:
            print "XML data source opened\n"
            mode = MODE_DOWNLOAD
    elif arguments.unsub_url:
        feed_url = arguments.unsub_url
        mode = MODE_UNSUBSCRIBE
    elif arguments.list_subs:
        mode = MODE_LIST
    elif arguments.update_subs:
        mode = MODE_UPDATE
    elif arguments.mail_address_add:
        mail_address = arguments.mail_address_add
        mode = MODE_MAIL_ADD
    elif arguments.mail_address_delete:
        mail_address = arguments.mail_address_delete
        mode = MODE_MAIL_DELETE
    elif arguments.list_mail:
        mode = MODE_MAIL_LIST
    else:
        error_string = "No Arguments supplied - for usage run 'PodGrab.py -h'"
        has_error = 1
    print "Default encoding: " + sys.getdefaultencoding()
    todays_date = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
    print "Current Directory: ", current_directory
    if does_database_exist(current_directory):
        connection = connect_database(current_directory)
        if not connection:
            error_string = "Could not connect to PodGrab database file!"
            has_error = 1
        else:
            cursor = connection.cursor()
    else:
        print "PodGrab database missing. Creating..."
        connection = connect_database(current_directory)
        if not connection:
            error_string = "Could not create PodGrab database file!"
            has_error = 1
        else:
            print "PodGrab database created"
            cursor = connection.cursor()
            setup_database(cursor, connection)
            print "Database setup complete"
    if not os.path.exists(download_directory):
        print download_directory
        print "Podcast download directory is missing. Creating..."
        try:
            os.mkdir(download_directory)
            print "Download directory '" + download_directory + "' created"
        except OSError:
            error_string = "Could not create podcast download sub-directory!"
            has_error = 1
    else:
        print "Download directory exists: '" + download_directory + "'" 
    if not has_error:
        if mode == MODE_UNSUBSCRIBE:
            feed_name = get_name_from_feed(cursor, connection, feed_url)
            if feed_name == "None":
                print "Feed does not exist in the database! Skipping..."
            else:
                feed_name = clean_string(feed_name)
                channel_directory = download_directory + os.sep + feed_name
                print "Deleting '" + channel_directory + "'..."
                delete_subscription(cursor, connection, feed_url)
                try :
                    shutil.rmtree(channel_directory)
                except OSError:
                    print "Subscription directory has not been found - it might have been manually deleted" 
                print "Subscription '" + feed_name + "' removed"
        elif mode == MODE_LIST:
            print "Listing current podcast subscriptions...\n"
            list_subscriptions(cursor, connection)
        elif mode == MODE_UPDATE:
            print "Updating all podcast subscriptions..."
            subs = get_subscriptions(cursor, connection)
            for sub in subs:
                feed_name = sub[0]
                feed_url = sub[1]
                feed_name.encode('utf-8')
                feed_url.encode('utf-8')
                print "Feed for subscription: '" + feed_name + "' from '" + feed_url + "' is updating..."
                data = open_datasource(feed_url)
                if not data:
                    print "'" + feed_url + "' for '" + feed_name.encode("utf-8") + "' is not a valid feed URL!"
                else:
                    message = iterate_feed(data, mode, download_directory, todays_date, cursor, connection, feed_url)
                    print message
                    mail += message
            mail = mail + "\n\n" + str(total_items) + " podcasts totalling " + str(total_size) + " bytes have been downloaded."
            if has_mail_users(cursor, connection):
                print "Have e-mail address(es) - attempting e-mail..."
                mail_updates(cursor, connection, mail, str(total_items))
        elif mode == MODE_DOWNLOAD or mode == MODE_SUBSCRIBE:
            print iterate_feed(data, mode, download_directory, todays_date, cursor, connection, feed_url)
        elif mode == MODE_MAIL_ADD:
            add_mail_user(cursor, connection, mail_address)
            print "E-Mail address: " + mail_address + " has been added"
        elif mode == MODE_MAIL_DELETE:
            delete_mail_user(cursor, connection, mail_address)
            print "E-Mail address: " + mail_address + " has been deleted"
        elif mode == MODE_MAIL_LIST:
            list_mail_addresses(cursor, connection)
    else:
        print "Sorry, there was some sort of error: '" + error_string + "'\nExiting...\n"
        if connection:
            connection.close()


def open_datasource(xml_url):
    try:
        response = urllib2.urlopen(xml_url)
    except ValueError:
        try:
            response = open(xml_url,'r')
        except ValueError:
            print "ERROR - Invalid feed!"
            response = False
        except urllib2.URLError:
            print "ERROR - Connection problems. Please try again later"
            response = False
        except httplib.IncompleteRead:
            print "ERROR - Incomplete data read. Please try again later"
            response = False
    if response != False:
        return response.read()
    else:
        return response


def iterate_feed(data, mode, download_dir, today, cur, conn, feed):
    print "Iterating feed..."
    message = ""
    try:
        xml_data = xml.dom.minidom.parseString(data)
        for channel in xml_data.getElementsByTagName('channel'):
            channel_title = channel.getElementsByTagName('title')[0].firstChild.data
            channel_link = channel.getElementsByTagName('link')[0].firstChild.data
            print "Channel Title: ===" + channel_title + "==="
            print "Channel Link: " + channel_link
            channel_title = clean_string(channel_title)
            channel_directory = download_dir + os.sep + channel_title
            if not os.path.exists(channel_directory):
                os.makedirs(channel_directory)
            print "Current Date: ", today
            if mode == MODE_DOWNLOAD:
                print "Bulk download. Processing..."
                num_podcasts = iterate_channel(channel, today, mode, cur, conn, feed, channel_directory)
                print "\n", num_podcasts, "have been downloaded"
            elif mode == MODE_SUBSCRIBE:
                print "Feed to subscribe to: " + feed + ". Checking for database duplicate..."
                if not does_sub_exist(cur, conn, feed):
                    print "Subscribe. Processing..."
                    num_podcasts = iterate_channel(channel, today, mode, cur, conn, feed, channel_directory)
                    print "\n", num_podcasts, "have been downloaded from your subscription"
                else:
                    print "Subscription already exists! Skipping..."
            elif mode == MODE_UPDATE:
                print "Updating RSS feeds. Processing..."
                num_podcasts = iterate_channel(channel, today, mode, cur, conn, feed, channel_directory)
                message += str(num_podcasts) + " have been downloaded from your subscription: '" + channel_title + "'\n"
    except xml.parsers.expat.ExpatError:
        print "ERROR - Malformed XML syntax in feed. Skipping..."
        message += "0 podcasts have been downloaded from this feed due to RSS syntax problems. Please try again later"
    except UnicodeEncodeError:
        print "ERROR - Unicoce encoding error in string. Cannot convert to ASCII. Skipping..."
        message += "0 podcasts have been downloaded from this feed due to RSS syntax problems. Please try again later"
    return message


def clean_string(str):
    new_string = str
    if new_string.startswith("-"):
        new_string = new_string.lstrip("-")
    if new_string.endswith("-"):
        new_string = new_string.rstrip("-")
    new_string_final = ''
    for c in new_string:
        if c.isalnum() or c == "-" or c == "." or c.isspace():
            new_string_final = new_string_final + ''.join(c)
        new_string_final = new_string_final.strip()
        new_string_final = new_string_final.replace(' ','-')
        new_string_final = new_string_final.replace('---','-')
        new_string_final = new_string_final.replace('--','-')
    return new_string_final

def write_podcast(item, chan_loc, date, type):
    (item_path, item_file_name) = os.path.split(item)
    if len(item_file_name) > 50:
        item_file_name = item_file_name[:50]
    today = datetime.date.today()
    item_file_name = today.strftime("%Y/%m/%d") + item_file_name
    local_file = chan_loc + os.sep + clean_string(item_file_name)
    if type == "video/quicktime" or type == "audio/mp4" or type == "video/mp4":
        if not local_file.endswith(".mp4"):
            local_file = local_file + ".mp4"
    elif type == "video/mpeg":
        if not local_file.endswith(".mpg"):
            local_file = local_file + ".mpg"
    elif type == "video/x-flv":
        if not local_file.endswith(".flv"):
            local_file = local_file + ".flv"
    elif type == "video/x-ms-wmv":
        if not local_file.endswith(".wmv"):
            local_file = local_file + ".wmv"
    elif type == "video/webm" or type == "audio/webm":
        if not local_file.endswith(".webm"):
            local_file = local_file + ".webm"
    elif type == "audio/mpeg":
        if not local_file.endswith(".mp3"):
            local_file = local_file + ".mp3"
    elif type == "audio/ogg" or type == "video/ogg" or type == "audio/vorbis":
        if not local_file.endswith(".ogg"):
            local_file = local_file + ".ogg"
    elif type == "audio/x-ms-wma" or type == "audio/x-ms-wax":
        if not local_file.endswith(".wma"):
            local_file = local_file + ".wma"    
    if os.path.exists(local_file):
        return 0
    else:
        print "\nDownloading " + item_file_name + " which was published on " + date
        try:
            item_file = urllib2.urlopen(item)
            output = open(local_file, 'wb')
            output.write(item_file.read())
            output.close()
            print "Podcast: ", item, " downloaded to: ", local_file
            return 1
        except urllib2.URLError as e:
            print "ERROR - Could not write item to file: ", e
        except socket.error as e:
            print "ERROR - Socket reset by peer: ", e


def does_database_exist(curr_loc):
    db_name = "PodGrab.db"
    if os.path.exists(curr_loc + os.sep + db_name):
        return 1
    else:
        return 0


def mail_updates(cur, conn, mess, num_updates):
    addresses = get_mail_users(cur, conn)
    for address in addresses:
        try:
            subject_line = "PodGrab Update"
            if int(num_updates) > 0:
                subject_line += " - NEW updates!"
            else:
                subject_line += " - nothing new..."
            mail('localhost', 'podgrab@' + platform.node(), address[0], subject_line, mess)
            print "Successfully sent podcast updates e-mail to: " + address[0]
        except smtplib.SMTPException:
            traceback.print_exc()
            print "Could not send podcast updates e-mail to: " + address[0]


def mail(server_url=None, sender='', to='', subject='', text=''):
    headers = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % (sender, to, subject)
    message = headers + text
    mail_server = smtplib.SMTP(server_url)
    mail_server.sendmail(sender, to, message)
    mail_server.quit()  



def iterate_channel(chan, today, mode, cur, conn, feed, chan_dir):
    global total_items
    global total_size
    NUM_MAX_DOWNLOADS = 4
    saved = 0
    num = 0
    size = 0
    last_ep = "NULL"
    print "Iterating channel..."
    if mode == MODE_SUBSCRIBE:
        print "Feed: " + feed
        if does_sub_exist(cur, conn, feed):
            print "Podcast subscription exists - getting latest podcast"
            last_ep = get_last_subscription_downloaded(cur, conn, feed)
        else:
            print "Podcast subscription is new - getting previous podcast"
            insert_subscription(cur, conn, chan.getElementsByTagName('title')[0].firstChild.data, feed)
    for item in chan.getElementsByTagName('item'):
        try:
            item_title = item.getElementsByTagName('title')[0].firstChild.data
            item_date = item.getElementsByTagName('pubDate')[0].firstChild.data
            item_file = item.getElementsByTagName('enclosure')[0].getAttribute('url')
            item_size = item.getElementsByTagName('enclosure')[0].getAttribute('length')
            item_type = item.getElementsByTagName('enclosure')[0].getAttribute('type')
            struct_time_today = strptime(today, "%a, %d %b %Y %H:%M:%S")
            try:
                struct_time_item = strptime(fix_date(item_date), "%a, %d %b %Y %H:%M:%S")
                has_error = 0   
            except TypeError:
                has_error = 1
            except ValueError:
                has_error = 1
            if mode == MODE_DOWNLOAD:
                if not has_error:
                    saved = write_podcast(item_file, chan_dir, item_date, item_type)
                else:
                    saved = 0
                    print "This item has a badly formatted date. Cannot download!"
                if saved > 0:
                    print "\nTitle: " + item_title
                    print "Date:  " + item_date
                    print "File:  " + item_file
                    print "Size:  " + item_size + " bytes"
                    print "Downloading " + item_file + "..."
                    num = num + saved
                size = size + int(item_size)
                total_size += size
                total_items += num
            elif mode == MODE_SUBSCRIBE or mode == MODE_UPDATE:
                if (last_ep == "NULL"):
                    last_ep = fix_date(item_date)
                    update_subscription(cur, conn, feed, last_ep)
                try:
                    struct_last_ep = strptime(last_ep, "%a, %d %b %Y %H:%M:%S")
                    has_error = 0
                except TypeError:
                    has_error = 1
                    print "This item has a badly formatted date. Cannot download!"
                except ValueError:
                    has_error = 1
                    print "This item has a badly formatted date. Cannot download!"
                if not has_error:
                    if mktime(struct_time_item) <= mktime(struct_time_today) and mktime(struct_time_item) >= mktime(struct_last_ep):
                        saved = write_podcast(item_file, chan_dir, item_date, item_type)
                        if saved > 0:
                            print "\nTitle: " + item_title
                            print "Date:  " + item_date
                            print "File:  " + item_file
                            print "Size:  " + item_size + " bytes"
                            print "Type:  " + item_type
                            update_subscription(cur, conn, feed, fix_date(item_date))
                            num = num + saved
                            size = size + int(item_size)
                            total_size += size
                            total_items += num
                        if (num >= NUM_MAX_DOWNLOADS):
                            print "Maximum session download of " + str(NUM_MAX_DOWNLOADS) + " podcasts has been reached. Exiting."
                            break
        except IndexError, e:
            #traceback.print_exc()
            print "This RSS item has no downloadable URL link for the podcast for '" + item_title  + "'. Skipping..."
        except AttributeError, e:
            print "This RSS item appears to have no data attribute for the podcast '" + item_title + "'. Skipping..." 
    return str(num) + " podcasts totalling " + str(size) + " bytes"


def fix_date(date):
    new_date = ""
    split_array = date.split(' ')
    for i in range(0,5):
        new_date = new_date + split_array[i] + " "
    return new_date.rstrip()



if __name__ == "__main__":
    main(sys.argv[1:])