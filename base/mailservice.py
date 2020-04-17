import json
import string
from json.decoder import JSONDecodeError

import yagmail
from fileloghelper import Logger

try:
    import base
    import base.statistics
    from base.utils import (InvalidParameterError, UserAuthenticationObject,
                            exec_sql, file_paths, ranstr, session_length)
except ImportError:
    if __name__ != "__main__":
        raise ImportError("Unable to import necessary modules.")
    from utils import file_paths

logger = Logger("logs/mailservive.log", "mailservice", True, True)
REGISTRATION_TEMPLATE = """Hi ${username},
thanks for signing up to Helix!
When did you? ${djoined}
Please click this link to complete your registration and activate your account: ${link}
"""
VERIFICATION_TEMPLATE = """Hi ${username},
you recently changed your email address. Therefore it needs to be verified so we know, you're who you pretend 😉. To do, please open this link: ${link}
Thanks!
"""
with open(file_paths["config.json"], "r") as f:
    mail = json.loads(f.read())
yag = yagmail.SMTP(mail["email"]["email"], password=mail["email"]["password"])


def send_email(TO, CONTENT, SUBJECT="", ATTACHMENTS=None, verbose=True):
    """Sends an email from FROM to TO, with content CONTENT and (optionally) subject SUBJECT and/or attachments ATTACHMENTS"""
    logger.context = "send_mail"
    try:
        yag.send(to=TO, subject=SUBJECT, contents=CONTENT,
                 attachments=ATTACHMENTS)
        logger.success("sent email to " + TO + ": " + SUBJECT, verbose)
    except Exception as e:
        logger.warning(
            "unable to send email because of the following exception")
        logger.handle_exception(e)


def register(username: str, email: str, first_name: str, last_name: str, djoined: str, verification=False):
    """if verification, this is not really a registration, so the email content needs to be changes even when the technical side stays the same"""
    logger.context = "register"
    with open(file_paths["config.json"], "r") as f:
        config = json.load(f)
    if config.get("skip-email-verification", False):
        logger.debug("Skipping email registration.")
        return False
    logger.debug(f"Registering user {username}…")
    identilink = ranstr()
    link = "http://helix2.ddns.net/verify/" + identilink
    with open(file_paths["new_users.json"], "r") as f:
        try:
            userobj = json.loads(f.read())
        except JSONDecodeError:
            with open(file_paths["new_users.json"], "w") as file:
                file.write("{}")
            userobj = {}
    userobj[identilink] = username
    with open(file_paths["new_users.json"], "w") as f:
        f.write(json.dumps(userobj))
    if not verification:
        temp = string.Template(REGISTRATION_TEMPLATE)
    else:
        temp = string.Template(VERIFICATION_TEMPLATE)
    content = temp.substitute(username=username, djoined=djoined, link=link)
    if verification:
        subject = "Your Helix Account"
    else:
        subject = "Your Helix registration"
    send_email(email, content, subject)
    return True


def verify_user(identilink: str):
    logger.context = "verify_user"
    with open(file_paths["new_users.json"], "r") as f:
        d = json.loads(f.read())
    try:
        user = d[identilink]
        exec_sql(f"UPDATE users SET verified=1 WHERE username='{user}'")
        logger.success(f"Verified user '{user}'")
        with open(file_paths["new_users.json"], "w") as f:
            del d[identilink]
            f.write(json.dumps(d))
        return True
    except KeyError:
        return False


def remove_identilink(identilink: str):
    logger.context = "remove_identilink"
    with open(file_paths["new_users.json"], "r") as f:
        links = json.loads(f.read())
    try:
        del links[identilink]
        with open(file_paths["new_users.json"], "w") as f:
            f.write(json.dumps(links))
    except KeyError:
        e = InvalidParameterError("Identilink not found")
        logger.handle_exception(e)
        raise e


def subcribe_to_newsletter(user: UserAuthenticationObject):
    logger.context = "subscribe_to_newsletter"
    exec_sql(f"UPDATE users SET newsletter=1 WHERE username='{user.username}'")
    logger.success(f"Subscribed '{user.username}' to newsletters", False)


def unsubscribe_newsletter(username: str):
    logger.context = "unsubscribe_newsletter"
    exec_sql(f"UPDATE users SET newsletter=0 WHERE username='{username}'")
    logger.success(f"Unsubscribed '{username}' from newsletters", False)


