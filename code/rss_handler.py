#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2
import xml.dom.minidom
import datetime
import httplib
import socket
import os
import shutil
from slugify import slugify
from operator import itemgetter

import settings
from code.db_handler import DbHandler
from mailer import mail_updates


class RssHandler:

    def __init__(self, feed=None, db=None):
        self.feed = feed
        if db:
            self.db = db
        else:
            self.db = DbHandler()

        if not os.path.exists(settings.DOWNLOAD_DIRECTORY):
            print "Podcast download directory is missing. Creating: '" + settings.DOWNLOAD_DIRECTORY + "'"
            try:
                os.mkdir(settings.DOWNLOAD_DIRECTORY)
                print "Download directory '" + settings.DOWNLOAD_DIRECTORY + "' created"
            except OSError:
                exit("Could not create podcast download sub-directory!")
        else:
            print "Download directory exists: '" + settings.DOWNLOAD_DIRECTORY + "'"

    def subscribe(self):
        data = self._open_data_source()
        if data is None or not data:
            exit("Not a valid XML file or URL feed!")
        else:
            print "XML data source opened\n"
        print self._iterate_feed(data)

    def unsubscribe(self):
        feed_name = self.db.get_name_from_feed(self.feed)
        if feed_name == "None":
            print "Feed does not exist in the database! Skipping..."
        else:
            feed_name = slugify(feed_name)
            channel_directory = settings.DOWNLOAD_DIRECTORY + os.sep + feed_name
            print "Deleting '" + channel_directory + "'..."
            self.db.delete_subscription(self.feed)
            try:
                shutil.rmtree(channel_directory)
            except OSError:
                print "Subscription directory has not been found - it might have been manually deleted"
            print "Subscription '" + feed_name + "' removed"

    def update(self):
        message = ''
        print "Updating all podcast subscriptions..."
        subs = self.db.get_subscriptions()
        for sub in subs:
            channel_name = sub[0]
            self.feed = sub[1]
            channel_name.encode('utf-8')
            self.feed.encode('utf-8')
            print "Feed for subscription: '" + channel_name + "' from '" + self.feed + "' is updating..."
            data = self._open_data_source()
            if not data:
                print "'" + channel_name + "' for '" + self.feed.encode("utf-8") + "' is not a valid feed URL!"
            else:
                message += self._iterate_feed(data)
                print message
        if self.db.has_mail_users():
            print "Have e-mail address(es) - attempting e-mail..."
            mail_updates(message, self.db.get_mail_users())

    def _iterate_feed(self, data):
        message = ''
        print "Iterating feed..."
        try:
            xml_data = xml.dom.minidom.parse(data)
            for channel in xml_data.getElementsByTagName('channel'):
                channel_title = channel.getElementsByTagName('title')[0].firstChild.data
                channel_link = channel.getElementsByTagName('link')[0].firstChild.data
                print "Channel Title: ===" + channel_title + "==="
                print "Channel Link: " + channel_link
                channel_title = slugify(channel_title)
                channel_directory = settings.DOWNLOAD_DIRECTORY + os.sep + channel_title
                if not os.path.exists(channel_directory):
                    os.makedirs(channel_directory)
                print "Updating RSS feeds. Processing..."
                podcasts = self._iterate_channel(channel, channel_directory)
                self._save_podcasts(podcasts)
                self._delete_old_podcasts(channel_directory)
                message = str(len(podcasts)) + " have been downloaded from your subscription: '" + channel_title + "'\n"
        except xml.parsers.expat.ExpatError:
            print "ERROR - Malformed XML syntax in feed. Skipping..."
            message = "0 podcasts have been downloaded from this feed due to RSS syntax problems. Please try again later"
        except UnicodeEncodeError:
            print "ERROR - Unicoce encoding error in string. Cannot convert to ASCII. Skipping..."
            message = "0 podcasts have been downloaded from this feed due to RSS syntax problems. Please try again later"
        return message

    def _iterate_channel(self, channel, channel_dir):
        num = 0
        last_ep_date = 0
        podcasts = []
        print "Iterating channel..."
        if self.db.does_sub_exist(self.feed):
            last_ep_date = self.db.get_last_subscription_downloaded(self.feed)
        else:
            self.db.insert_subscription(
                slugify(channel.getElementsByTagName('title')[0].firstChild.data),
                self.feed
            )
        for item in channel.getElementsByTagName('item'):
            try:
                try:
                    item_time = self._date_to_int(
                        item.getElementsByTagName('pubDate')[0].firstChild.data
                    )
                except (TypeError, ValueError):
                    item_time = 0

                if item_time > last_ep_date and num < settings.NUMBER_OF_PODCASTS_TO_KEEP:
                    podcasts.append({
                        'title': item.getElementsByTagName('title')[0].firstChild.data,
                        'file':  item.getElementsByTagName('enclosure')[0].getAttribute('url'),
                        'dir':   channel_dir,
                        'type':  item.getElementsByTagName('enclosure')[0].getAttribute('type'),
                        'size':  item.getElementsByTagName('enclosure')[0].getAttribute('length'),
                        'date':  item_time
                    })
                    print item.getElementsByTagName('title')[0].firstChild.data
                    num += 1
                else:
                    return podcasts
            except (TypeError, ValueError):
                print "This item has a badly formatted date. Cannot download!"
        return podcasts

    def _open_data_source(self):
        try:
            response = urllib2.urlopen(self.feed)
        except ValueError:
            try:
                response = open(self.feed, 'r')
            except ValueError:
                print "ERROR - Invalid feed!"
                return None
            except urllib2.URLError:
                print "ERROR - Connection problems. Please try again later"
                return None
            except httplib.IncompleteRead:
                print "ERROR - Incomplete data read. Please try again later"
                return None
        if not response:
            return response.read()
        else:
            return response

    def _save_podcasts(self, podcasts):
        extension_map = {
            'video/quicktime': '.mp4',
            'audio/mp4': '.mp4',
            'video/mp4': '.mp4',
            'video/mpeg': '.mpg',
            'video/x-flv': '.flv',
            'video/x-ms-wmv': '.wmv',
            'video/webm': '.webm',
            'audio/webm': '.webm',
            'audio/mpeg': '.mp3',
            'audio/ogg': '.ogg',
            'video/ogg': '.ogg',
            'audio/vorbis': '.ogg',
            'audio/x-ms-wma': '.wma',
            'audio/x-ms-wax': '.wma',
        }
        if podcasts:
            podcasts = sorted(podcasts, key=itemgetter('date'))

            for podcast in podcasts:
                (item_path, item_file_name) = os.path.split(podcast['file'])
                if len(item_file_name) > 50:
                    item_file_name = item_file_name[:50]
                today = datetime.date.today()
                item_file_name = today.strftime("%Y/%m/%d") + item_file_name
                local_file = podcast['dir'] + os.sep + slugify(item_file_name)
                if extension_map[podcast['type']]:
                    if not local_file.endswith(extension_map[podcast['type']]):
                        local_file += extension_map[podcast['type']]
                if not os.path.exists(local_file):
                    print "\nDownloading " + item_file_name
                    try:
                        item_file = urllib2.urlopen(podcast['file'])
                        with open(local_file, 'wb') as output:
                            output.write(item_file.read())
                        print "Podcast: ", podcast['file'], " downloaded to: ", local_file
                    except urllib2.URLError as e:
                        print "ERROR - Could not write item to file: ", e
                    except socket.error as e:
                        print "ERROR - Socket reset by peer: ", e
            print podcasts
            self.db.update_subscription(self.feed, podcasts[-1]['date'])

    def _delete_old_podcasts(self, channel_dir):
        os.chdir(channel_dir)
        files = sorted(os.listdir(os.getcwd()), key=os.path.getmtime)
        if len(files) <= settings.NUMBER_OF_PODCASTS_TO_KEEP:
            return
        for old_file in files[:settings.NUMBER_OF_PODCASTS_TO_KEEP-1]:
            os.remove(old_file)

    def _date_to_int(self, date):
        new_date = ""
        split_array = date.split(' ')
        for i in range(0, 5):
            new_date = new_date + split_array[i] + " "
        return int(datetime.datetime.strptime(new_date[:-1], "%a, %d %b %Y %H:%M:%S").strftime('%s'))

    def _int_to_date(self, date):
        return datetime.datetime.fromtimestamp(date).strftime("%a, %d %b %Y %H:%M:%S")
