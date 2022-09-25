import os, settings, smtplib, requests, json
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from util.pyasync import thread
from util.printing import debugException
import phonenumbers, globals


# more gateways available:
# https://kb.sandisk.com/app/answers/detail/a_id/17056/~/list-of-mobile-carrier-gateway-addresses
# https://www.fbbbrown.com/garmin-connect-iq/help-faq/list-of-mobile-carrier-gateway-addresses/
CARRIER_SMS_GATEWAYS = {
    'alltel':       '@mms.alltelwireless.com',
    'att':          '@mms.att.net',
    'tmobile':      '@tmomail.net',
    'verizon':      '@vtext.com',
    'sprint':       '@pm.sprint.com',
    'boost':        '@myboostmobile.com',
    'cricket':      '@mms.cricketwireless.net',
    'metro':        '@mymetropcs.com',
    'tracfone':     '@mmst5.tracfone.com',
    'uscellular':   '@mms.uscc.net',
    'virgin':       '@@vmpix.com',
    'straighttalk': '@mypixmessages.com'
}

# TODO: only tested with the following carriers:
#       sprint, verizon, att
#       possibly get a hold of telnyx and ask for possible responses for carrier name
#       ref: https://developers.telnyx.com/docs/api/v1/number-lookup
def normalizeCarrierName(carrier):
    """
    Normalize carrier name from telnyx to match our mappings

    :param carrier:     name from external carrier lookup
    :type carrier:      str
    :return:            normalized name
    :rtype:             str
    """

    name = carrier.lower()
    if 'verizon wireless' in name:
        return 'verizon'
    elif 'cingular wireless' in name:
        return 'att'
    elif 'sprint' in name:
        return 'sprint'
    else:
        return name

@thread
def sendEmail(recipients, text_body, html_body=None, subject=settings.MAIL_DEFAULT_SUBJECT,
               sender=settings.MAIL_DEFAULT_SENDER, data=None, attachments=()):
    """
    Send an Email asynchronously to recipients

    :param recipients:      email addresses we are sending to
    :type recipients:       list|tuple
    :param text_body:       email plain text message to send
    :type text_body:        str
    :param html_body:       email html message to send
    :type html_body:        str
    :param subject:         subject of the email
    :type subject:          str
    :param sender:          email address we are sending from
    :type sender:           str
    :param data:            key, value pairs to add to message
    :type data:             dict
    :param attachments:     list|tuple
    :type attachments:      files to attach to email
    :return:                no return value
    :rtype:                 None
    """

    try:
        if data is not None:
            text_body += "\r\n\n"
            for key, value in data.items():
                text_body += "{}: {}\n".format(str(key),str(value))
            text_body += "\n"

        # print("Creating email")
        msg_root = MIMEMultipart('alternative')
        msg_root['From'] = sender
        msg_root['To'] = ", ".join(recipients)
        msg_root['Subject'] = subject
        msg_root.preamble = "|-------------------MULTIPART_BOUNDARY-------------------|\n"

        # print("Adding text body to email")
        msg_root.attach(MIMEText(text_body, 'plain'))

        if html_body is not None and html_body != "":
            # print("Adding html body to email")
            msg_root.attach(MIMEText(html_body, 'html'))

        if len(attachments) > 0:
            # print("Adding attachments to email")
            for file in attachments:
                with open(file, 'rb') as fp:
                    msg_attachments = MIMEBase('application', "octet-stream")
                    msg_attachments.set_payload(fp.read())
                encoders.encode_base64(msg_attachments)
                msg_attachments.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file))
                msg_root.attach(msg_attachments)

        # print("sending email")
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            server.connect(settings.MAIL_SERVER, settings.MAIL_PORT)
            server.ehlo()
            if settings.MAIL_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            msg_root_str = msg_root.as_string()
            server.sendmail(sender, recipients, msg_root_str)
            server.quit()

    except Exception as ex:
        debugException(ex, log_ex=False, print_ex=True, showstack=False)

def sendSMS(recipients, text_body, html_body=None, subject=settings.MAIL_DEFAULT_SUBJECT,
               sender=settings.MAIL_DEFAULT_SENDER, data=None, attachments=()):
    """
    Send an SMS Message asynchronously to recipients

    :param recipients:      email addresses we are sending to
    :type recipients:       list|tuple
    :param text_body:       email plain text message to send
    :type text_body:        str
    :param html_body:       email html message to send
    :type html_body:        str
    :param subject:         subject of the email
    :type subject:          str
    :param sender:          email address we are sending from
    :type sender:           str
    :param data:            key, value pairs to add to message
    :type data:             dict
    :param attachments:     list|tuple
    :type attachments:      files to attach to email
    :return:                no return value
    :rtype:                 None
    """

    recipients_formatted = []

    # format recipients to send through sms carrier gateway
    for recipient in recipients:
        try:
            # lookup carrier and country info
            if recipient in globals.number_info:
                number_info = globals.number_info[recipient]
            else:
                url = settings.SMS_NUMBER_LOOKUP_URL + recipient
                number_data = json.loads(requests.get(url).text)
                number_info = {
                    'country_code': number_data['country_code'],
                    'carrier_name': normalizeCarrierName(number_data['carrier']['name'])
                }
                globals.number_info[recipient] = number_info

            # lookup sms gateway for carrier and format number
            sms_gateway = CARRIER_SMS_GATEWAYS[number_info['carrier_name']]
            number = str(phonenumbers.parse(recipient, number_info['country_code']).national_number)
            recipients_formatted.append(number + sms_gateway)
        except Exception as ex:
            debugException(ex, log_ex=False, print_ex=True, showstack=False)
            continue

    # send email out sms carrier gateway
    sendEmail(recipients_formatted, text_body, html_body, subject, sender, data, attachments)

# TODO add support for APN and GCM push notifcations
# https://github.com/dgilland/pushjack
# https://pushjack.readthedocs.io/en/latest/

# TODO: add support for slack
