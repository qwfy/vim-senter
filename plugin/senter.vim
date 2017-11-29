if exists('g:loaded_senter')
    finish
endif
let g:loaded_senter = 1

function! s:SetAddress() abort
    if !exists('b:senter_address')
        let gopen = _SenterGetGOpen()
        if exists(gopen)
            let orig_winid = win_getid()
            let F = function(eval(gopen))
            let senter_address = F()
            call win_gotoid(orig_winid)
            let b:senter_address = senter_address
        endif
    endif
endfunction

function! s:HelpSenterSend(startline, endline) range abort
    call s:SetAddress()
    if !exists('b:senter_address')
        echoerr 'Nothing is sent: address is not set.'
    else
        call SenterSend(a:startline, a:endline)
    endif
endfunction

function! s:HelpSenterSendCell() abort
    call s:SetAddress()
    if !exists('b:senter_address')
        echoerr 'Nothing is sent: address is not set.'
    else
        call SenterSendCell()
    endif
endfunction

command -range -nargs=0 SenterSend call s:HelpSenterSend(<line1>, <line2>)
command -nargs=0 SenterSendCell call s:HelpSenterSendCell()

if !exists('g:senter_no_map')
    nnoremap <S-ENTER> :SenterSendCell<CR>
    xnoremap <ENTER> :'<,'>SenterSend<CR>
endif

function! SenterStatusLine() abort
    if &buftype == 'terminal'
        return 'Job '. b:terminal_job_id
    else
        let bnumber = bufnr('%')
        if exists('b:senter_address')
            return join([bnumber, b:senter_address], ' => ')
        else
            return bnumber
        endif
    endif
endfunction


" Settings for specific transports and targets
if !exists('g:senter_open_jobsend_jupyter_console')
    let g:senter_open_jobsend_jupyter_console = 'SenterJobsendJupyterConsole'
endif

if !exists('g:senter_open_jobsend_jupyter_console_command')
    let g:senter_open_jobsend_jupyter_console_command = 'jupyter console'
endif

function! SenterJobsendJupyterConsole() abort
    vnew
    let job_id = termopen(g:senter_open_jobsend_jupyter_console_command)
    return job_id
endfunction


if !exists('g:senter_open_rmq_jupyter_nbportal')
    let g:senter_open_rmq_jupyter_nbportal = 'SenterRmqJupyterNbportal'
endif

function! SenterRmqJupyterNbportal() abort
    " When sending to jupyter_nbportal via rmq,
    " use a modified version of the file name as address:
    " - get the relative file name, relative to current directory
    " - replace slashes with semicolons
    " - if file ends with .py, replace it with .ipynb
    return expand("%:p:.:gs?/?;?:gs?\.py$?.ipynb?")
endfunction
