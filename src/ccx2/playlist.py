# Copyright (c) 2008, Pablo Flouret <quuxbaz@gmail.com>
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

import urwid
import xmmsclient

from xmmsclient import collections as coll
from xmmsclient.sync import XMMSError

import collutil
import commands
import listbox
import mif
import signals
import widgets
import xmms


class RowColumns(urwid.Columns):
  def __init__(self, song_w, pos, max_pos):
    self.song_w = song_w
    self.pos_w = urwid.Text('', align='right')
    self.pos = -1
    self.max_pos = 0

    self.__super.__init__([self.pos_w, self.song_w], focus_column=1, dividechars=1)

    self.set_pos(pos, max_pos)

  mid = property(lambda self: self.song_w.mid)

  def set_pos(self, pos, max_pos):
    if pos != self.pos:
      self.pos = pos
      self.pos_w.set_text('%d.' % (pos+1))
      self._invalidate()

    if max_pos != self.max_pos:
      self.max_pos = max_pos
      max_pos_len = len(str(max_pos))
      self.column_types[0] = ('fixed', max_pos_len+1)
      self._invalidate()


# FIXME: cleanup all the xmms-playlist-changed mess

class PlaylistWalker(urwid.ListWalker):
  def __init__(self, pls, format):
    self.pls = pls
    self.format = format
    self.parser = mif.FormatParser(format)
    self.song_widgets = {}
    self.row_widgets = {}
    self.focus = 0

    self.feeder = collutil.PlaylistFeeder(self.pls, self.parser.fields())

    try:
      self.current_pos = int(self.feeder.collection.attributes.get('position', -1))
    except ValueError:
      self.current_pos = -1

    signals.connect('xmms-medialib-entry-changed', self.on_medialib_entry_changed)
    signals.connect('xmms-playlist-current-pos', self.on_xmms_playlist_current_pos)
    signals.connect('xmms-playlist-changed', self.on_xmms_playlist_changed)

  def __len__(self):
    return len(self.feeder)

  def on_medialib_entry_changed(self, mid):
    if mid in self.song_widgets:
      del self.song_widgets[mid]
      for pos in self.feeder.id_positions(mid):
        try:
          del self.row_widgets[pos]
        except KeyError:
          pass
      signals.emit('need-redraw')

  def on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    if pls != self.pls:
      return

    if type != xmmsclient.PLAYLIST_CHANGED_ADD:
      self.row_widgets = {}

    self.set_focus(self.focus)
    signals.emit('need-redraw')

  def on_xmms_playlist_current_pos(self, pls, pos):
    if pls == self.pls and pos != self.current_pos:
      self.current_pos = pos
      signals.emit('need-redraw')

  def get_pos(self, pos):
    mid = self.feeder.position_id(pos)

    if pos < 0 or mid is None:
      return None, None

    if mid not in self.song_widgets:
      text = self.parser.eval(self.feeder[pos])
      self.song_widgets[mid] = widgets.SongWidget(mid, text)

    try:
      w = self.row_widgets[pos]
      w.set_pos(pos, len(self.feeder))
    except KeyError:
      w = self.row_widgets[pos] = RowColumns(self.song_widgets[mid], pos, len(self.feeder))

    return w, pos

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= len(self.feeder):
      focus = len(self.feeder) - 1

    self.focus = focus
    self._modified()

  def focus_current_pos(self):
    self.set_focus(self.current_pos)

  def set_focus_last(self): self.set_focus(len(self.feeder)-1)
  def get_focus(self): return self.get_pos(self.focus)
  def get_prev(self, pos): return self.get_pos(pos-1)
  def get_next(self, pos): return self.get_pos(pos+1)


