#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

from code.rss_handler import RssHandler
from code.rss_handler import DbHandler


def main(argv):

    # Arg list and help menu
    parser = argparse.ArgumentParser(description='A command line Podcast downloader for RSS XML feeds')
    parser.add_argument('-s', '--subscribe',
                        action="store", dest="sub_feed_url",
                        help='Subscribe to the following XML feed and download latest podcast')
    parser.add_argument('-un', '--unsubscribe', action="store", dest="unsub_url",
                        help='Unsubscribe from the following Podcast feed')
    parser.add_argument('-l', '--list', action="store_const", const="ALL", dest="list_subs",
                        help='Lists current Podcast subscriptions')
    parser.add_argument('-u', '--update', action="store_const", const="UPDATE", dest="update_subs",
                        help='Updates all current Podcast subscriptions')
    parser.add_argument('-ma', '--mail-add', action="store", dest="mail_address_add",
                        help='Add a mail address to mail subscription updates to')
    parser.add_argument('-md', '--mail-delete', action="store", dest="mail_address_delete",
                        help='Delete a mail address')
    parser.add_argument('-ml', '--mail-list', action="store_const", const="MAIL", dest="list_mail",
                        help='Lists all current mail addresses')
    arguments = parser.parse_args()

    # Spin up the Db class that we will use for the life of the program
    db = DbHandler()
    
    if arguments.sub_feed_url:
        # Add a new rss feed
        RssHandler(arguments.sub_feed_url, db).subscribe()
    elif arguments.unsub_url:
        # Remove a rss feed
        RssHandler(arguments.unsub_url, db).unsubscribe()
    elif arguments.update_subs:
        # Update all rss feeds
        RssHandler(db).update()
    elif arguments.list_subs:
        # List current podcast subscriptions
        db.list_subscriptions()
    elif arguments.mail_address_add:
        # Add an email to the mail list
        db.add_mail_user(arguments.mail_address_add)
    elif arguments.mail_address_delete:
        # Delete an email from the mail list
        db.delete_mail_user(arguments.mail_address_delete)
    elif arguments.list_mail:
        # Print the mail list
        db.list_mail_addresses()
    else:
        exit("No Arguments supplied - for usage run 'PodGrab.py -h'")

if __name__ == "__main__":
    main(sys.argv[1:])
