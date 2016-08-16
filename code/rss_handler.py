#!/usr/bin/env python

import urllib2
import xml.dom.minidom
import datetime
from time import strptime, mktime
import httplib
import socket
import settings

from code.settings import *
from code.db_handler import *


def open_datasource(xml_url):
    try:
        response = urllib2.urlopen(xml_url)
    except ValueError:
        try:
            response = open(xml_url, 'r')
        except ValueError:
            print "ERROR - Invalid feed!"
            response = False
        except urllib2.URLError:
            print "ERROR - Connection problems. Please try again later"
            response = False
        except httplib.IncompleteRead:
            print "ERROR - Incomplete data read. Please try again later"
            response = False
    if not response:
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
            if mode == MODE_SUBSCRIBE:
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


def iterate_channel(chan, today, mode, cur, conn, feed, chan_dir):
    total_items = 0
    total_size = 0
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
            except TypeError:
                pass
            except ValueError:
                pass
            if mode == MODE_SUBSCRIBE or mode == MODE_UPDATE:
                if last_ep == "NULL":
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
                    if mktime(struct_time_item) <= mktime(struct_time_today) \
                            and mktime(struct_time_item) >= mktime(struct_last_ep):
                        saved = write_podcast(item_file, chan_dir, item_date, item_type)
                        if saved > 0:
                            print "\nTitle: " + item_title
                            print "Date:  " + item_date
                            print "File:  " + item_file
                            print "Size:  " + item_size + " bytes"
                            print "Type:  " + item_type
                            update_subscription(cur, conn, feed, fix_date(item_date))
                            num += saved
                            size += int(item_size)
                            total_size += size
                            total_items += num
                        if num >= settings.NUMBER_OF_PODCASTS_TO_KEEP:
                            print "Maximum session download of " \
                                  + str(settings.NUMBER_OF_PODCASTS_TO_KEEP) \
                                  + " podcasts has been reached. Exiting."
                            break
        except IndexError, e:
            # traceback.print_exc()
            print "This RSS item has no downloadable URL link for the podcast for '" \
                  + item_title + "'. Skipping..."
        except AttributeError, e:
            print "This RSS item appears to have no data attribute for the podcast '" \
                  + item_title + "'. Skipping..."
    return str(num) + " podcasts totalling " + str(size) + " bytes"


def clean_string(str):
    new_string = str
    if new_string.startswith("-"):
        new_string = new_string.lstrip("-")
    if new_string.endswith("-"):
        new_string = new_string.rstrip("-")
    new_string_final = ''
    for c in new_string:
        if c.isalnum() or c == "-" or c == "." or c.isspace():
            new_string_final += ''.join(c)
        new_string_final = new_string_final.strip()
        new_string_final = new_string_final.replace(' ', '-')
        new_string_final = new_string_final.replace('---', '-')
        new_string_final = new_string_final.replace('--', '-')
    return new_string_final


def fix_date(date):
    new_date = ""
    split_array = date.split(' ')
    for i in range(0, 5):
        new_date = new_date + split_array[i] + " "
    return new_date.rstrip()


def write_podcast(item, chan_loc, date, type):
    (item_path, item_file_name) = os.path.split(item)
    if len(item_file_name) > 50:
        item_file_name = item_file_name[:50]
    today = datetime.date.today()
    item_file_name = today.strftime("%Y/%m/%d") + item_file_name
    local_file = chan_loc + os.sep + clean_string(item_file_name)
    if type == "video/quicktime" or type == "audio/mp4" or type == "video/mp4":
        if not local_file.endswith(".mp4"):
            local_file += ".mp4"
    elif type == "video/mpeg":
        if not local_file.endswith(".mpg"):
            local_file += ".mpg"
    elif type == "video/x-flv":
        if not local_file.endswith(".flv"):
            local_file += ".flv"
    elif type == "video/x-ms-wmv":
        if not local_file.endswith(".wmv"):
            local_file += ".wmv"
    elif type == "video/webm" or type == "audio/webm":
        if not local_file.endswith(".webm"):
            local_file += ".webm"
    elif type == "audio/mpeg":
        if not local_file.endswith(".mp3"):
            local_file += ".mp3"
    elif type == "audio/ogg" or type == "video/ogg" or type == "audio/vorbis":
        if not local_file.endswith(".ogg"):
            local_file += ".ogg"
    elif type == "audio/x-ms-wma" or type == "audio/x-ms-wax":
        if not local_file.endswith(".wma"):
            local_file += ".wma"
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