class Playlist(listbox.MarkableListBox):
  context_name = 'playlist'

  def __init__(self, app):
    self.__super.__init__([])

    self.body.current_pos = -1 # filthy filthy

    self.xs = xmms.get()
    self.app = app
    self.format = 'playlist'

    self._walkers = {} # pls => walker
    self.active_pls = self.xs.playlist_current_active()
    self.view_pls = self.active_pls

    signals.connect('xmms-collection-changed', self.on_xmms_collection_changed)
    signals.connect('xmms-playlist-loaded', self.load)
    signals.connect('xmms-playlist-changed', self.on_xmms_playlist_changed)
    signals.connect('xmms-playlist-current-pos', self.on_xmms_playlist_current_pos)

    self.load(self.active_pls)

  def load(self, pls, from_xmms=True):
    focus_active = False
    if pls not in self._walkers:
      self._walkers[pls] = PlaylistWalker(pls, self.app.config.format(self.format))
      focus_active = True

    self._set_active_attr(self.body.current_pos, self._walkers[pls].current_pos)

    self.body = self._walkers[pls]

    if focus_active:
      self.set_focus(self.body.current_pos)

    if from_xmms:
      self.active_pls = pls

    self.view_pls = pls
    self._invalidate()

  def on_xmms_collection_changed(self, pls, type, namespace, newname):
    if namespace == 'Playlists':
      if type == xmmsclient.COLLECTION_CHANGED_RENAME:
        try:
          del self._walkers[pls]
          if pls == self.active_pls:
            self.load(newname)
        except KeyError:
          pass
        signals.emit('need-redraw')

  def on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    try:
      if type == xmmsclient.PLAYLIST_CHANGED_REMOVE and not pos:
        del self._walkers[pls]
    except KeyError:
      pass

  def on_xmms_playlist_current_pos(self, pls, pos):
    cp = self.body.current_pos
    self._set_active_attr(cp, pos)

    if self._bottom_pos is not None and self._top_pos is not None and \
       cp <= self._bottom_pos and cp >= self._top_pos and \
       (pos > self._bottom_pos or pos < self._top_pos):
      self.set_focus(pos)

  def cmd_activate(self, args):
    if args:
      if len(args.split()) > 1:
        raise commands.CommandError("Too many arguments, only one needed")
      try:
        pos = int(args)-1
        if pos < 0 or pos > len(self.body):
          raise ValueError
      except ValueError:
        raise commands.CommandError("valid playlist position required")
    else:
      pos = self.get_focus()[1]
    if pos is not None:
      self.xs.playlist_play(playlist=self.view_pls, pos=pos)

  def cmd_goto(self, args):
    if args == 'playing':
      self.body.focus_current_pos()
    else:
      try:
        p = int(args)
      except ValueError:
        return commands.CONTINUE_RUNNING_COMMANDS
      self.set_focus(p)

  def cmd_rm(self, args):
    m = self.marked_data
    if not m:
      w, pos = self.get_focus()
      if pos is None:
        return
      m = {pos: self.get_mark_data(pos, w)}

    for pos, w in sorted(m.items(), key=lambda e: e[0], reverse=True):
      self.xs.playlist_remove_entry(pos, self.view_pls, sync=False)

    self.unmark_all()

  def cmd_move(self, args):
    try:
      n = int(args)
    except ValueError:
      if not args:
        n = self.get_focus()[1]+1
      else:
        raise CommandError, "bad argument"

    if args and args[0] in ('+', '-'):
      if n > 0:
        self.move_down(n)
      else:
        self.move_up(-n)
    else:
      self.move_abs(n)

  def _get_marked_for_move(self, reverse=False):
    m = self.marked_data.items()
    if not m:
      w, pos = self.get_focus()
      if pos is None:
        return
      m = [(pos, self.get_mark_data(pos, w))]

    m.sort(key=lambda e: e[0], reverse=reverse)

    return m

  def move_abs(self, n, m=None):
    m = self._get_marked_for_move()

    if not m:
      return

    n -= 1
    if n > m[0][0]:
      self.move_down(n-m[0][0], reversed(m))
    else:
      self.move_up(m[0][0]-n, m)

  def move_up(self, n, m=None):
    if m is None:
      m = self._get_marked_for_move()

    top = 0
    for pos, mid in m:
      dest = pos - n

      if dest < top:
        dest = top
        top += 1

      self.xs.playlist_move(pos, dest, sync=False)
      if not self.marked_data: # moving only the focused song
        self.set_focus(dest)
      else:
        self.toggle_mark(pos, mid)
        self.toggle_mark(dest, mid)
        # TODO: scroll if moving past first row in view

  def move_down(self, n, m=None):
    if m is None:
      m = self._get_marked_for_move(reverse=True)

    bottom = len(self.body)-1
    for pos, mid in m:
      dest = pos+n

      if dest > bottom:
        dest = bottom
        bottom -= 1

      self.xs.playlist_move(pos, dest, sync=False)
      if not self.marked_data: # moving only the focused song
        self.set_focus(dest)
      else:
        self.toggle_mark(pos, mid)
        self.toggle_mark(dest, mid)
        # TODO: scroll if moving past last row in view

  def cmd_same(self, args):
    fields = args.split()
    w, p = self.get_focus()
    if w is not None:
      info = self.xs.medialib_get_info(w.mid)
      q = ' AND '.join('%s:"%s"' % (f, info[f]) for f in fields if info.get(f))
      if q:
        self.app.search(q)
      else:
        pass # TODO: error message

  def get_mark_data(self, pos, w):
    return w.mid

  def get_contexts(self):
    return [self]

  def _set_active_attr(self, prevpos, newpos):
    if prevpos != -1:
      self.remove_row_attr(prevpos, 'active')

    if newpos != -1:
      self.add_row_attr(newpos, 'active')


