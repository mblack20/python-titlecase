#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Original Perl version by: John Gruber http://daringfireball.net/ 10 May 2008
Python version by Stuart Colville http://muffinresearch.co.uk
License: http://www.opensource.org/licenses/mit-license.php
"""

from __future__ import unicode_literals

import argparse
import re
import sys
import logging

__all__ = ['titlecase']
__version__ = '0.12.0'

SMALL = (
    # original list
    'a|an|and|as|at|but|by|en|for|if|in|of|on|or|the|to|v\.?|via|vs\.?'

    # extras for city/place names
    '|al|au|da|das|de|del|della|delle|des|di|do|dos|du|el|es|et|la|las|le|les|lez|los|na|nad|sous|sul|sur|under|upon|y'
)
PUNCT = r"""!"“#$%&'‘()*+,\-–‒—―./:;?@[\\\]_`{|}~"""

SMALL_WORDS = re.compile(r'^(%s)$' % SMALL, re.I)
INLINE_PERIOD = re.compile(r'[a-z][.][a-z]', re.I)
UC_ELSEWHERE = re.compile(r'[%s]*?[a-zA-Z]+[A-Z]+?' % PUNCT)
CAPFIRST = re.compile(r"^[%s]*?([A-Za-z])" % PUNCT)
SMALL_FIRST = re.compile(r'^([%s]*)(%s)\b' % (PUNCT, SMALL), re.I)
SMALL_LAST = re.compile(r'\b(%s)[%s]?$' % (SMALL, PUNCT), re.I)
SUBPHRASE = re.compile(r'([:.;?!\-–‒—―][ ])(%s)' % SMALL)
APOS_SECOND = re.compile(r"^[dol]{1}['‘]{1}[a-z]+(?:['s]{2})?$", re.I)
UC_INITIALS = re.compile(r"^(?:[A-Z]{1}\.{1}|[A-Z]{1}\.{1}[A-Z]{1})+$")
MAC_MC = re.compile(r"^([Mm]c|MC)(\w.+)")


class Immutable(object):
    pass


text_type = unicode if sys.version_info < (3,) else str


class ImmutableString(text_type, Immutable):
    pass


class ImmutableBytes(bytes, Immutable):
    pass


def _mark_immutable(text):
    if isinstance(text, bytes):
        return ImmutableBytes(text)
    return ImmutableString(text)


def set_small_word_list(small=SMALL):
    global SMALL_WORDS
    global SMALL_FIRST
    global SMALL_LAST
    global SUBPHRASE
    SMALL_WORDS = re.compile(r'^(%s)$' % small, re.I)
    SMALL_FIRST = re.compile(r'^([%s]*)(%s)\b' % (PUNCT, small), re.I)
    SMALL_LAST = re.compile(r'\b(%s)[%s]?$' % (small, PUNCT), re.I)
    SUBPHRASE = re.compile(r'([:.;?!][ ])(%s)' % small)


