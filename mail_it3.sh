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
        a) ATTACHMENTS+=("$OPTARG") ;;
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

# MIME boundary
BOUNDARY="====$(date +%s%N)===="

# Prepare email headers
{
    printf "From: %s\n" "$FROM"
    printf "To: %s\n" "$SEND_TO"
    [[ -n "$CC" ]] && printf "Cc: %s\n" "$CC"
    [[ -n "$REPLY_TO" ]] && printf "Reply-To: %s\n" "$REPLY_TO"
    printf "Subject: %s\n" "$SUBJECT"
    printf "MIME-Version: 1.0\n"
    printf "Content-Type: multipart/mixed; boundary=\"%s\"\n" "$BOUNDARY"
    printf "\n--%s\n" "$BOUNDARY"

    # Email body
    if [[ -n "$HTML_N" ]]; then
        printf "Content-Type: text/html; charset=\"utf-8\"\n"
    else
        printf "Content-Type: text/plain; charset=\"utf-8\"\n"
    fi
    printf "Content-Transfer-Encoding: 7bit\n\n"

    # Wrap in HTML if needed
    if [[ -n "$HTML_N" ]]; then
        printf "<!DOCTYPE html>\n<html>\n<body>\n%s\n</body>\n</html>\n" "$MESSAGE"
    else
        printf "%s\n" "$MESSAGE"
    fi

    # Attachments
    for ATTACHMENT in "${ATTACHMENTS[@]}"; do
        FILENAME=$(basename "$ATTACHMENT")
        printf "\n--%s\n" "$BOUNDARY"
        printf "Content-Type: application/octet-stream; name=\"%s\"\n" "$FILENAME"
        printf "Content-Transfer-Encoding: base64\n"
        printf "Content-Disposition: attachment; filename=\"%s\"\n\n" "$FILENAME"
        base64 "$ATTACHMENT"
    done

    printf "\n--%s--\n" "$BOUNDARY"
} | sendmail -t