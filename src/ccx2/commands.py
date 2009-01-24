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

class CommandHandler(object):
  """Command handler.

  ``context`` refers to a hashable object of any kind in which the given command makes sense,
  for instance, a `Playlist` object. The ``context`` will be passed as first argument to
  the action function associated with a command.
  """

  def __init__(self):
    super(object, self).__init__(CommandHandler)

    self.by_context = {}
    self.by_command = {}
    self.by_key = {}

  def register_command(self, context, command, action):
    """Register a command in a context.

    :param command: The command name
    :param action: The action to perform when the command is run.
      The action can be a function, or a string with a command to be
      recursively fed to `run_command`, effectively creating command aliases.
      The function should receive a `context` as first parameter and a ``string``
      with the arguments for the command.
    :type context: `object`
    :type command: `str`
    :type action: ``function`` | `str`
    """
    self.by_command.setdefault(command, {})[context] = action
    self.by_context.setdefault(context, {})[command] = action

  def register_keys(self, context, command, keys):
    """Register keys associated with a command in a given context.

    :param keys: Keys to associate with the command.
    :type context: `object`
    :type command: `str`
    :type keys: `list`
    """
    if keys:
      for k in keys:
        self.by_key.setdefault(k, {})[context] = command

  def run_command(self, contexts, command, args=''):
    """Run a command.

    :param args: The arguments to the command.
    :type contexts: `list` | `object`
    :type command: `str`
    :type args: `str`
    """
    if command not in self.by_command:
      return False

    if not hasattr(contexts, '__iter__'):
      contexts = [contexts]

    for context in contexts:
      try:
        action = self.by_command[command][context]
        break
      except KeyError:
        pass
    else:
      return False # TODO: error message

    if callable(action):
      action(context, args) # TODO: catch a CommandError exception or something
      return True
    else:
      l = action.split()
      command = l[0]
      args = len(l) > 1 and l[1].strip() or ''

      # XXX: use the context the command was found in or send all contexts?
      return self.run_command(context, command, args)

  def run_key(self, contexts, key):
    """Run the command bound to a key.

    :type contexts: `list` | `object`
    :type key: `str`
    """
    if key not in self.by_key:
      return False

    if not hasattr(contexts, '__iter__'):
      contexts = [contexts]

    for context in contexts:
      try:
        action = self.by_key[key][context]
        break
      except KeyError:
        pass # TODO: error message
    else:
      return False

    l = action.split()
    command = l[0]
    args = len(l) > 1 and l[1].strip() or ''

    # XXX: use the context the command was found in or send all contexts?
    return self.run_command(context, command, args)

  def get_command_prompt(self, contexts):
    """Return an `InputEdit` prompt that will run the specified command.

    :type contexts: `list` | `object`
    """
    def _process_command_input(text):
      l = text.strip().split(' ', 1)
      command = l[0]
      args = len(l) > 1 and l[1].strip() or ''

      self.run_command(contexts, command, args)

    w = widgets.InputEdit(caption=':')
    urwid.connect_signal(w, 'done', _process_command_input)
    return w