class PlaylistSwitcherWalker(urwid.ListWalker):
  def __init__(self):
    self.xs = xmms.get()
    self.focus = 0
    self.rows = {}
    self.playlists = []
    self.nplaylists = 0

    signals.connect('xmms-collection-changed', self.on_xmms_collection_changed)
    signals.connect('xmms-playlist-changed', self.on_xmms_playlist_changed)

    self._load()

  def __len__(self):
    return self.nplaylists

  def _load(self):
    self.playlists = [p for p in sorted(self.xs.playlist_list()) if not p.startswith('_')]
    self.nplaylists = len(self.playlists)

  def _reload(self):
    self.rows = {}
    self._load()
    if self.focus >= self.nplaylists:
      self.focus = self.nplaylists-1
    self._modified()

  def get_pos(self, pos):
    if pos < 0 or pos >= self.nplaylists:
      return None, None

    pls = self.playlists[pos]

    if pos not in self.rows:
      self.rows[pos] = widgets.PlaylistWidget(pls)

    return self.rows[pos], pos

  def get_focus(self):
    return self.get_pos(self.focus)

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= self.nplaylists:
      focus = self.nplaylists-1
    self.focus = focus
    self._modified()

  def get_prev(self, pos):
    return self.get_pos(pos-1)

  def get_next(self, pos):
    return self.get_pos(pos+1)

  def on_xmms_collection_changed(self, pls, type, namespace, newname):
    if namespace == 'Playlists' and type != xmmsclient.COLLECTION_CHANGED_UPDATE:
      self._reload()
      signals.emit('need-redraw')

  def on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    if pos is None and \
       type in (xmmsclient.PLAYLIST_CHANGED_ADD,
                xmmsclient.PLAYLIST_CHANGED_MOVE,
                xmmsclient.PLAYLIST_CHANGED_REMOVE):
      self._reload()
      signals.emit('need-redraw')


class PlaylistSwitcher(listbox.MarkableListBox):
  context_name = 'playlist-switcher'

  def __init__(self, app):
    self.__super.__init__(PlaylistSwitcherWalker())

    self.xs = xmms.get()
    self.app = app
    self.cur_active = self.xs.playlist_current_active()
    self.active_pos = 0
    self._set_active_attr(None, self.cur_active)

    signals.connect('xmms-playlist-loaded', self.on_xmms_playlist_loaded)
    signals.connect('xmms-collection-changed', self.on_xmms_collection_changed)

  def on_xmms_playlist_loaded(self, pls):
    self._set_active_attr(self.cur_active, pls)
    self.cur_active = pls
    self._invalidate()
    signals.emit('need-redraw')

  def on_xmms_collection_changed(self, pls, type, namespace, newname):
    if namespace == 'Playlists' and type != xmmsclient.COLLECTION_CHANGED_UPDATE:
      if pls == self.cur_active:
        self.cur_active = newname

      self.clear_attrs()
      self._set_active_attr(None, self.cur_active)

      signals.emit('need-redraw')

  def _set_active_attr(self, prevpls, newpls):
    try:
      if prevpls:
        prevpos = self.body.playlists.index(prevpls)
      newpos = self.body.playlists.index(newpls)
    except ValueError:
      return # shouldn't happen

    if prevpls:
      self.remove_row_attr(prevpos, 'active')

    if newpls:
      self.add_row_attr(newpos, 'active')

  def cmd_activate(self, args):
    w = self.get_focus()[0]
    if w:
      self.xs.playlist_load(w.name, sync=False)

  # FIXME: works like crap
  def cmd_insert(self, args):
    w = self.get_focus()[0]
    if w:
      # this awfulness stems from the fact that you have to use playlist_add_collection,
      # but collections in the playlist namespace don't have order, doh
      # coll2.0 should fix this mess
      idl = coll.IDList()
      cur_active = self.xs.playlist_current_active()
      ids_from = self.xs.playlist_list_entries(w.name, 'Playlists')
      ids_to = self.xs.playlist_list_entries(cur_active, 'Playlists')

      for id in ids_to+ids_from:
        idl.ids.append(id)

      self.xs.coll_save(idl, cur_active, 'Playlists')

  def cmd_rm(self, args):
    w = self.get_focus()[0]
    if w:
      self.xs.playlist_remove(w.name, sync=False)

  def cmd_rename(self, args):
    w = self.get_focus()[0]
    if w:
      def rename(widget, new_name):
        self.xs.coll_rename(w.name, new_name, 'Playlists', sync=False)
      if args:
        rename(None, args)
      else:
        self.app.show_prompt('new name: ', rename)

  def cmd_new(self, args):
    def create(widget, name):
      if name:
        self.xs.playlist_create(name, sync=False)
    if args:
      create(None, args)
    else:
      self.app.show_prompt('playlist name: ', create)

  def get_contexts(self):
    return [self]

