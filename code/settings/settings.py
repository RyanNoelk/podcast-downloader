#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

FROM_EMAIL_ADDRESS = "ichbinsub@gmail.com"
EMAIL_PASSWORD = "abcdefg"
CURRENT_DIRECTORY = os.path.realpath(os.path.dirname(sys.argv[0]))
DOWNLOAD_DIRECTORY = CURRENT_DIRECTORY + os.sep + "podcasts"
DB_NAME = "podcast.db"
NUMBER_OF_PODCASTS_TO_KEEP = 2

try:
    from local_settings import *
except ImportError:
    pass