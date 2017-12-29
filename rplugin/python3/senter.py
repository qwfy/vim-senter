# TODO incomplete:
# - guard g:loaded_senter?
# - log to python-client's log?
# - auto focus browser when using jupyter_nbportal

import neovim
import json
import logging
import os
import re

try:
    import pika
except ImportError:
    pika = None

@neovim.plugin
class Senter():
    def __init__(self, nvim):
        self.nvim = nvim
        self.logger = logging.getLogger('senter')
        self.logfile = os.getenv('SENTER_DEBUG_LOG', None)
        if self.logfile:
            log_format = '%(asctime)s %(levelname)-8s (%(name)s) %(message)s'
            formatter = logging.Formatter(log_format)
            handler = logging.FileHandler(filename=self.logfile)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)


    # utility functions ----------------------------------------------
    def tell_user(self, msg):
        # TODO incomplete: what's the better way?
        self.nvim.command(f"echo '{msg}'")


    def get_input(self, name):
        v = self.nvim.funcs.input(f'Enter a value for {name}: ')
        return None if v == '' else v


    def get_address_o(self, ask=True):
        '''
        b:senter_address
        '''
        if 'senter_address' in self.nvim.current.buffer.vars:
            return self.nvim.current.buffer.vars['senter_address']
        else:
            if ask:
                new_address = self.get_input('b:senter_address')
                if new_address is not None:
                    self.nvim.current.buffer.vars['senter_address'] = new_address
                return new_address
            else:
                return None


    def get_send_config_o(self, name, ask=True):
        '''
        g:senter_transport_<filetype> default transport method for filetype
        g:senter_target_<filetype>    default target for filetype
        b:senter_transport            transport method for buffer
        b:senter_target               target for buffer
        '''

        bvars = self.nvim.current.buffer.vars
        bname = f'senter_{name}'

        def ask_input_b():
            nonlocal bname, bvars
            ipt = self.get_input(f'b:{bname}')
            if ipt is not None:
                bvars[bname] = ipt
            return ipt

        if bname in bvars:
            return bvars[bname]
        else:
            gvars = self.nvim.vars
            filetype = self.nvim.current.buffer.options['filetype']
            gname = f'senter_{name}_{filetype}'
            self.logger.debug(f'getting send config: {gname}')
            if gname in gvars:
                return gvars[gname]
            else:
                if ask:
                    return ask_input_b()
                else:
                    return None

    def process_text(self, text, target, filetype):
        '''Process the text to make it suitable for target.

        Just sending what's you want to send to a target may not work,
        since the target may not support multiline input, (like the native
        Python repl), or the target may expect the input to be in a particular
        format, (say wrapped in a Protocol Buffer message). Such things should
        be done here.
        '''
        if target == 'jupyter_console' and filetype == 'python':
            # the purpose of the newlines at the end is to
            # let jupyter console execute what we just sent
            x = remove_surrounding_empty_lines(text)
            x = dedent(x)
            x = brackete_quote(x)
            x += '\n\n\n'
            return x

        elif target == 'jupyter_nbportal' and filetype == 'python':
            x = remove_surrounding_empty_lines(text)
            x = dedent(x)
            msg = {'command': 'insert_code_at_bottom_and_execute',
                   'data': x}
            return json.dumps(msg)

        elif target == 'ghci':
            x = remove_surrounding_empty_lines(text)
            p = r'^import .+$(^import .+$|\n)*'
            match = re.match(p, x, re.M)
            if match is None:
                x = ghci_quote(x)
            else:
                rest = x[match.end():]
                imports = x[match.start():match.end()]
                imports = remove_empty_lines(imports)
                imports = imports.rstrip('\n')
                if rest == '':
                    x = imports
                else:
                    x = '\n'.join([imports, ghci_quote(rest)])
            x += '\n'
            return x

        else:
            return text


    # functions for the RabbitMQ transport ---------------------------
    def send_rmq(self, text, queue_name, times_tried=0):
        self.logger.debug(f'sending to queue: {queue_name}')

        host = 'localhost'
        self.logger.debug(f'connecting to {host}')
        params = pika.ConnectionParameters(host)
        conn = pika.BlockingConnection(params)
        chan = conn.channel()
        self.logger.debug(f'connected to {host}')

        chan.queue_declare(queue=queue_name,
                           durable=False,
                           auto_delete=True,
                           exclusive=False)
        chan.basic_publish(exchange='',
                           routing_key=queue_name,
                           body=text)

        conn.close()


    # functions for nvim's jobsend() transport
    def send_jobsend(self, text, job_id):
        # the split is necessary, see :help jobsend()
        lines = text.split('\n')
        if lines and lines[-1] != '':
            # add a newline at the end
            lines += ['']
        self.nvim.funcs.jobsend(int(job_id), lines)


    # functions for sending ------------------------------------------
    def dispatch_send(self, text):
        transport = self.get_send_config_o('transport')
        target = self.get_send_config_o('target')
        address = self.get_address_o()
        if any([transport is None,
                target is None,
                address is None]):
            self.tell_user(f'Nothing is sent, bad config.')
        else:
            data_to_send = self.process_text(
                text, target,
                self.nvim.current.buffer.options['filetype'])
            if transport == 'jobsend':
                self.send_jobsend(data_to_send, address)
            elif transport == 'rmq':
                self.send_rmq(data_to_send, address)
            else:
                self.tell_user(f'Unsupported transport method: {transport}')

    def do_send_range(self, firstline, lastline):
        self.logger.debug(f'sending range {range}')
        text = '\n'.join(self.nvim.current.buffer.range(firstline, lastline))
        self.dispatch_send(text)

    @neovim.function('SenterSend', range='', sync=True)
    def send_range(self, args):
        firstline, lastline = args
        return self.do_send_range(firstline, lastline)

    @neovim.function('SenterSendCell', range=False, sync=True)
    def send_cell(self, args):
        '''Send text between tow cell markers.

        In theory, maybe this could be done with SenterSend,
        but the regex is two complex, so do it in python.
        '''

        # guess the comment char, this maybe incorrect
        comment_string = self.nvim.current.buffer.options['commentstring']
        parts = comment_string.split('%s')
        if not parts:
            self.tell_user('Cannot find comment char.')
        else:
            marker = parts[0].strip()
            marker += ' %%'
            marker = r'^\s*' + marker
            marker = vim_regex_or(marker+r'$', marker+r' .*$')

            firstline = self.nvim.funcs.search(marker, 'bcnW')
            if firstline == 0:
                firstline = 1
            else:
                firstline += 1

            lastline = self.nvim.funcs.search(marker, 'cnW')
            if lastline == 0:
                lastline = self.nvim.funcs.line('$')
            else:
                lastline -= 1

            self.logger.debug(f'firstline={firstline}, lastline={lastline}')
            if firstline > lastline:
                self.tell_user('Nothing to send.')
            else:
                self.do_send_range(firstline, lastline)


    # functions for configuration ------------------------------------
    @neovim.command('SenterConfig', nargs='*', sync=True)
    def config(self, args):
        num_args = len(args)
        if num_args == 0:
            self.get_send_config_o('transport')
            self.get_send_config_o('target')
            self.get_address_o()
        else:
            # TODO incomplete: this is the wrong implementation
            for k, v in zip(['transport', 'target', 'address'], args):
                if v != '':
                    name = f'senter_{k}'
                    self.nvim.current.buffer.vars[name] = v


    @neovim.command('SenterClear', nargs='*', sync=True)
    def clear(self, args):
        '''Clear transport and address configuration.

        SenterClear:
            Clear all.

        SenterClear transport | target | address
            Clear specified, multiple arguments can be specified.
        '''

        num_args = len(args)
        if num_args == 0:
            names = ['transport', 'target', 'address']
        else:
            names = args
        for name in names:
            n = f'senter_{name}'
            if n in self.nvim.current.buffer.vars:
                self.nvim.command(f'unlet b:{n}')

    @neovim.command('SenterReport', sync=True)
    def report(self):
        '''View current configuration.'''
        transport = self.get_send_config_o('transport', ask=False) or ''
        target = self.get_send_config_o('target', ask=False) or ''
        address = self.get_address_o(ask=False) or ''
        result = ' '.join([
            f'transport={transport}',
            f'target={target}',
            f'address={address}'])
        self.tell_user(result)


    # auxillary functions for the .vim part --------------------------
    @neovim.function('_SenterGetGOpen', sync=True)
    def get_g_open(self, args):
        transport = self.get_send_config_o('transport')
        target = self.get_send_config_o('target')
        return f'g:senter_open_{transport}_{target}'



