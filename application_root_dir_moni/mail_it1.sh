#!/bin/bash

########################################################
# mail_it.sh - Sends email with plain text or HTML and attachments.
########################################################

USAGE="Usage: mail_it.sh -s subject -m message -f from_address -t to_address,[...] [-c cc_address,[...]] [-r reply_to_address,[...]] [-a attachment,[...]] [-h]"

HTML_N=""
while getopts s:m:f:t:c:r:a:h arguments; do
    case $arguments in
        s) SUBJECT=$OPTARG ;;
        m) MESSAGE=$OPTARG ;;
        f) FROM=$OPTARG ;;
        t) SEND_TO=$OPTARG ;;
        c) CC=$OPTARG ;;
        r) REPLY_TO=$OPTARG ;;
        a) ATTACHMENTS+=("$OPTARG") ;;  # Use array for multiple attachments
        h) HTML_N=1 ;;
        *) echo "$USAGE"; exit 1 ;;
    esac
done

# Ensure required fields are set
if [[ -z "$SUBJECT" || -z "$MESSAGE" || -z "$FROM" || -z "$SEND_TO" ]]; then
    echo "ERROR: Missing required parameters." >&2
    echo "$USAGE"
    exit 1
fi

# Ensure FROM is a single email address
function VerifyAddress {
    if [[ $(echo "$2" | sed "s/[,;:]/ /g" | wc -w) -ne 1 ]]; then
        echo "ERROR: '$1' must be a single address." >&2
        exit 1
    fi
}
VerifyAddress "-f from_address" "$FROM"

# Validate attachments
for ATTACHMENT in "${ATTACHMENTS[@]}"; do
    if [[ ! -f "$ATTACHMENT" ]]; then
        echo "ERROR: Attachment '$ATTACHMENT' not found." >&2
        exit 1
    fi
done

# Construct MIME email
NL="\n"
BOUNDARY="===MIME_BOUNDARY==="
MSG="From: $FROM${NL}To: $SEND_TO"

[[ -n "$CC" ]] && MSG="$MSG${NL}Cc: $CC"
[[ -n "$REPLY_TO" ]] && MSG="$MSG${NL}Reply-To: $REPLY_TO"

MSG="$MSG${NL}Subject: $SUBJECT"
MSG="$MSG${NL}MIME-Version: 1.0"
MSG="$MSG${NL}Content-Type: multipart/mixed; boundary=$BOUNDARY"
MSG="$MSG${NL}--$BOUNDARY"

# Set email body
if [[ -n "$HTML_N" ]]; then
    MSG="$MSG${NL}Content-Type: text/html; charset=\"utf-8\""
    MESSAGE="<!DOCTYPE html><html><body>${NL}${MESSAGE}${NL}</body></html>"
else
    MSG="$MSG${NL}Content-Type: text/plain; charset=\"utf-8\""
fi
MSG="$MSG${NL}${NL}$MESSAGE"

# Attach files
for ATTACHMENT in "${ATTACHMENTS[@]}"; do
    FILENAME=$(basename "$ATTACHMENT")
    MSG="$MSG${NL}--$BOUNDARY"
    MSG="$MSG${NL}Content-Transfer-Encoding: base64"
    MSG="$MSG${NL}Content-Type: application/octet-stream; name=\"$FILENAME\""
    MSG="$MSG${NL}Content-Disposition: attachment; filename=\"$FILENAME\"${NL}"
    MSG="$MSG$(base64 "$ATTACHMENT")"
done

MSG="$MSG${NL}--$BOUNDARY--"

# Send the email
echo -e "$MSG" | sendmail -t
