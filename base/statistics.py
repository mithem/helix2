import datetime
import json

import pymysql

import base
from base.utils import (InvalidParameterError, UserAuthenticationObject,
                        file_paths)


def register_user_activity(user: UserAuthenticationObject):
    def create_new():
        base.exec_sql(
            f"INSERT INTO statistics (username, start, end) VALUES ('{user.username}','{now_date.isoformat(timespec='seconds')}', '{now_date.isoformat(timespec='seconds')}')")
    now_date = datetime.datetime.now()
    last_activity = base.exec_sql(
        f"SELECT * FROM statistics WHERE username='{user.username}' ORDER BY id DESC LIMIT 1")
    if len(last_activity) == 0:
        create_new()
    else:
        old_date = datetime.datetime.fromisoformat(last_activity[0]["end"])
        if old_date + datetime.timedelta(seconds=60) < now_date:
            create_new()
        elif old_date + datetime.timedelta(seconds=10) < now_date:
            base.exec_sql(
                f"UPDATE statistics SET end='{now_date.isoformat(timespec='seconds')}' WHERE id={last_activity[0].get('id')}")


def get_sessions(user: UserAuthenticationObject):
    sessions = base.exec_sql(
        f"SELECT * FROM statistics WHERE username='{user.username}' ORDER BY id")
    return sessions
