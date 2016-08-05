#!/usr/bin/env python

import os
import sqlite3


def connect_database(curr_loc):
    conn = sqlite3.connect(curr_loc + os.sep + "PodGrab.db")
    return conn

def setup_database(cur, conn):
    cur.execute("CREATE TABLE subscriptions (channel text, feed text, last_ep text)")
    cur.execute("CREATE TABLE email (address text)")
    conn.commit()


def insert_subscription(cur, conn, chan, feed):
    chan.replace(' ', '-')
    chan.replace('---','-')
    row = (chan, feed, "NULL")
    cur.execute('INSERT INTO subscriptions(channel, feed, last_ep) VALUES (?, ?, ?)', row)
    conn.commit()

def delete_subscription(cur, conn, url):
    row = (url,)
    cur.execute('DELETE FROM subscriptions WHERE feed = ?', row)
    conn.commit()


def get_name_from_feed(cur, conn, url):
    row = (url,)
    cur.execute('SELECT channel from subscriptions WHERE feed = ?', row)
    return_string = cur.fetchone()
    try:
        return_string = ''.join(return_string)
    except TypeError:
        return_string = "None"
    return str(return_string)


def list_subscriptions(cur, conn):
    count = 0
    try:
        result = cur.execute('SELECT * FROM subscriptions')
        for sub in result:
            print "Name:\t\t", sub[0]
            print "Feed:\t\t", sub[1]
            print "Last Ep:\t", sub[2], "\n"
            count += 1
        print str(count) + " subscriptions present"
    except sqlite3.OperationalError:
        print "There are no current subscriptions or there was an error"


def get_subscriptions(cur, conn):
    try:
        cur.execute('SELECT * FROM subscriptions')
        return cur.fetchall()
    except sqlite3.OperationalError:
        print "There are no current subscriptions"
        return None


def update_subscription(cur, conn, feed, date):
    row = (date, feed)
    cur.execute('UPDATE subscriptions SET last_ep = ? where feed = ?', row)
    conn.commit()


def get_last_subscription_downloaded(cur, conn, feed):
    row = (feed,)
    cur.execute('SELECT last_ep FROM subscriptions WHERE feed = ?', row)
    return cur.fetchone()


def does_sub_exist(cur, conn, feed):
    row = (feed,)
    cur.execute('SELECT COUNT (*) FROM subscriptions WHERE feed = ?', row)
    return_string = str(cur.fetchone())[1]
    if return_string == "0":
        return 0
    else:
        return 1

def add_mail_user(cur, conn, address):
    row = (address,)
    cur.execute('INSERT INTO email(address) VALUES (?)', row)
    conn.commit()


def delete_mail_user(cur, conn, address):
    row = (address,)
    cur.execute('DELETE FROM email WHERE address = ?', row)
    conn.commit()


def get_mail_users(cur, conn):
    cur.execute('SELECT address FROM email')
    return cur.fetchall()


def list_mail_addresses(cur, conn):
    cur.execute('SELECT * from email')
    result = cur.fetchall()
    print "Listing mail addresses..."
    for address in result:
        print "Address:\t" + address[0]


def has_mail_users(cur, conn):
    cur.execute('SELECT COUNT(*) FROM email')
    if cur.fetchone() == "0":
        return 0
    else:
        return 1


def does_database_exist(curr_loc):
    db_name = "PodGrab.db"
    if os.path.exists(curr_loc + os.sep + db_name):
        return 1
    else:
        return 0
