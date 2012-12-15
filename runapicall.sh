#!/bin/bash
# Proper header for a Bash script.

API_HOST='http://127.0.0.1:5000'
API_TOKEN=''
API_GET=''
API_POSTARG=''
API_METHODARG=''

while getopts "t:g:f:d:m:h:" optname
  do
    case "$optname" in
      "t")  # token
        API_TOKEN=', token='$OPTARG
        ;;
      "g")  # get params
        API_GET="?$OPTARG"
        ;;
      "f")  # file to use for post/put purposes
        API_POSTARG=" -d @$OPTARG"
        ;;
      "d")  # raw data to use for post/put purposes
        API_POSTARG=" -d '$OPTARG'"
        ;;
      "m")
        API_METHODARG=" -X $OPTARG"
        ;;
      "h")
        API_HOST="$OPTARG"
        ;;
      *)
    esac
  done
  ARGSTART=$OPTIND

ARGS=${@:$ARGSTART}

if [ "${ARGS[0]}" = "" ]
then
  echo "Error, please specify a valid absolute URI path."
  exit 1
fi

ABSOLUTE_URI="${ARGS[0]}"
API_KEY="thisisnotanapikey"

LOGFILE='/tmp/'${ABSOLUTE_URI//\//_}'.txt'
LOGFILE=${LOGFILE/\/_//}
LOGFILE=${LOGFILE/_.txt/.txt}

curl -H "Authentication: MC api-key=${API_KEY}${API_TOKEN}" "${API_HOST}${ABSOLUTE_URI}${API_GET}"${API_POSTARG}${API_METHODARG} -o "$LOGFILE"

AAA="curl -H \"Authentication: MC api-key=${API_KEY}${API_TOKEN}\" \"${API_HOST}${ABSOLUTE_URI}${API_GET}\"${API_POSTARG}${API_METHODARG} -o \"$LOGFILE\""

echo $AAA

python ./jsonbeautify.py $LOGFILE
