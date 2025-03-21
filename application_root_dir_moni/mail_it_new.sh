#!/bin/bash
# Modified by Hasitha — Fix HTML handling

USAGE="Usage: mail_it.sh -s SUBJECT -m MESSAGE -f FROM -t TO [-c CC] [-r REPLY_TO] [-a ATTACHMENT] [-h]"

NL=$'\n'
BOUNDARY="ZZ_/afg6432dfgkl.94531q"
MSG=""
ATTACHMENTS=()
HTML_N=0  # <-- Initialize as 0

while getopts s:m:f:t:c:r:a:h arguments; do
    case $arguments in
        s) SUBJECT=$OPTARG ;;
        m) MESSAGE=$OPTARG ;;
        f) FROM=$OPTARG ;;
        t) SEND_TO=$OPTARG ;;
        c) CC=$OPTARG ;;
        r) REPLY_TO=$OPTARG ;;
        a) ATTACHMENTS+=("$OPTARG") ;;
        h) HTML_N=1 ;;  # <-- Set to 1 if -h is passed
        *) echo "$USAGE"; exit 1 ;;
    esac
done

# Validate required parameters
if [[ -z "$SUBJECT" || -z "$MESSAGE" || -z "$FROM" || -z "$SEND_TO" ]]; then
    echo "$USAGE"
    exit 1
fi

# Build headers
MSG="Subject: $SUBJECT${NL}From: $FROM${NL}To: $SEND_TO"
if [[ -n "$CC" ]]; then
    MSG="$MSG${NL}Cc: $CC"
fi
if [[ -n "$REPLY_TO" ]]; then
    MSG="$MSG${NL}Reply-To: $REPLY_TO"
fi

# Handle attachments
if [[ "${#ATTACHMENTS[@]}" -eq 0 ]]; then
    MSG="$MSG${NL}MIME-Version: 1.0"
    if [[ "$HTML_N" -eq 1 ]]; then  # <-- Proper comparison
        MSG="$MSG${NL}Content-Type: text/html; charset=\"utf-8\""
        MESSAGE="<!DOCTYPE html><html><body>${NL}${MESSAGE}${NL}</body></html>"  # <-- Wrap HTML
    else
        MSG="$MSG${NL}Content-Type: text/plain; charset=\"utf-8\""
    fi
    MSG="$MSG${NL}${NL}$MESSAGE"
else
    MSG="$MSG${NL}MIME-Version: 1.0"
    MSG="$MSG${NL}Content-Type: multipart/mixed; boundary=\"$BOUNDARY\""
    MSG="$MSG${NL}${NL}--$BOUNDARY"
    if [[ "$HTML_N" -eq 1 ]]; then  # <-- Proper comparison
        MSG="$MSG${NL}Content-Type: text/html; charset=\"utf-8\""
        MESSAGE="<!DOCTYPE html><html><body>${NL}${MESSAGE}${NL}</body></html>"  # <-- Wrap HTML
    else
        MSG="$MSG${NL}Content-Type: text/plain; charset=\"utf-8\""
    fi
    MSG="$MSG${NL}Content-Transfer-Encoding: 7bit${NL}${NL}$MESSAGE${NL}"

    for ATTACHMENT in "${ATTACHMENTS[@]}"; do
        if [[ -f "$ATTACHMENT" ]]; then
            MIME_TYPE=$(file --mime-type -b "$ATTACHMENT")
            BASE64_ENCODED=$(base64 "$ATTACHMENT")
            FILENAME=$(basename "$ATTACHMENT")
            MSG="$MSG--$BOUNDARY${NL}"
            MSG="$MSGContent-Type: $MIME_TYPE; name=\"$FILENAME\"${NL}"
            MSG="$MSGContent-Transfer-Encoding: base64${NL}"
            MSG="$MSGContent-Disposition: attachment; filename=\"$FILENAME\"${NL}${NL}$BASE64_ENCODED${NL}"
        fi
    done
    MSG="$MSG--$BOUNDARY--"
fi

# Send email
echo -e "$MSG" | sendmail -t
