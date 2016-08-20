#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3
from slugify import slugify

import settings


class DbHandler:

    def __init__(self):
        if os.path.exists(settings.CURRENT_DIRECTORY + os.sep + settings.DB_NAME):
            self.conn = sqlite3.connect(settings.CURRENT_DIRECTORY + os.sep + "PodGrab.db")
            if not self.conn:
                exit("Could not connect to PodGrab database file!")
            else:
                self.cursor = self.conn.cursor()
        else:
            print "PodGrab database missing. Creating..."
            self.conn = sqlite3.connect(settings.CURRENT_DIRECTORY + os.sep + "PodGrab.db")
            if not self.conn:
                exit("Could not create PodGrab database file!")
            else:
                self.cursor = self.conn.cursor()
                self.cursor.execute("CREATE TABLE subscriptions (channel text, feed text, last_ep int)")
                self.cursor.execute("CREATE TABLE email (address text)")
                self.conn.commit()

    def insert_subscription(self, channel, feed):
        """
        Creates an entry into the database with a new podcast subscription.
        :param channel:  The name of the RSS feed.
        :param feed: URL to the RSS feed.
        """
        row = (slugify(channel), feed, 0)
        self.cursor.execute('INSERT INTO subscriptions(channel, feed, last_ep) VALUES (?, ?, ?)', row)
        self.conn.commit()

    def delete_subscription(self, feed):
        """
        Deletes an entry from the database.
        :param feed: URL to the RSS feed.
        """
        row = (feed,)
        self.cursor.execute('DELETE FROM subscriptions WHERE feed = ?', row)
        self.conn.commit()

    def get_name_from_feed(self, feed):
        """
        Retrieves the name of an RSS feed.
        :param feed: URL to the RSS feed.
        :return: The name of the RSS feed or None if it doesn't exist.
        """
        row = (feed,)
        self.cursor.execute('SELECT channel from subscriptions WHERE feed = ?', row)
        return_string = self.cursor.fetchone()
        try:
            return_string = ''.join(return_string)
            return str(return_string)
        except TypeError:
            pass
        return None

    def list_subscriptions(self):
        """
        Lists all current podcast subscriptions.
        """
        print "Listing current podcast subscriptions...\n"
        count = 0
        try:
            result = self.cursor.execute('SELECT * FROM subscriptions')
            for sub in result:
                print "Name:\t\t", sub[0]
                print "Feed:\t\t", sub[1]
                print "Last Ep:\t", sub[2], "\n"
                count += 1
            print str(count) + " subscriptions present"
        except sqlite3.OperationalError:
            print "There are no current subscriptions or there was an error"

    def get_subscriptions(self):
        """
        Gets all current subscriptions.
        :return: all current subscriptions.
        """
        try:
            self.cursor.execute('SELECT * FROM subscriptions')
            return self.cursor.fetchall()
        except sqlite3.OperationalError:
            return None

    def update_subscription(self, feed, date):
        """
        Updates a subscription with feed==feed with the given date.
        :param date: epoch int of the current date.
        :param feed: URL to the RSS feed.
        """
        row = (date, feed)
        self.cursor.execute('UPDATE subscriptions SET last_ep = ? where feed = ?', row)
        self.conn.commit()

    def get_last_subscription_downloaded(self, feed):
        """
        Returns the epoch int date of the last podcast that was downloaded.
        :param feed: URL to the RSS feed.
        :return: epoch int date of the last podcast that was downloaded.
        """
        row = (feed,)
        self.cursor.execute('SELECT last_ep FROM subscriptions WHERE feed = ?', row)
        return self.cursor.fetchone()[0]

    def does_sub_exist(self, feed):
        """
        Checks whether a subscription exists based on the feed.
        :param feed: URL to the RSS feed.
        :return: True or False.
        """
        row = (feed,)
        self.cursor.execute('SELECT COUNT (*) FROM subscriptions WHERE feed = ?', row)
        return_string = str(self.cursor.fetchone())[1]
        if return_string == "0":
            return 0
        else:
            return 1

    def add_mail_user(self, address):
        """
        Adds an email address to the database.
        :param address: email address.
        """
        row = (address,)
        self.cursor.execute('INSERT INTO email(address) VALUES (?)', row)
        self.conn.commit()
        print "E-Mail address: " + address + " has been added"

    def delete_mail_user(self, address):
        """
        Deletes an email address from the database.
        :param address: email address.
        """
        row = (address,)
        self.cursor.execute('DELETE FROM email WHERE address = ?', row)
        self.conn.commit()
        print "E-Mail address: " + address + " has been deleted"

    def get_mail_users(self):
        """
        Returns all email address in the database.
        :return: all email address in the database.
        """
        self.cursor.execute('SELECT address FROM email')
        return self.cursor.fetchall()

    def list_mail_addresses(self):
        """
        Lists all of the emails addresses in the database
        """
        self.cursor.execute('SELECT * from email')
        result = self.cursor.fetchall()
        print "Listing mail addresses..."
        for address in result:
            print "Address:\t" + address[0]

    def has_mail_users(self):
        """
        Checks whether there are any users with email addresses.
        :return: True or False.
        """
        self.cursor.execute('SELECT COUNT(*) FROM email')
        if self.cursor.fetchone() == "0":
            return False
        else:
            return True
