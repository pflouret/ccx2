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

"""
Ex-like command dispatching via a prompt or keybindings
"""

__docformat__ = "restructuredtext en"

STOP_RUNNING_COMMANDS = None
CONTINUE_RUNNING_COMMANDS = 1

class CommandError(Exception): pass

_commands = set([
    'activate',
    'clear',
    'cycle',
    'insert',
    'goto',
    'move',
    'navl',
    'navdn',
    'navup',
    'navr',
    'navpgdn',
    'navpgup',
    'navhome',
    'navend',
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
    'tab',
    'toggle',
    'unmark-all',
    'volume',
])

_help = {
}

class CommandManager(object):
  def __init__(self, config):
    self.config = config

  def add_command(self, command):
    # FIXME
    _commands.add(command)

  def add_command_help_doc(self, command, doc, context='general'):
    # FIXME
    _help.setdefault(context, {})[command] = doc

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

