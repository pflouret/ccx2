#!/usr/bin/env python

import re
import socket
import string
import sys
import unicodedata
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse

try:
  import json
except ImportError:
  import simplejson as json

try:
  import lxml.html
except ImportError:
  pass

socket.setdefaulttimeout(5)

LYRICWIKI_URL = 'http://lyrics.wikia.org'
YQL_URL = "http://query.yahooapis.com/v1/public/yql?q=select%%20title,url%%20from%%20search.web%%20where%%20query%%3D%%22%s%%20-inurl%%3ACategory%%20site%%3Alyrics.wikia.com%%22%%20and%%20title%%20like%%20%%22%%25%%3A%%25%%22&format=json"
# "http://query.yahooapis.com/v1/public/yql?q=select%20title,url%20from%20search.web%20where%20query%3D%22XXXXX%20-inurl%3ACategory%20site%3Alyrics.wikia.com%22%20and%20title%20like%20%22%25%3A%25%22&format=json&callback=cbfunc"

year_rx = re.compile(r'\s*\(\d{4}\)$')
sym_rx = re.compile(r'[^a-zA-Z0-9 ]')

def do_request(req):
  if not req: raise ValueError

  error = None

  try:
    r = urllib.request.urlopen(req)
  except:
    error = True

  if error or r.code != 200:
    return None

  return r.read()

def get_google_results(query):
  url = YQL_URL % urllib.parse.quote_plus(query.encode('utf-8'))

  response = do_request(url)

  if not response: return []

  r = json.loads(response)

  if not r["query"]["results"]: return []

  if type(r["query"]["results"]) == type([]):
    r["query"]["results"] = [r["query"]["results"]]
  if type(r["query"]["results"]["result"]) != type([]):
    r["query"]["results"]["result"] = [r["query"]["results"]["result"]]

  return [(re.sub(' Lyrics -.*', '', lxml.html.fromstring(e["title"]).text_content()), e["url"])
          for e in r["query"]["results"]["result"]]

def get_lyrics(url):
  html = do_request(url)

  if not html:
    return None

  doc = lxml.html.fromstring(html.decode('utf8'))
  try:
    lyricbox = doc.cssselect('div.lyricbox')[0]
  except IndexError:
    return None

  for e in lyricbox.getchildren():
    if e.tag != 'br':
      e.drop_tree()

  lines = [next(lyricbox.itertext())] + [b.tail or "" for b in lyricbox.getchildren()]
  return '\n'.join(lines) or None

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
    except ValueError as TypeError:
      pass

  def get_song_results(self):
    return get_google_results("%s %s" % (self.artist, self.title))

  def get_song_url(self, albums):
    if not albums: raise ValueError

    album = self.album and self.normalizeish(self.album)

    if album and album in albums:
      albums = {album: albums[album]}

    title = self.normalizeish(self.title)

    for album in list(albums.values()):
      for tracknr, a in album.items():
        if title == self.normalizeish(a.text):
          return LYRICWIKI_URL + a.get('href')

  def try_url(self):
    artist = string.capwords(self.artist).replace(" ", "_")
    url = "%s/%s" % (LYRICWIKI_URL, urllib.parse.quote_plus(artist.encode('utf-8')))

    return do_request(url)

  def try_url_from_google(self):
    for title, url in get_google_results(self.artist):
      if ':' not in url.replace('http://', ''):
        return do_request(url)

  def normalizeish(self, s):
    s = year_rx.sub('', s).strip()
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'replace')
    s = sym_rx.sub('', s)
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
        except (TypeError, IndexError):
          pass
      if not al: del albums[album]

    return albums or None

