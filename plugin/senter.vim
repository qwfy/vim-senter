if exists('g:loaded_senter')
    finish
endif
let g:loaded_senter = 1

" set address, optionally open transport and/or target
function! s:SetAddress() abort
    if !exists('b:senter_address')
        let gopen = _SenterGetGOpen()
        if exists(gopen)
            " TODO incomplete: do we also need to remember the tab id?
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


" functions that returns addresses,
" optionally by opening a new transport and/or target
" ====================================================================
function! SenterSplitJobsend(cmd) abort
    vnew
    let job_id = termopen(a:cmd)
    return job_id
endfunction

function! Senter_jobsend_jupyter_console() abort
    return SenterSplitJobsend(g:senter_openconfig_jobsend_jupyter_console_command)
endfunction

function! Senter_jobsend_ghci() abort
    return SenterSplitJobsend(g:senter_openconfig_jobsend_ghci_command)
endfunction

function! Senter_rmq_jupyter_nbportal() abort
    return expand("%:p:.:gs?/?;?:gs?\.py$?.ipynb?")
endfunction


" key maps
" ====================================================================
if !exists('g:senter_map')
    let g:senter_map = 1
endif
if g:senter_map == 1
    nnoremap <S-ENTER> :SenterSendCell<CR>
    xnoremap <ENTER> :'<,'>SenterSend<CR>
endif


" status line
" ====================================================================
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
