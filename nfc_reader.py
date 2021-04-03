#!/usr/bin/env python3

from mfrc522 import SimpleMFRC522
import argparse
import logging
import musicpd
import time

argparser = argparse.ArgumentParser()
argparser.add_argument('-l', '--loglevel',
	help='Level of logging that should be passed to stdout (e.g. DEBUG, INFO)')
args = argparser.parse_args()
loglevel = args.loglevel.upper() if args.loglevel else ''

numeric_loglevel = getattr(logging, loglevel.upper(), None)
if not isinstance(numeric_loglevel, int):
	raise ValueError('Invalid log level: %s' % args.loglevel)

logging.basicConfig(level=numeric_loglevel)
logging.captureWarnings(True)

last_seen_tag_id = None

reader = SimpleMFRC522()
cli = musicpd.MPDClient()
seen_nones = 0
playing = False

while True:
	(id, text) = reader.read_no_block()
	if id is None:
		if seen_nones > 3 and playing:
			logging.debug('Seen no NFC card %d times in a row, stopping playback', seen_nones)
			cli.connect()
			cli.pause()
			cli.disconnect()
			playing = False

		seen_nones += 1
		if seen_nones > 1:
			logging.debug('Seen no NFC card %d times in a row', seen_nones)
	elif id != last_seen_tag_id:
		playlist = text.rstrip()
		cli.connect()
		try:
			cli.clear()
			cli.load(playlist)
			cli.play()
			logging.info('Loaded playlist %s', playlist)
			playing = True
			seen_nones = 0
		except musicpd.CommandError as e:
			logging.info('Error loading playlist %s: %r', playlist, e)
		cli.disconnect()
		last_seen_tag_id = id
	elif id == last_seen_tag_id and not playing:
		cli.connect()
		try:
			cli.play()
			playing = True
			seen_nones = 0
		except musicpd.CommandError as e:
			logging.info('Error playing back %s: %r', playlist, e)
		cli.disconnect()
	else:
		# We see the same NFC tag as before.
		seen_nones = 0

	time.sleep(1)
