# -*- coding: utf-8 -*-

# system imports
from enum import Enum


OFF = 0
MIXED = 1
ON = 2

CLIP = 0
TRUNCATE_HEAD = 1
TRUNCATE_MIDDLE = 2
TRUNCATE_TAIL = 3

WORD_WRAP = 10
CHARACTER_WRAP = 11


class ImageTemplate(Enum):
    FollowLink = 0
    InvalidData = 1
    Refresh = 2
    Reveal = 3
    StopProgress = 4
