#!/bin/sh

########################################################
# mail_it.sh
# A bash script that sends email as either plain text or HTML. It allows
# multiple recipients, CC addresses, reply-to addresses, and attachments.
#
# Usage: mail_it.sh -s subject -m message -f from_address \
#                   -t to_address,[...] [-c cc_address,[...]] [-r reply_to_address,[...]] \
#                   [-a attachment,[...]] [-h]
#
# subject:        email subject
# message:        email message text
# from_address:   sender address
# to_address:     one or more comma-separated recipient addresses
# cc_address:     one or more comma-separated CC addresses
# reply_to_address: one or more comma-separated reply-to addresses
# attachment:     one or more files to be attached to the email
# -h:             send message text as html
#
# Examples:
# mail_it.sh -s "This is a test message" \
#            -m "Test email body" \
#            -f "sender@abc.com" \
#            -t "recip1@abc.com,recip2@abc.com" \
#            -a "file1.pdf file2.pdf"
#
# mail_it.sh -s "This is a test message" \
#            -m "<h1>Heading</h1><pre>Unformatted Text</pre>" \
#            -f "sender@abc.com" \
#            -t "recip1@abc.com,recip2@abc.com" \
#            -h
########################################################

# Process command line arguments.
USAGE="Usage: mail_it.sh -s subject -m message -f from_address -t to_address,[...] [-c cc_address,[...]] [-r reply_to_address,[...]] [-a attachment,[...]] [-h]"
HTML_N=""
while getopts s:m:f:t:c:r:a:h arguments
do
    case $arguments in
        s) SUBJECT=$OPTARG;;
        m) MESSAGE=$OPTARG;;
        f) FROM=$OPTARG;;
        t) SEND_TO=$OPTARG;;
        c) CC=$OPTARG;;
        r) REPLY_TO=$OPTARG;;
        a) ATTACHMENTS=$OPTARG;;
        h) HTML_N=1;;
        *) echo "$USAGE"; exit 1;;
    esac
done

# Verify that required arguments are set.
if [[ "$SUBJECT" == "" || "$MESSAGE" == "" || "$FROM" == "" || "$SEND_TO" == "" ]]
then
    echo "$USAGE" >&2
    exit 1
fi

# Verify that FROM is a single address.
function VerifyAddress {
    if (( $(echo "$2" | sed "s/[,;:]/ /g" | wc -w) != 1 ))
    then
        echo "ERROR: '$1' must be a single address" >&2
        exit 1
    fi
}

VerifyAddress "-f from_address" "$FROM"

# Verify that all attachments exist.
if [[ "$ATTACHMENTS" != "" ]]
then
    for ATTACHMENT in $ATTACHMENTS
    do
        if [[ ! -f "$ATTACHMENT" ]]
        then
            echo "ERROR: Attachment '$ATTACHMENT' not found" >&2
            exit 1
        fi
    done
fi

# Create the MIME email message.
NL="\n"
BOUNDARY="alb2c34de456f"
MSG="From: $FROM${NL}To: $SEND_TO"

if [[ "$CC" != "" ]]
then
    MSG="$MSG${NL}Cc: $CC"
fi

if [[ "$REPLY_TO" != "" ]]
then
    MSG="$MSG${NL}Reply-To: $REPLY_TO"
fi

MSG="$MSG${NL}Subject: $SUBJECT"
MSG="$MSG${NL}MIME-Version: 1.0"
MSG="$MSG${NL}Content-Type: multipart/mixed; boundary=$BOUNDARY"
MSG="$MSG${NL}--$BOUNDARY"

if [[ "$HTML_N" != "" ]]
then
    MSG="$MSG${NL}Content-Type: text/html; charset=\"us-ascii\""
    MESSAGE="<!DOCTYPE html><html><body>${NL}${MESSAGE}${NL}</body></html>"
else
    MSG="$MSG${NL}Content-Type: text/plain; charset=\"us-ascii\""
fi

MSG="$MSG${NL}${MESSAGE}"

# Add attachments, if any.
for ATTACHMENT in $ATTACHMENTS
do
    FILENAME=$(basename $ATTACHMENT)
    MSG="$MSG${NL}--$BOUNDARY"
    MSG="$MSG${NL}Content-Transfer-Encoding: base64"
    MSG="$MSG${NL}Content-Type: application/octet-stream; name=$FILENAME"
    MSG="$MSG${NL}${NL}$(base64 $ATTACHMENT)"
done

MSG="$MSG${NL}--$BOUNDARY--"

# Send the email.
echo "$MSG" | sendmail -t
