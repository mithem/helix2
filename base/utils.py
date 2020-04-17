import datetime
import random
import re
import string
from hashlib import sha3_512

import pymysql.cursors
import tabulate
from fileloghelper import Logger
from pymysql.err import OperationalError

file_paths = {
    "new_users.json": "/Users/miguel/repos/helix2/new_users.json",
    "repo": "/Users/miguel/repos/helix2/",
    "config.json": "/Users/miguel/repos/helix2/config.json",
}


def exec_sql(sql_command="SELECT * FROM tasks", verbose=True, logger: Logger = None):
    """Execute sql_command on database and return None or whatever is returned from the database. If sql_command is not specified, all tasks will get returned"""
    result = None
    if logger != None and type(logger) == Logger:
        logger.context = "exec_sql"
    else:
        logger = Logger("exec_sql.log", "exec_sql", True, True)
    try:
        connection = pymysql.connect(host='localhost',
                                     user='helix_db_wrapper',
                                     password='helix_wrapper007',
                                     db='Helix',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
    except OperationalError as e:
        logger.handle_exception(e)
        raise AuthenticationError("Access denied to database")
    if verbose and logger != None:
        logger.success("connected to database", False)
    if verbose and logger != None:
        logger.debug("executing SQL-Command: " + sql_command)
    with connection.cursor() as cursor:
        cursor.execute(sql_command)
        if "SELECT" in sql_command:
            result = cursor.fetchall()
        else:
            connection.commit()
    if verbose and logger != None:
        logger.debug("SQL query returned: " + str(result))
    try:
        connection.close()
        if verbose and logger != None:
            logger.success("Shut down connection to database", False)
    except Exception as e:
        if logger != None and type(logger) == Logger:
            logger.handle_exception(e)
        else:
            print(e)
    finally:
        return result


def has_passed(tdate, date=None):
    """returns whether tdate (iso format) has passed date (now by default)"""
    if date == None:
        date = datetime.datetime.now()
    if tdate == None or tdate == "None" or tdate == "":
        return False
    if tdate[-1].lower() == "z":
        task_date = datetime.datetime.fromisoformat(tdate[:-1])
    else:
        task_date = datetime.datetime.fromisoformat(tdate)
    if type(date) == str:
        if date[-1].lower() == "z":
            date = date[:-1]
        if len(date) <= 19:
            date += ".000000"
        date = datetime.datetime.fromisoformat(date)
    return task_date < date


def check_user_parameters(username: str = None, first_name: str = None, last_name: str = None, password: str = None, email: str = None):
    """raises InvalidParameterError if values are not acceptable"""
    username_pattern = r"^[a-zA-Z]+[a-zA-Z0-9_.]$"
    name_pattern = r"^[A-ZÄÖÜ][a-zA-Z-ÄÖÜ]+$"
    password_pattern = r"^[a-zA-Z_]+[a-zA-Z0-9_.#-$%§\"!\?=&^°´`*ß+'()\{}[\]@*\\\/]+$"
    email_pattern = r"^[a-zA-Z0-9\._%+-]+@[a-zA-Z0-9.-_]+.[a-zA-Z]{2,}$"
    if username != None and not re.match(username_pattern, username):
        raise InvalidParameterError("username invalid")
    if username != None and not len(username) >= 6:
        raise InvalidParameterError("username too short")
    if first_name != None and not re.match(
            name_pattern, first_name):
        raise InvalidParameterError("first name invalid (please romanize)")
    if last_name != None and not re.match(
            name_pattern, last_name):
        raise InvalidParameterError("last name invalid (please romanize)")
    if password != None and not re.match(password_pattern, password):
        raise InvalidParameterError("password characters invalid")
    if password != None and not len(password) >= 8:
        raise InvalidParameterError("password too short")
    if email != None and not re.match(email_pattern, email):
        raise InvalidParameterError("email invalid")
    return True


def tab(header_and_content: dict, logger: Logger = None):
    headers = list(header_and_content.keys())
    data = list(header_and_content.values())
    if type(data[0]) != list:
        data = [data]
    out = tabulate.tabulate(data, headers)
    if logger != None:
        logger.debug("\n" + out)
        print(out)
    else:
        print(out)
    return out


def is_users_password(user, password):
    """returns wether the password of 'user': str is 'password'"""
    try:
        userobj = exec_sql(f"SELECT * FROM users WHERE username='{user}'")[0]
        hash = userobj.get("hash", "")
        salt = userobj.get("salt")

        user_verified = userobj.get("verified")
    except IndexError:
        return False  # if user doesn't exist, authentication fails
    real_hash = userobj.get("hash")
    is_it_hash = sha3_512(bytes(password+salt, "utf-8")).hexdigest()
    return real_hash == is_it_hash and user_verified


def authenticate(user, password):
    """Tries to return UserAuthenticationObject (pretty much deprecated)"""
    return UserAuthenticationObject(user, password)


class UserAuthenticationObject:
    def __init__(self, username: str, password: str):
        """Central object to authenticate.

        Parameters:
        - username: str
        - password: str (unencrypted)"""
        self._authenticated = is_users_password(username, password)
        if not self._authenticated:
            raise AuthenticationError
        self.username = username

    def __bool__(self):
        return bool(self._authenticated)

    def __str__(self):
        return self.username

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return False


def ranstr(size=20, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def session_length(s1, s2=None):
    """s1 as session dict with start and end attributes or s1 & s2 as isoformat strings or datetime objects itself. Return session length in seconds"""
    if type(s1) == dict:
        s2 = s1.get("end")
        s1 = s1.get("start")
    if type(s1) == str:
        s1 = datetime.datetime.fromisoformat(s1)
    if type(s2) == str:
        s2 = datetime.datetime.fromisoformat(s2)
    elif s2 == None:
        return 10
    td = s2 - s1
    seconds = td.total_seconds()
    return seconds


def get_salt(n=512):
    return ''.join(random.choice(string.digits +
                                 string.ascii_uppercase + string.ascii_lowercase) for i in range(n))


class AuthenticationError(Exception):
    pass


class InvalidParameterError(Exception):
    pass


class AlreadyExistsError(Exception):
    pass


class UserAlreadyExists(AlreadyExistsError):
    pass


class TaskAlreadyExists(AlreadyExistsError):
    pass


class EmailAlreadyLinked(AlreadyExistsError):
    pass


class NotExistsError(Exception):
    pass


class TaskDoesNotExist(NotExistsError):
    pass


class UserDoesNotExist(NotExistsError):
    pass
