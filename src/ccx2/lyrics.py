# Copyright (c) 2008-2009 Pablo Flouret <quuxbaz@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met: Redistributions of
# source code must retain the above copyright notice, this list of conditions and
# the following disclaimer. Redistributions in binary form must reproduce the
# above copyright notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
# Neither the name of the software nor the names of its contributors may be
# used to endorse or promote products derived from this software without specific
# prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import threading

import urwid

from . import commands
from . import config
from . import listbox
from . import lyricwiki
from . import signals
from . import widgets
from . import xmms

class FetcherThread(threading.Thread):
  def __init__(self, lyrics, info, url=None):
    self.lyrics = lyrics
    self.info = info
    self.url = url
    self.abort = False

    super(FetcherThread, self).__init__()
    self.setDaemon(True)

  def save_lyrics(self, lyrics):
    self.lyrics.xs.medialib_property_set(
        self.info['id'], 'lyrics', lyrics, 'client/generic', sync=False)

  def from_url(self):
    self.lyrics.set_info("fetching lyrics...")

    lyrics = lyricwiki.get_lyrics(self.url)

    if self.abort:
      return

    if lyrics:
      self.save_lyrics(lyrics)
      self.lyrics.set_lyrics(lyrics)
    else:
      self.lyrics.set_info("some kind of error occurred while fetching the lyrics, try again!")

  def run(self):
    if self.url:
      self.from_url()
      return

    self.lyrics.set_info("searching for lyrics...")

    artist, title = self.info.get('artist'), self.info.get('title')

    if not artist or not title:
      self.lyrics.set_info("artist or title not set, not enough info to search for lyrics")
      return

    lw = lyricwiki.LyricWiki(artist, title, self.info.get('album'), self.info.get('tracknr'))
    lyrics = lw.get()

    if lyrics:
      self.save_lyrics(lyrics)
    else:
      self.lyrics.set_info("no direct match, searching for results...")
      results = lw.get_song_results()

    if self.abort:
      return

    if lyrics:
      self.lyrics.set_lyrics(lyrics)
    else:
      self.lyrics.show_results(results)


class ResultsFetcherThread(threading.Thread):
  def __init__(self, lyrics, query):
    self.lyrics = lyrics
    self.query = query
    self.abort = False

    super(ResultsFetcherThread, self).__init__()
    self.setDaemon(True)

  def run(self):
    self.lyrics.set_info("searching...")
    signals.emit('need-redraw')

    results = lyricwiki.get_google_results(self.query)

    if self.abort:
      return
    
    self.lyrics.show_results(results)


class LyricsListBox(urwid.ListBox):

  def set_rows(self, rows):
    self.body = urwid.SimpleListWalker(rows)
    urwid.connect_signal(self.body, "modified", self._invalidate)
    self._invalidate()

  def keypress(self, size, key):
    k = self.__super.keypress(size, key)
    if k in ('up', 'down'):
      # don't let a focus change happen in the pile if up or down are unhandled
      return None
    return k


class ResultsListBox(LyricsListBox, listbox.AttrListBox):

  def __init__(self, lyrics, body):
    self.lyrics = lyrics
    self.__super.__init__(body, attr='default', focus_attr='focus', focus_str='-focus')

  def cmd_activate(self, args):
    f = self.get_focus()
    if f and f[0]:
      self.lyrics.fetch_lyrics(f[0].url)


class Lyrics(urwid.Pile):
  context_name = 'lyrics'

  def __init__(self, app):
    self.app = app
    self.xs = xmms.get()

    self.on_display = False
    self.info = None
    self.fetcher_thread = None
    self.results_fetcher_thread = None
    self.lock = threading.RLock()

    self.input = widgets.InputEdit(caption='search lyricwiki.org > ')
    urwid.connect_signal(self.input, 'done', self.search)

    self.info_w = urwid.Text('')

    self.llb = LyricsListBox([])
    self.llbw = urwid.Padding(self.llb, 'center', ('relative', 95))
    self.rlb = ResultsListBox(self, [])

    blank = urwid.Text('')
    self.__super.__init__([('flow', self.input),
                           ('flow', self.info_w),
                           ('flow', blank),
                           self.llbw], 3)

    signals.connect('xmms-playback-current-info', self.on_xmms_playback_current_info)

  def on_xmms_playback_current_info(self, info):
    self.info = info
    if self.on_display:
      self.fetch_lyrics()

  def search(self, widget, query):
    if self.results_fetcher_thread:
      self.results_fetcher_thread.abort = True
    self.results_fetcher_thread = ResultsFetcherThread(self, query)
    self.results_fetcher_thread.start()

  def fetch_lyrics(self, url=None):
    try:
      self.lock.acquire()

      self.set_lyrics('')

      if self.fetcher_thread:
        self.fetcher_thread.abort = True

      if not url:
        lyrics = self.info.get('lyrics')

        s = "%s %s" % (self.info.get('artist', ''), self.info.get('title', ''))
        self.input.set_edit_text(s)
        self.input.edit_pos = len(s)

        if lyrics:
          self.set_lyrics(lyrics)
          return
      self.fetcher_thread = FetcherThread(self, self.info, url)
      self.fetcher_thread.start()
    finally:
      self.lock.release()

  def set_lyrics(self, lyrics):
    try:
      self.lock.acquire()

      in_list_w = self.widget_list[-1]
      if in_list_w != self.llbw:
        self.widget_list[-1] = self.llbw
        if self.focus_item == in_list_w:
          self.set_focus(self.llbw)

      if not self.info.get('lyrics'):
        self.info[('client/generic', 'lyrics')] = lyrics

      self.llb.set_rows([urwid.Text(l) for l in lyrics.split('\n')])
      self.set_info()
      self._invalidate()
      signals.emit('need-redraw')
    finally:
      self.lock.release()

  def show_results(self, results):
    try:
      self.lock.acquire()

      if self.widget_list[-1] != self.rlb:
        self.widget_list[-1] = self.rlb
        self.set_focus(self.rlb)

      if results:
        self.rlb.set_rows([widgets.LyricResultWidget(r[0], r[1]) for r in results])
        self.set_info()
      else:
        self.set_info("no results found :/")

      self._invalidate()
      signals.emit('need-redraw')
    finally:
      self.lock.release()

  def set_info(self, msg=""):
    self.info_w.set_text(msg)
    self._invalidate()
    signals.emit('need-redraw')

  def cmd_cycle(self, args=None):
    cur = self.widget_list.index(self.focus_item)
    n = len(self.widget_list)
    i = (cur + 1) % n
    while i != cur and not self.widget_list[i].selectable():
      i = (i + 1) % n
    self.set_focus(i)

  def tab_loaded(self):
    self.on_display = True

    if not self.info:
      self.on_xmms_playback_current_info(self.xs.playback_current_info())

    self.fetch_lyrics()

  def tab_unloaded(self):
    self.on_display = False

  def get_contexts(self):
    return [self, self.widget_list[-1]]