def send_user_data(uao: UserAuthenticationObject):
    try:
        logger.context = "send_user_data"
        user = base.get_user(uao)
        sessions = base.statistics.get_sessions(uao)
        user_data = {"username": uao.username,
                     "password": uao.raw_password, "dateJoined": user.get("joined"), "email": user.get("email"), "sessions": []}
        for s in sessions:
            user_data["sessions"].append(
                {"start": s.get("start"), "end": s.get("end"), "duration": session_length(s)})
        filecontent = json.dumps(user_data)
        fname = file_paths["repo"] + "userData.json"
        with open(fname, "w") as f:
            f.write(filecontent)
        text = """Hi username,
        you recently requested your personal user data. So here you have it (in json format). Thanks for using Helix!
        Bye!\n\n
        """.replace("username", uao.username)
        text += filecontent
        send_email(user.get("email"), text, "Your Helix data")
    except Exception as e:
        logger.handle_exception(e)
        raise e


class Newsletter:
    def __init__(self, send_to_all: bool, content: str, subject: str, addressees: list = None, attachments=None):
        """base.mailservice.send_newsletter() will automatically try to replace 'username' in content with username if 'addressees' is list of user info dicts or None"""
        self.send_to_all: bool = send_to_all
        self.addressees = addressees
        self.content = content
        self.subject = subject
        self.attachments = attachments
        self.addressee_type = None
        if addressees != None:
            for i in self.addressees:
                if self.addressee_type == None:
                    self.addressee_type = type(i)
                elif type(i) == self.addressee_type:
                    continue
                else:
                    raise TypeError("List has items of different types")
            if self.addressee_type != str and self.addressee_type != dict:
                raise TypeError(
                    "'adressees' contains invalid types (str & dict supported)")


def send_newsletter(newsletter: Newsletter):  # TODO: more testing
    """This will automatically try to replace '${username}' in content with username if 'addressees' is list of user info dicts or None"""
    logger.context = "send_newsletter"
    logger.debug("trying to send newsletter: " + newsletter.subject, True)
    newsletter.content += "\n\nDon't want these emails anymore? http://helix2.ddns.net/unsubscribe?username=${username}"
    temp = string.Template(newsletter.content)
    if newsletter.send_to_all:
        users = base.get_all_users()
        logger.progress(x=0, description="Sending newsletter...",
                        startx=0, maxx=len(users))
        for u in users:
            if u.get("username") == "tester":
                continue
            mail_content = temp.substitute(username=u.get("username"))
            send_email(u.get("email"), mail_content,
                       newsletter.subject, newsletter.attachments, False)
            logger.progress(users.index(u) + 1)
    else:
        if newsletter.addressees == None:
            users = base.get_all_users(newsletter_only=True)
            logger.progress(
                x=0, description="Sending newsletter...", startx=0, maxx=len(users))
            for u in users:
                if u.get("username") == "tester":
                    continue
                mail_content = temp.substitute(username=u.get("username"))
                send_email(u.get("email"), mail_content,
                           newsletter.subject, newsletter.attachments, False)
                logger.progress(users.index(u) + 1)
        elif newsletter.addressee_type == str:
            logger.progress(x=0, description="Sending newsletter...",
                            startx=0, maxx=len(newsletter.addressees))
            for email in newsletter.addressees:
                mail_content = newsletter.content.replace(
                    "${username}", "there")
                send_email(email, mail_content,
                           newsletter.subject, newsletter.attachments, False)
                logger.progress(newsletter.addressees.index(email) + 1)
        elif newsletter.addressee_type == dict:
            logger.progress(x=0, description="Sending newsletter...",
                            startx=0, maxx=len(newsletter.addressees))
            for user in newsletter.addressees:
                if user.get("username") == "tester":
                    continue
                try:
                    mail_content = temp.substitute(
                        username=user.get("username"))
                    send_email(user["email"], mail_content,
                               newsletter.subject, newsletter.attachments, False)
                except KeyError:
                    logger.show_error(
                        KeyError("error parsing user data for user " + str(user)))
                finally:
                    logger.progress(newsletter.addressees.index(user) + 1)
    logger.success("Sent newsletter " + newsletter.subject)
