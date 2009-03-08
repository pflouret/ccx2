ccx2
====

A console client for the XMMS2 music player.

- - -

Requirements
------------

* [XMMS2][xmms2] 0.6 DrM (a.k.a. [git development version][xmms2git] for now)
* Python >= 2.5 (might work with 2.4, untested)
* [Urwid][urwid] >= 0.9.8.3 ([mercurial dev version][urwidhg] if running python >= 2.6)
* ncurses

[xmms2]: http://xmms2.xmms.se
[xmms2git]: http://git.xmms.se/?p=xmms2-devel.git
[urwid]: http://excess.org/urwid/
[urwidhg]: https://excess.org/hg/urwid/

### Optional

For cover art display:

* The [python imaging library][pil] (PIL)
* A 256-color enabled terminal.
  (Some info on how to enable 256 colors in [xterm][xterm], [urxvt][urxvt] and [PuTTY][putty]).

[pil]: http://www.pythonware.com/products/pil/
[xterm]: http://www.frexx.de/xterm-256-notes/
[urxvt]: http://scie.nti.st/2008/10/13/get-rxvt-unicode-with-256-color-support-on-ubunut
[putty]: http://www.emacswiki.org/emacs/PuTTY#toc2

- - -

Installation
------------

    $ sudo python setup.py install

To run:

    $ ccx2

- - -

Bugs
----
Most likely!, send bug reports or comments of any kind to `quuxbaz@gmail.com`

- - -

License
-------
New BSD license, see the LICENSE file for more details.

ccx2 is copyright (c) 2008-2009, Pablo Flouret
