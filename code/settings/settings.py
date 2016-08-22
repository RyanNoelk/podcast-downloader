#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

FROM_EMAIL_ADDRESS = "ichbinsub@gmail.com"
CURRENT_DIRECTORY = os.path.realpath(os.path.dirname(sys.argv[0]))
DB_NAME = "podcast.db"
#DOWNLOAD_DIRECTORY = "/data/ryannoelk/files/podcasts"
DOWNLOAD_DIRECTORY = "/Users/ryannoelk/code/podcast-downloader/podcasts"
NUMBER_OF_PODCASTS_TO_KEEP = 2