def titlecase(text, callback=None, small_first_last=True):
    """
    Titlecases input text

    This filter changes all words to Title Caps, and attempts to be clever
    about *un*capitalizing SMALL words like a/an/the in the input.

    The list of "SMALL words" which are not capped comes from
    the New York Times Manual of Style, plus 'vs' and 'v'.

    """

    lines = re.split('[\r\n]+', text)
    processed = []
    for line in lines:
        all_caps = line.upper() == line
        tc_line = []

        # Handle hyphenation without recursion
        has_hyphens = False
        hyphen_pos = []
        if '-' in line:
            hyphen_pos = [pos for pos, char in enumerate(line) if char == '-']
            logging.debug('Has hyphens : {}'.format(hyphen_pos))
            line = line.replace('-', ' ')
            has_hyphens = True

        words = re.split('[\t ]', line)

        for word in words:
            if callback:
                new_word = callback(word, all_caps=all_caps)
                if new_word:
                    # Address #22: If a callback has done something
                    # specific, leave this string alone from now on
                    tc_line.append(_mark_immutable(new_word))
                    continue

            if all_caps:
                logging.debug('is all caps')
                if UC_INITIALS.match(word):
                    tc_line.append(word)
                    continue

            if APOS_SECOND.match(word):
                logging.debug('ASOS second match')
                if len(word[0]) == 1 and word[0] not in 'aeiouAEIOU':
                    word = word[0].lower() + word[1] + word[2].upper() + word[3:]
                else:
                    word = word[0].upper() + word[1] + word[2].upper() + word[3:]
                tc_line.append(word)
                continue

            match = MAC_MC.match(word)
            if match:
                logging.debug('MAC_MC second match')
                tc_line.append("%s%s" % (match.group(1).capitalize(),
                                         titlecase(match.group(2), callback, small_first_last)))
                continue

            if INLINE_PERIOD.search(word) or (not all_caps and UC_ELSEWHERE.match(word)):
                logging.debug('INLINE_PEROID match')
                tc_line.append(word)
                continue

            if SMALL_WORDS.match(word):
                logging.debug('word : `{}` SMALL_WORDS match (lowercasing)'.format(word))
                tc_line.append(word.lower())
                continue

            if "/" in word and "//" not in word:
                logging.debug('SLASHES found (recursing)')
                slashed = map(
                    lambda t: titlecase(t, callback, False),
                    word.split('/')
                )
                tc_line.append("/".join(slashed))
                continue

            # if '-' in word:
            #     logging.debug('Hyphenated word (recursing).')
            #     hyphenated = map(
            #         lambda t: titlecase(t, callback, small_first_last),
            #         word.split('-')
            #     )
            #     tc_line.append("-".join(hyphenated))
            #     logging.debug('Returning: {}'.format(tc_line))
            #     continue

            if all_caps:
                logging.debug('ALL_CAPS, lowercasing')
                word = word.lower()

            # Just a normal word that needs to be capitalized
            if not SMALL_WORDS.match(word):
                logging.debug('word : `{}` not matched, capitalising'.format(word))
                tc_line.append(CAPFIRST.sub(lambda m: m.group(0).upper(), word))

        logging.debug('TC_LINE: {}'.format(tc_line))
        if small_first_last and tc_line:
            if not isinstance(tc_line[0], Immutable):
                logging.debug('IS SMALL_FIRST')
                tc_line[0] = SMALL_FIRST.sub(lambda m: '%s%s' % (
                    m.group(1),
                    m.group(2).capitalize()
                ), tc_line[0])
                logging.debug('TC_LINE[0]: {}'.format(tc_line[0]))

            if not isinstance(tc_line[-1], Immutable):
                logging.debug('IS SMALL_LAST')
                tc_line[-1] = SMALL_LAST.sub(
                    lambda m: m.group(0).capitalize(), tc_line[-1]
                )
                logging.debug('TC_LINE[-1]: {}'.format(tc_line[-1]))

        result = " ".join(tc_line)
        logging.debug('RESULT: {}'.format(tc_line))

        result = SUBPHRASE.sub(lambda m: '%s%s' % (
            m.group(1),
            m.group(2).capitalize()
        ), result)
        logging.debug('AFTER SUBPHRASE RESULT: {}'.format(tc_line))

        # Replace hyphens
        if has_hyphens:
            logging.debug('Replacing hyphens.')
            result_list = list(result)
            for pos in hyphen_pos:
                result_list[pos] = '-'
            result = "".join(result_list)
            logging.debug('AFTER REPLACING : {}'.format(result))

        processed.append(result)

    return "\n".join(processed)


def cmd():
    '''Handler for command line invocation'''

    # Try to handle any reasonable thing thrown at this.
    # Consume '-f' and '-o' as input/output, allow '-' for stdin/stdout
    # and treat any subsequent arguments as a space separated string to
    # be titlecased (so it still works if people forget quotes)
    parser = argparse.ArgumentParser()
    in_group = parser.add_mutually_exclusive_group()
    in_group.add_argument('string', nargs='*', default=[],
                          help='String to titlecase')
    in_group.add_argument('-f', '--input-file',
                          help='File to read from to titlecase')
    parser.add_argument('-o', '--output-file',
                        help='File to write titlecased output to)')

    args = parser.parse_args()

    if args.input_file is not None:
        if args.input_file == '-':
            ifile = sys.stdin
        else:
            ifile = open(args.input_file)
    else:
        ifile = sys.stdin

    if args.output_file is not None:
        if args.output_file == '-':
            ofile = sys.stdout
        else:
            ofile = open(args.output_file, 'w')
    else:
        ofile = sys.stdout

    if len(args.string) > 0:
        in_string = ' '.join(args.string)
    else:
        with ifile:
            in_string = ifile.read()

    with ofile:
        ofile.write(titlecase(in_string))
