import smtplib
from email.message import EmailMessage
def sendmail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('Mail_id','Mail_Passcode')
    msg=EmailMessage()
    msg['From']='Mail_id'
    msg['Subject']=subject
    msg['To']=to
    msg.set_content(body)
    server.send_message(msg)
    server.quit()


