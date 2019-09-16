import os, settings, smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from util.decorator import async
from util.printing import debugException

@async
def sendEmail(recipients, text_body, html_body=None, subject=settings.MAIL_DEFAULT_SUBJECT,
               sender=settings.MAIL_DEFAULT_SENDER, data=None, attachments=[]):
    """
    Send an Email asynchronously to recipients
    :param recipients:  list
    :param text_body:   str
    :param html_body:   str
    :param subject:     str
    :param sender:      str
    :param data:        dict
    :param attachments: list
    :return:            None
    """

    try:
        if data is not None:
            text_body += "\r\n\n"
            for key, value in data.items():
                text_body += "{}: {}\n".format(key,value)
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