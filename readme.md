Vim-SEnter enables you to send text from nvim to REPLs or other places.

It has builtin support for

- Jupyter Console
- Jupyter Notebook (additional dependency needed)
- GHCi (stack ghci)

Other REPLs can be added, if you need nothing fancy, adding support for a
new REPL is just a few lines of configuration.


## General Workflow

Here is one workflow for Jupyter Console, other REPLs are similar, but may
vary.

- Open a buffer, say `/tmp/a.py`, type some Python in it.

- Visually select the lines you want to send, and press `<Enter>` to send it.
  Other sending methods, like `<S-Enter>` to send the current cell,
  (`:help senter-cell`), and sending by range are also supported.

- A `jupyter console` will be automatically started in a vertical split and
  the text you just sent will be executed in it.


## Installation

This plugin requires neovim and Python 3.6+. (Support for vim and Python 2 will not be added,
support for 3 =< python < 3.6 can be easily added, the requirement of 3.6
comes from the use of f-string).

Just use your nvim's plugin manager to install it. For example, if you are using vim-plug:

    Plug 'qwfy/vim-senter', { 'do': ':UpdateRemotePlugins' }

If you are using other plugin managers, don't forget to execute `:UpdateRemotePlugins` after installing this plugin.

The Jupyter Console works out of the box.

If you want to send to Jupyter Notebook, you also need to install
[jupyter-nbportal](https://github.com/qwfy/jupyter-nbportal/blob/master/readme.md),
the `pika` Python library (`pip install pika` will do),
and be sure to have a look at `:help senter-jupyter-nbportal`.


## Usage, Customization and Support for New REPLs

Guide for these can be found at `:help senter`.

First have a look at the `senter-quick-start` section, then head to a specific
transport and target, like `senter-jupyter-console`.

If your choice of targets doesn't have a builtin support, or you are not happy
with the builtin support for Jupyter Console or Jupyter Notebook, head to the
section `senter-details` and section `senter-extend-example`.


## Similar Project

You may also want to consider the [jpalardy/vim-slime](https://github.com/jpalardy/vim-slime),
which is implemented in VimL. I used it for a few months,
it supports more REPLs by default.
