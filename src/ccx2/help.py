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

from . import urwid

from . import commands
from . import config

class Help(urwid.ListBox):
  def __init__(self, app):
    self.app = app

    keys = {}
    for key, cmd in self.app.config.keys.items():
      keys.setdefault(cmd, []).append(config.urwid_key_to_key(key))
    keys = sorted(list(keys.items()), key=lambda e: e[0])

    # ugly for py2.4, >= 2.5 has a key argument for max
    pad = len(list(sorted(keys, key=lambda e: len(e[0]), reverse=True))[0][0]) + 2
    format = '%%%ds : %%s' % pad

    rows = [urwid.Text('Keys\n====\n')]
    rows.extend(urwid.Text(format % (cmd, ', '.join(ks))) for cmd, ks in keys)
    rows.append(urwid.Divider(' '))

    rows.append(urwid.Text('Commands\n========\n'))
    for ctx in sorted(commands.help):
      rows.append(urwid.Text('%s\n%s' % (ctx, '-'*len(ctx))))
      for cmd in sorted(commands.help[ctx]):
        d = commands.help[ctx][cmd]
        t = '  :%s\n    %s\n' % (d['usage'], d['desc'].replace('\n', '\n    '))
        rows.append(urwid.Text(t))

    self.__super.__init__(rows)

