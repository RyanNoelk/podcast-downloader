#!/usr/bin/env python

import smtplib
import platform
import traceback

from code.db_handler import get_mail_users


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
