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

import ConfigParser
import StringIO
import sys

# H: horizontal | V: vertical | D: down | U: up

# unicode
UBORDER_H = u'\u2500'
UBORDER_V = u'\u2502'
UBORDER_H_D = u'\u252c'

DEFAULT_WORD_SEPARATORS = '.,~:+][}{\\/-_;"'

def key_to_urwid_key(key):
  if '-' in key and key != '-':
    key = key.replace('-', ' ', 1)
  if key == 'ctrl space':
    key = '<0>'
  key = key.replace('space', ' ')
  key = key.replace('comma', ',')
  return key

class Config(object):
  def __init__(self, path, create=False):
    self.cp = ConfigParser.SafeConfigParser()
    try:
      self.cp.read(path)
    except Exception, e:
      msg = "warning: error while reading the config file:\n%s\nusing defaults" % e
      print >> sys.stderr, msg

    self.keys = {}
    self.aliases = {}
    self._formatting = {}

    self._read_keys()
    self._read_aliases()
    self._read_formatting()

  formatting = property(lambda self: self._formatting) # TODO

  def _read_keys(self):
    if not self.cp.has_section('keys'):
      return
    for cmd, keys in self.cp.items('keys'):
      keys = [k.strip() for k in keys.split(',')]
      for k in keys:
        self.keys[k] = cmd
        # TODO: multiple commands to the same key (context based) ?
        # self.keys.setdefault(key_to_urwid_key(k), []).append(cmd)

  def _read_aliases(self):
    if self.cp.has_section('aliases'):
      self.aliases = dict(self.cp.items('aliases'))

  def _read_formatting(self):
    cp = self.cp.has_section('formatting') and self.cp or default_cp
    self._formatting = dict(cp.items('formatting'))


DEFAULT_CONFIG = """
[aliases]
q = quit
sa = same artist
sb = same album
s = search

[keys]
activate = enter,  ctrl-m,ctrl-j
cycle = tab
insert = a
insert +1 = w
goto playing = g
move = m
move -1 = K
move +1 = J
navl = h
navdn = j
navup = k
navr = l
navpgdn = page-down
navpgup = page-up
navhome = home
navend = end
new = n
pb-prev = z
pb-toggle = x
pb-play = c
pb-stop = v
pb-next = b
quit = q
; rehash =
rename = #
rm = d,del
; same =
; save =
; search =
seek +5 = >
seek -5 = <
tab 1 = 1,f1
tab 2 = 2,f2
tab 3 = 3,f3
tab 4 = 4,f4
tab prev = [
tab next = ]
toggle ; navdn = space
navup ; toggle = ctrl-space
unmark-all = meta-space
volume +2 = +,=
volume -2 = -

[formatting]
search = [:c?:p|:a] \> :l \> [#[:partofset.]:n ][:c?:a \>] :t
simple = :a \> :t [:c?+:p+]
nowplaying =
  :status:CR:CR
  :a:CR
  [:n. ]:t:CR
  :l[:c? (:p)][ CD:partofset]:CR
  [:d][ :g][ {:publisher}]:CR
  [#:id][ :{bitrate}bps][ :{samplerate}Hz:CR
  :CR
  \[:elapsed[/:total]\]
"""

default_cp = ConfigParser.SafeConfigParser()
default_cp.readfp(StringIO.StringIO(DEFAULT_CONFIG))

#for k, v in Config('nccx2.conf').formatting.items(): print '%r\n%s\n\n' % (k,v)
