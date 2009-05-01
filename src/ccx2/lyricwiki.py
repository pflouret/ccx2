#!/usr/bin/env python

import re
import socket
import string
import sys
import unicodedata
import urllib
import urllib2

try:
  import json
except ImportError:
  import simplejson as json

try:
  import lxml.html
except ImportError:
  pass

from pprint import pprint

socket.setdefaulttimeout(5)

LYRICWIKI_URL = u'http://lyricwiki.org'
GOOGLE_URL = "http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=%s+" \
             "-inurl%%3Aindex.php+-inurl%%3Aapi.php+-inurl%%3A%%22Category%%3A%%22+" \
             "site%%3Alyricwiki.org&rsz=large&hl=en&safe=off"

year_rx = re.compile(r'\s*\(\d{4}\)$')
sym_rx = re.compile(r'[^a-zA-Z0-9 ]')

def do_request(req):
  if not req: raise ValueError

  error = None

  try:
    r = urllib2.urlopen(req)
  except:
    error = True

  if error or r.getcode() != 200:
    return None

  return r.read()

def get_google_results(query):
  url = GOOGLE_URL % urllib.quote_plus(query.encode('utf-8'))

  response = do_request(url)

  if not response: return []

  r = json.loads(response)

  if r["responseStatus"] != 200: return []

  return [(e["titleNoFormatting"].replace(' - Lyrics from LyricWiki', ''), e["url"])
          for e in r["responseData"]["results"]]

def get_lyrics(url):
  html = do_request(url)

  if not html:
    return None

  doc = lxml.html.fromstring(html.decode('utf8'))
  try:
    lyricbox = doc.cssselect('div.lyricbox')[0]
  except IndexError:
    return None

  if lyricbox.text is None:
    return None
  
  return "%s\n%s" % (lyricbox.text, '\n'.join([br.tail or "" for br in lyricbox.findall('br')]))

class LyricWiki(object):
  def __init__(self, artist, title, album=None, tracknr=None):
    self.artist = artist
    self.title = title
    self.album = album
    self.tracknr = tracknr

  def get(self, url=None):
    try:
      html = self.try_url() or self.try_url_from_google()
      albums = self.get_albums(html)
      url = self.get_song_url(albums)
      return get_lyrics(url)
    except ValueError, TypeError:
      pass

  def get_song_results(self):
    return get_google_results("%s %s" % (self.artist, self.title))

  def get_song_url(self, albums):
    if not albums: raise ValueError

    album = self.album and self.normalizeish(self.album)

    if album and album in albums:
      albums = {album: albums[album]}

    title = self.normalizeish(self.title)

    for album in albums.values():
      for tracknr, a in album.iteritems():
        if title == self.normalizeish(a.text):
          return LYRICWIKI_URL + a.get('href')

  def try_url(self):
    artist = string.capwords(self.artist).replace(" ", "_")
    url = u"%s/%s" % (LYRICWIKI_URL, urllib.quote_plus(artist.encode('utf-8')))

    return do_request(url)

  def try_url_from_google(self):
    for title, url in get_google_results(self.artist):
      if ':' not in url.replace('http://', ''):
        return do_request(url)

  def normalizeish(self, s):
    s = year_rx.sub(u'', s).strip()
    s = unicodedata.normalize('NFKD', unicode(s)).encode('ascii', 'replace')
    s = sym_rx.sub(u'', s)
    return s.lower()
    
  def get_albums(self, html):
    if not html: raise ValueError

    doc = lxml.html.fromstring(html.decode('utf8'))
    sections = doc.cssselect('h2 > span.mw-headline')
    albums = {}

    for s in sections:
      try:
        album = s.cssselect('a:first-child')[0].text
      except:
        album = s.text

      if not len(album): continue
      
      album = self.normalizeish(album)

      songlist = s.xpath("./following::ol[1]")

      if not songlist: continue

      al = albums.setdefault(album, {})
      for i, e in enumerate(songlist[0].getchildren()):
        try:
          a = e.cssselect('a')[0]
          if '(page does not exist)' not in a.get('title'):
            al[i+1] = a
        except TypeError, IndexError:
          pass
      if not al: del albums[album]

    return albums or None

