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
from time import gmtime, strftime
import shutil

from code.settings import *
from code.rss_handler import *
from code.mailer import *


def main(argv):
    mode = MODE_NONE
    has_error = 0
    error_string = ""
    feed_url = ""
    mail_address = ""
    mail = ""
    current_directory = os.path.realpath(os.path.dirname(sys.argv[0]))
    download_directory = DOWNLOAD_DIRECTORY
    total_items = 0
    total_size = 0
    data = ""

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
    
    if arguments.sub_feed_url:
        feed_url = arguments.sub_feed_url
        data = open_datasource(feed_url)
        if not data:
            error_string = "Not a valid XML file or URL feed!"
            has_error = 1
        else:
            print "XML data source opened\n"
            mode = MODE_SUBSCRIBE
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
                try:
                    shutil.rmtree(channel_directory)
                except OSError:
                    print "Subscription directory has not been found - it might have been manually deleted" 
                print "Subscription '" + feed_name + "' removed"
        elif mode == MODE_SUBSCRIBE:
            print iterate_feed(data, mode, download_directory, todays_date, cursor, connection, feed_url)
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


if __name__ == "__main__":
    main(sys.argv[1:])