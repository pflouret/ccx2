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


# H: horizontal | V: vertical | D: down | U: up

# unicode
UBORDER_H = u'\u2500'
UBORDER_V = u'\u2502'
UBORDER_H_D = u'\u252c'

UDOUBLE_BORDER_H = u'\u2550'
UDOUBLE_BORDER_V = u'\u2551'
UDOUBLE_BORDER_H_D = u'\u2566'

# ascii
ABORDER_H = u'-'
ABORDER_V = u'|'
ABORDER_H_D = u'-'

ADOUBLE_BORDER_H = u'='
ADOUBLE_BORDER_V = u'|'
ADOUBLE_BORDER_H_D = u'='

DEFAULT_WORD_SEPARATORS = '.,~:+][}{\\/-_;"'

default_unicode_borders = {
    'h': UBORDER_H,
    'v': UBORDER_V,
    'hd': UBORDER_H_D,
    'dh': UDOUBLE_BORDER_H,
    'dv': UDOUBLE_BORDER_V,
    'dhd': UDOUBLE_BORDER_H_D,
}

default_ascii_borders = {
    'h': ABORDER_H,
    'v': ABORDER_V,
    'hd': ABORDER_H_D,
    'dh': ADOUBLE_BORDER_H,
    'dv': ADOUBLE_BORDER_V,
    'dhd': ADOUBLE_BORDER_H_D,
}

default_keybindings = {
    'general': {
        'move-left': ['h', 'left'],
        'move-up': ['k', 'up'],
        'move-down': ['j', 'down'],
        'move-right': ['l', 'right'],
        'page-up': ['ctrl u', 'page up'],
        'page-down': ['ctrl d', 'page down'],
        'move-top': ['home', 'ctrl a'],
        'move-bottom': ['end', 'ctrl e'],
        'goto-tab-n': ['1', '2', '3', '4', '5', '6', '7', '8', '9'],
        'goto-prev-tab': ['['],
        'goto-next-tab': [']'],
        'mark-and-move-down': [' '], # space
        'mark-and-move-up': ['<0>'], # ctrl space
        'return': ['enter', 'ctrl m'],
        'delete': ['d', 'delete'],
        'cancel': ['esc', 'ctrl g'],
        'quit': ['q', 'ctrl q'],
    },
    'text_edit': {
        'delete-word-backward': ['ctrl w', 'ctrl backspace'],
        'delete-word-forward': ['meta d', 'meta delete'],
    },
    'playback': {
        'play': ['x'],
        'play-pause-toggle': ['p', 'c'],
        'stop': ['s', 'backspace', 'v'],
        'next-track': ['>', 'b'],
        'previous-track': ['<', 'z'],
    },
    'playlist': {
        'play-focus': ['enter'],
        'move-marked-up': ['K'],
        'move-marked-down': ['J'],
    },
    'playlist-switcher': {
        'load': ['enter'],
        'new': ['n'],
        'rename': ['r'],
        'add-playlist-to-current': ['a'],
    },
    'collection-browser': {
        'navigate-in': ['l', 'right'],
        'navigate-out': ['h', 'left', 'backspace'],
        'add-to-playlist': ['a'],
    },
}

default_formatting = {
    'by_albumartist':
        """(or :performer :artist)
            > :album
            > (if :partofset (cat "CD" :partofset))
            > (pad :tracknr "2" "0"). 
              (if (not (= :artist :performer)) (cat :artist " - ")):title'}
        """,
    'simple':
        """(or :performer :artist) - 
            (if :partofset (cat :partofset "."))(pad :tracknr "2" "0") - 
            :title (if :compilation (cat " | " :artist))""",
    'search':
        """(or :performer :artist) - 
            (if :album (cat :album " - "))
            (if :compilation (cat :artist " - "))
            (if :partofset (cat :partofset "-"))(pad :tracknr "2" "0"). :title"""
}

keybindings = default_keybindings
formatting = default_formatting
borders = default_unicode_borders
word_separators = DEFAULT_WORD_SEPARATORS

