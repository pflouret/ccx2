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

"""
Ex-like command dispatching via a prompt or keybindings
"""

__docformat__ = "restructuredtext en"

STOP_RUNNING_COMMANDS = None
CONTINUE_RUNNING_COMMANDS = 1

class CommandError(Exception): pass

class CommandManager(object):
  def __init__(self, config):
    self.config = config

  def add_command(self, command):
    # FIXME
    _commands.add(command)

  def add_command_help_doc(self, command, doc, context='general'):
    # FIXME
    help.setdefault(context, {})[command] = doc

  def run_command(self, command, contexts):
    if not command:
      return False

    handled = False
    for cmd, args in self._unalias_command(command):
      if cmd not in _commands:
        continue # hmmmm...

      fun_name = 'cmd_'+cmd.replace('-', '_')

      for obj in contexts:
        if hasattr(obj, fun_name):
          r = getattr(obj, fun_name)(args)
          handled = True
        else:
          r = CONTINUE_RUNNING_COMMANDS

        if r == STOP_RUNNING_COMMANDS:
          break

    return handled

  def run_key(self, key, contexts):
    if key not in self.config.keys:
      return False

    return self.run_command(self.config.keys[key], contexts)

  def _split_cmd_args(self, s):
    l = s.split(None, 1)
    if len(l) == 1:
      l.append('')
    else:
      l[1] = l[1].strip()
    return tuple(l)

  # TODO: detect recursive aliases
  def _unalias_command(self, command):
    commands = self._unchain_command(command)

    r = []
    for c in commands:
      cmd, args = self._split_cmd_args(c)

      if cmd in self.config.aliases:
        r.extend(self._unalias_command(self.config.aliases[cmd]))
        r[-1] = (r[-1][0], (r[-1][1] + ' ' + args).strip())
      else:
        r.append((cmd, args))
    return r

  def _unchain_command(self, s):
    if ';' not in s:
      return [s]

    parts = []
    acc = ''
    i, n = 0, len(s)
    while i < n:
      c = s[i]
      if c == ';':
        if i+1 >= n:
          break
        if s[i+1] == ';':
          i += 1
        else:
          parts.append(acc)
          acc = ''
          i += 1
          continue
      acc += c
      i += 1

    if acc:
      parts.append(acc)

    return [p.strip() for p in parts]

_commands = set([
    'activate',
    'clear',
    'cycle',
    'insert',
    'goto',
    'keycode',
    'move',
    'nav',
    'new',
    'pb-next',
    'pb-play',
    'pb-prev',
    'pb-stop',
    'pb-toggle',
    'quit',
    'rehash',
    'rename',
    'rm',
    'same',
    'save',
    'search',
    'seek',
    'slow-as-hell',
    'tab',
    'toggle',
    'unmark-all',
    'volume',
])

help = {
    'global': {
        'clear': {'usage': 'clear',
                  'desc': 'Clear the current playlist.'},
        'nav': {'usage': 'nav up|down|left|right|page-up|page-down|home|end',
                'desc': 'Move cursor in a direction.'},
        'pb-next': {'usage': 'pb-next',
                    'desc': 'Jump to next song.'},
        'pb-play': {'usage': 'pb-play',
                    'desc': 'Start playback.'},
        'pb-prev': {'usage': 'pb-prev',
                    'desc': 'Jump to previous song.'},
        'pb-stop': {'usage': 'pb-stop',
                    'desc': 'Stop playback.'},
        'pb-toggle': {'usage': 'pb-toggle',
                      'desc': 'Toggle playback.'},
        'quit': {'usage': 'quit',
                 'desc': 'Exit ccx2.'},
        'rehash': {'usage': 'rehash <pattern>',
                   'desc': 'Rehash the media matched by pattern.'},
        'search': {'usage': 'search [<pattern>]',
                   'desc': 'Focus the search tab and search for pattern if provided.'},
        'seek': {'usage': 'seek +<seconds>|-<seconds>|<time>',
                 'desc': 'Seek to a relative or absolute position.\n'
                         'Time format is H:M:S, hours and minutes can be omitted.'},
        'keycode': {'usage': 'keycode',
                   'desc': 'Print a config compatible keycode.'},
        'slow-as-hell': {'usage': 'slow-as-hell',
                         'desc': "Complain about ccx2's speed."},
        'volume': {'usage': 'volume [+<value>|-<value>|<value>]',
                   'desc': 'Get or set the volume for all channels. Value range is 0-100.'},
    },
    'nowplaying': {
        'same': {'usage': 'same <fields>',
                 'desc': "Search songs in the medialib with the same field values as "
                         "the current song."},
    },
    'playlist': {
        'activate': {'usage': 'activate',
                     'desc': "Play the focused song."},
        'goto': {'usage': 'goto <pos>|playing',
                 'desc': "Go to <pos> position in playlist or currently playing song."},
        'rm': {'usage': 'rm',
               'desc': "Remove marked songs or focused song if none are marked."},
        'move': {'usage': 'move [+<pos>|-<pos>|<pos>]',
                 'desc': "Move marked songs to position or offset.\n"
                         "The focused song is moved if no songs are marked."},
        'same': {'usage': 'same <fields>',
                 'desc': "Search songs in the medialib with the same field values as "
                         "the focused song."},
        'toggle': {'usage': 'toggle [<pos>]',
                   'desc': "Toggle mark on position or focused song if no position is given."},
        'unmark-all': {'usage': 'unmark-all',
                       'desc': "Unmark all songs."},
    },
    'playlist-switcher': {
        'activate': {'usage': 'activate',
                     'desc': "Switch to focused playlist."},
        'insert': {'usage': 'insert',
                   'desc': "Add focused playlist contents to current playlist."},
        'rm': {'usage': 'rm',
               'desc': "Remove focused playlist."},
        'rename': {'usage': 'rename [<new-name>]',
                   'desc': "Rename focused playlist. Prompt for a name if none is given."},
        'new': {'usage': 'new [<name>]',
                'desc': "Create a new playlist. Prompt for a name if none is given."},
    },
    'search': {
        'cycle': {'usage': 'cycle',
                  'desc': "Cycle between the search input and results."},
        'insert': {'usage': 'insert [+<pos>|-<pos>|pos]',
                   'desc': "Insert the marked songs to a position in the playlist.\n"
                           "If no songs are marked insert the focused song.\n"
                           "If no position is given append the song to the playlist."
                           "Relative positions are relative to the current playing song.\n"},
        'save': {'usage': 'save <collection-name>',
                 'desc': "Save the current search as a collection."},
        'toggle': {'usage': 'toggle [<pos>]',
                   'desc': "Toggle mark on position or focused song if no position is given."},
        'unmark-all': {'usage': 'unmark-all',
                       'desc': "Unmark all songs."},
    },
    'tabs': {
        'tab': {'usage': 'tab <number>|<name>',
             'desc': "Focus tab by number or name."},
    }
}