# text processing functions --------------------------------------
def vim_regex_or(a, b):
    return ''.join([r'\(', a, r'\|', b, r'\)'])

def remove_empty_lines(text):
    p = r'\n{2,}'
    return re.sub(p, '\n', text, count=0, flags=re.M)

def is_multiple_nonempty_lines(text):
    return re.findall(r'\n+', text.strip('\n')) != []

def ghci_quote(text):
    if is_multiple_nonempty_lines(text):
        return '\n'.join([':{', text, ':}'])
    else:
        return text

def brackete_quote(text):
    '''Quote for bracketed paste.'''

    return ''.join(['\x1B[200~', text, '\x1B[201~'])

def remove_surrounding_empty_lines(text):
    text = re.sub(r'^(\s*\n+)+', r'', text, 0)
    text = re.sub(r'(\s*\n+)+$', r'', text, 0)
    return text.strip('\n')

def dedent(text):
    '''Dedent a block of text.

    It expects the first line (if it has a first line)
    to contain characters other than spaces and tabs,
    if it doesn't, the text is left untouched.

    Mixed indentaion is not supported.
    '''

    pat = r'(?P<indent_char>[ \t])(?P=indent_char)*'
    match = re.match(pat, text)
    if match is None:
        return text
    else:
        indent_pat = match.group(0)
        return re.sub('^'+indent_pat, '', text, count=0, flags=re.M)
