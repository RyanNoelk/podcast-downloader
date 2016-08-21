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
        """
        Setup the RSS handler.
        :param feed: URL to the RSS feed
        :param db: DB class object
        """
        self.feed = feed
        if db:
            self.db = db
        else:
            self.db = DbHandler()

        # Create the base DOWNLOAD_DIRECTORY as found in settings if it has not been created yet.
        if not os.path.exists(settings.DOWNLOAD_DIRECTORY):
            print "Podcast download directory is missing. Creating: '" + settings.DOWNLOAD_DIRECTORY + "'"
            try:
                os.mkdir(settings.DOWNLOAD_DIRECTORY)
                print "Download directory '" + settings.DOWNLOAD_DIRECTORY + "' created"
            except OSError:
                exit("Could not create podcast download sub-directory!")

    def subscribe(self):
        """
        Subscribe to a podcast. Then download the first x number of episodes as defined in the settings.
        """
        data = self._open_data_source()
        if data is None or not data:
            exit("Not a valid XML file or URL feed!")
        podcasts = self._iterate_feed(data)
        if podcasts:
            self._save_podcasts(podcasts)
            print self._delete_old_podcasts(podcasts[0]['dir'])
        else:
            pass

    def unsubscribe(self):
        """
        Delete a subscription. Remove it from the database and delete all podcasts the its dir.
        """
        feed_name = self.db.get_name_from_feed(self.feed)
        if feed_name is None or not feed_name:
            print "Feed does not exist in the database!"
        else:
            feed_name = slugify(feed_name)
            channel_directory = settings.DOWNLOAD_DIRECTORY + os.sep + feed_name
            self.db.delete_subscription(self.feed)
            try:
                shutil.rmtree(channel_directory)
            except OSError:
                print "Subscription directory has not been found - it might have been manually deleted"
            print "Subscription '" + feed_name + "' removed"

    def update(self):
        """
        Update and loop through all subscriptions.
        Then download the first x number of episodes as defined in the settings.
        """
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
                podcasts = self._iterate_feed(data)
                if podcasts:
                    self._save_podcasts(podcasts)
                    self._delete_old_podcasts(podcasts[0]['dir'])
        if self.db.has_mail_users():
            print "Have e-mail address(es) - attempting e-mail..."
            message = "0 podcasts have been downloaded from this feed due to RSS syntax problems. " \
                      "Please try again later"
            mail_updates(message, self.db.get_mail_users())

    def _iterate_feed(self, data):
        last_ep_date = 0
        podcasts = []
        try:
            xml_data = xml.dom.minidom.parse(data).getElementsByTagName('channel')[0]
            channel_title = slugify(xml_data.getElementsByTagName('title')[0].firstChild.data)
            # Build the channel dir and create it if it doesn't exist
            channel_directory = settings.DOWNLOAD_DIRECTORY + os.sep + channel_title
            if not os.path.exists(channel_directory):
                os.makedirs(channel_directory)

            # Fetch the last episode date, or
            # Create a DB entry if the subscription doesn't exist
            if self.db.does_sub_exist(self.feed):
                last_ep_date = self.db.get_last_subscription_downloaded(self.feed)
            else:
                self.db.insert_subscription(channel_title, self.feed)

            # Iterate though each item (podcast) in the xml_data
            try:
                for item in xml_data.getElementsByTagName('item'):
                    # Get and convert the date of the current podcast
                    item_time = self._date_to_int(
                        item.getElementsByTagName('pubDate')[0].firstChild.data
                    )

                    # If current podcast date > the last episode date, and
                    # The number of podcasts from the settings > number of current podcasts downloaded
                    # Add the current podcast to the list
                    if item_time > last_ep_date and settings.NUMBER_OF_PODCASTS_TO_KEEP+2 > len(podcasts):
                        podcasts.append({
                            'title': item.getElementsByTagName('title')[0].firstChild.data,
                            'file': item.getElementsByTagName('enclosure')[0].getAttribute('url'),
                            'dir': channel_directory,
                            'type': item.getElementsByTagName('enclosure')[0].getAttribute('type'),
                            'size': item.getElementsByTagName('enclosure')[0].getAttribute('length'),
                            'date': item_time
                        })
                    else:
                        break
            except (TypeError, ValueError):
                print "This item has a badly formatted date. Cannot download!"
        except xml.parsers.expat.ExpatError:
            print "ERROR - Malformed XML syntax in feed. Skipping..."
        except UnicodeEncodeError:
            print "ERROR - Unicode encoding error in string. Cannot convert to ASCII. Skipping..."
        return podcasts

    def _open_data_source(self):
        """
        Try and open the feed (self.feed) as as declared in init or update.
        :return: the data feed or None if there was a problem
        """
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
        """
        Given a list of podcasts, save the podcasts to the file system.
        :param podcasts:
            'title': title of the podcast,
            'file':  URL where the podcast can be downloaded,
            'dir':   The dir to save the podcast at,
            'type':  file type of the podcast,
            'size':  byte size of the podcast,
            'date':  date the podcast was uploaded
        """
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
            # Sort the podcasts so the oldest one is saved first.
            # This allows us to use the file system time for tracking which podcast is the oldest.
            podcasts = sorted(podcasts, key=itemgetter('date'))

            for podcast in podcasts:
                # Get the file name (we don't use the path right now)
                (item_path, item_file_name) = os.path.split(podcast['file'])
                # Limit the file name to onl the first 50 chars
                if len(item_file_name) > 50:
                    item_file_name = item_file_name[:50]
                # Build the local file
                local_file = podcast['dir'] + os.sep + slugify(item_file_name)
                # Make sure the file has the correct extension
                if extension_map[podcast['type']]:
                    if not local_file.endswith(extension_map[podcast['type']]):
                        local_file += extension_map[podcast['type']]
                # If the file isn't already there, try and save it
                if not os.path.exists(local_file):
                    print "\nDownloading " + item_file_name
                    try:
                        item_file = urllib2.urlopen(podcast['file'])
                        with open(local_file, 'wb') as output:
                            output.write(item_file.read())
                        print "Podcast downloaded to: ", local_file
                    except urllib2.URLError as e:
                        print "ERROR - Could not write item to file: ", e
                    except socket.error as e:
                        print "ERROR - Socket reset by peer: ", e
            self.db.update_subscription(self.feed, podcasts[-1]['date'])

    def _delete_old_podcasts(self, channel_dir):
        """
        Delete all old podcasts from a given dir. Following then NUMBER_OF_PODCASTS_TO_KEEP in settings.
        :param channel_dir: The dir where the podcasts live
        """
        message = "Deleted Files: \n"
        os.chdir(channel_dir)
        files = sorted(os.listdir(os.getcwd()), key=os.path.getmtime)
        print files
        if len(files) <= settings.NUMBER_OF_PODCASTS_TO_KEEP:
            return "No files to delete"
        for old_file in files[:len(files) - settings.NUMBER_OF_PODCASTS_TO_KEEP]:
            os.remove(old_file)
            message += old_file + "\n"
        return message

    def _date_to_int(self, date):
        """
        Convert a date (%a, %d %b %Y %H:%M:%S) to an int
        :param date: date
        :return: seconds since epoch
        """
        new_date = ""
        split_array = date.split(' ')
        for i in range(0, 5):
            new_date += split_array[i] + " "
        if new_date:
            return int(datetime.datetime.strptime(new_date[:-1], "%a, %d %b %Y %H:%M:%S").strftime('%s'))
        else:
            return 0

    def _int_to_date(self, date):
        """
        Convert a int (seconds since epoch) to a date
        :param date: seconds since epoch
        :return: date
        """
        return datetime.datetime.fromtimestamp(date).strftime("%a, %d %b %Y %H:%M:%S")
