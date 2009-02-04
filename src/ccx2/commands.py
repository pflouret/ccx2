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

import urwid

import widgets

__docformat__ = "restructuredtext en"

STOP_RUNNING_COMMANDS = None
CONTINUE_RUNNING_COMMANDS = 1

class CommandError(Exception): pass

_commands = set([
    'activate',
    'cycle',
    'insert',
    'mvbot',
    'mvdn',
    'mvtop',
    'mvup',
    'new',
    'pb-next',
    'pb-play',
    'pb-prev',
    'pb-stop',
    'pb-toggle',
    'quit',
    'rename',
    'rm',
    'same',
    'search',
    'tab',
    'toggle',
    'unmark-all',
])

_aliases = {
    'q': 'quit',
    'sa': 'same artist',
    'sb': 'same album',
}

_keys = {
    'enter': 'activate',
    'ctrl m': 'activate',
    'ctrl j': 'activate',
    'tab': 'cycle',
    'a': 'insert',
    'K': 'mvup',
    'J': 'mvdn',
    'home': 'mvtop',
    'end': 'mvbot',
    'n': 'new',
    'z': 'pb-prev',
    'x': 'pb-toggle',
    'c': 'pb-play',
    'v': 'pb-stop',
    'b': 'pb-next',
    'q': 'quit',
    'F2': 'rename',
    'd': 'rm',
    'del': 'rm',
    '1': 'tab 1',
    '2': 'tab 2',
    '3': 'tab 3',
    '4': 'tab 4',
    '[': 'tab prev',
    ']': 'tab next',
    ' ': 'toggle',
    'meta  ': 'unmark-all', # meta-space
}

_help = {
}

def get_command_prompt(contexts):
  w = widgets.InputEdit(caption=':')
  def f(text):
    try:
      run_command(text, contexts)
    except CommandError:
      pass # FIXME

  urwid.connect_signal(w, 'done', f)
  return w

def add_command(command):
  _commands.add(command)

def add_alias(command, alias):
  _aliases[alias] = command # XXX: check if alias exists?

def add_keybinding(command, key):
  _keys[key] = command # XXX: check if command exists?

def add_command_help_doc(command, doc, context='general'):
  _help.setdefault(context, {})[command] = doc

def run_command(command, contexts):
  if not command:
    return False

  handled = False
  for cmd, args in _unalias_command(command):
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

def run_key(key, contexts):
  if key not in _keys:
    return False

  return run_command(_keys[key], contexts)

def _split_cmd_args(s):
  l = s.split(None, 1)
  if len(l) == 1:
    l.append('')
  return tuple(l)

# TODO: detect recursive aliases
def _unalias_command(command):
  cmd, args = _split_cmd_args(command)

  if cmd not in _aliases:
    return [(cmd, args)]

  commands = _unchain_command(_aliases[cmd]) # ['c 1 2', 'd']

  r = []
  for c in commands:
    r.extend(_unalias_command(c))

  r[-1] = (r[-1][0], (r[-1][1] + ' ' + args).strip())
  return r

def _unchain_command(s):
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

