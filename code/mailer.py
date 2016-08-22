#!/usr/bin/env python

import traceback
from email.header import Header
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPException

from code.settings.settings import FROM_EMAIL_ADDRESS, EMAIL_PASSWORD


def mail_updates(body, addresses):
    if addresses:
        subject = "Podcast Updated"

        for address in addresses:
            try:
                message = MIMEText(body, _charset="UTF-8")
                message['Subject'] = Header(subject, "utf-8")

                server = SMTP_SSL(u'smtp.gmail.com:465')
                server.ehlo()
                server.login(FROM_EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(FROM_EMAIL_ADDRESS, address, message.as_string())
                server.quit()

                print "Successfully sent podcast updates e-mail to: " + address[0]
            except SMTPException:
                traceback.print_exc()
