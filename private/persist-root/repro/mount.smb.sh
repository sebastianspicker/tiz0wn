#!/bin/bash

function join_by { local IFS="$1"; shift; echo "$*"; }

# debug=true
debug=${debug:=false}

UTIL=/bin/mount
UTIL_OPT=$*
SMB_PATH_OPT="smbpath="
SMB_PATH_TEMPLATE="\[:SMBPATH:\]"

function Print()
{
    [[ "$debug" == "true" ]] && echo $*
}

function read_credentials()
{
    local filename=$1
    join_by , $(sed "/$SMB_PATH_OPT/d" $filename)
}

function read_smbpath()
{
    local filename=$1
    grep ${SMB_PATH_OPT} $filename
}

Print "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv"
Print "Options: $UTIL_OPT"
if [[ $UTIL_OPT =~ (credentials=)([^,]*), ]]; then

    Print " >>>>>>>>>>>>>>>>>>>> BEGIN, MIDDLE <<<<<<<<<<<<<<<<<<< "
    Print "FileName=${BASH_REMATCH[2]}"
    FileName=${BASH_REMATCH[2]}
    FileContent=$(read_credentials $FileName)
    smbpath=$(read_smbpath $FileName)
    SMB_PATH=${smbpath/$SMB_PATH_OPT/}

    UTIL_OPT=${UTIL_OPT/credentials=${FileName}/$FileContent}
    Print "UTIL_OPT=${UTIL_OPT}"
    UTIL_OPT=${UTIL_OPT//$SMB_PATH_TEMPLATE/$SMB_PATH}
    
elif [[ $UTIL_OPT =~ (credentials=)([^ ]*) ]]; then

    Print " >>>>>>>>>>>>>>>>>>>> MIDDLE <<<<<<<<<<<<<<<<<<< "
    Print "FileName=${BASH_REMATCH[2]}"
    FileName=${BASH_REMATCH[2]}
    FileContent=$(read_credentials $FileName)
    smbpath=$(read_smbpath $FileName)
    SMB_PATH=${smbpath/$SMB_PATH_OPT/}

    UTIL_OPT=${UTIL_OPT/credentials=${FileName}/$FileContent}
    UTIL_OPT=${UTIL_OPT//$SMB_PATH_TEMPLATE/$SMB_PATH}
    
elif [[ $UTIL_OPT =~ (credentials=)(.*) ]]; then
    
    Print " >>>>>>>>>>>>>>>>>>>> END <<<<<<<<<<<<<<<<<<< "
    Print "FileName=${BASH_REMATCH[2]}"
    FileName=${BASH_REMATCH[2]}
    FileContent=$(read_credentials $FileName)
    smbpath=$(read_smbpath $FileName)
    SMB_PATH=${smbpath/$SMB_PATH_OPT/}

    UTIL_OPT=${UTIL_OPT/credentials=${FileName}/$FileContent}
    UTIL_OPT=${UTIL_OPT//$SMB_PATH_TEMPLATE/$SMB_PATH}
fi

echo  $UTIL_OPT
Print "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
[[ "$debug" == "false" ]] && /bin/bash -c "$UTIL $UTIL_OPT"


