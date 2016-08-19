#!/usr/bin/env python

import smtplib
import platform
import traceback


def mail_updates(mess, addresses):
    if addresses:
        subject_line = "PodGrab Update"
        '''
        if int(num_updates) > 0:
            subject_line += " - NEW updates!"
        else:
            subject_line += " - nothing new..."
        '''

        for address in addresses:
            try:
                headers = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % \
                        ('podgrab@' + platform.node(), address[0], subject_line)
                message = headers + mess
                mail_server = smtplib.SMTP('smtp.gmail.com:587')
                mail_server.ehlo()
                mail_server.starttls()
                mail_server.sendmail('podgrab@' + platform.node(), address[0], message)
                mail_server.quit()

                print "Successfully sent podcast updates e-mail to: " + address[0]
            except smtplib.SMTPException:
                traceback.print_exc()
                print "Could not send podcast updates e-mail to: " + address[0]
