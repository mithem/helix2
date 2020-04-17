import time
import warnings
from hashlib import sha256

import pytest
from pymysql.err import ProgrammingError

from base import delete_task, delete_user, get_tasks, get_user, get_all_users
from base.mailservice import Newsletter
from base.statistics import register_user_activity, get_sessions
from base.utils import (AuthenticationError, InvalidParameterError,
                        TaskDoesNotExist, UserAuthenticationObject,
                        authenticate, check_user_parameters, exec_sql,
                        has_passed, ranstr, session_length, tab)

try:
    test_user = UserAuthenticationObject("tester", "test1234")
except AuthenticationError:
    warnings.warn(
        "User 'tester' cannot be authenticated with password 'test1234'. Check if user is verified (SQL: verified != 0)")


class ConfigError(Exception):
    pass


def test_db_setup():
    """test whether the db is set up correctly for tests"""
    user = get_user(test_user)
    ident = user.get("id")
    assert type(ident) == int
    try:
        assert ident == 1
    except AssertionError:
        print(ident)
        warnings.warn(
            "User 'tester' does not have id 1. It needs to for testing.")
        assert False
    try:
        exec_sql("SELECT * FROM users")
        exec_sql("SELECT * FROM tasks")
        exec_sql("SELECT * FROM statistics")
        exec_sql("SELECT * FROM tests")
    except ProgrammingError:
        raise ConfigError(
            "tables not configured correctly. Expected to get tables: 'users', 'tasks', 'statistics', and 'tests'. Refer to the project documentation for more info.")


def test_has_passed():
    t1 = has_passed("2020-01-12T13:00:00", "2020-01-12T14:00:00Z")
    t2 = has_passed("2020-01-17T20:56:00")
    t3 = has_passed("2042-01-01T00:00:00")
    t4 = has_passed("2024-03-01T00:00:00", "2025-08-12T23:59:59Z")
    assert t1 and t2 and not t3 and t4


def test_get_tasks():
    task1 = {"id": 1, "user": "root", "title": "Phantasialand besuchen", "description": "Könnte mal wieder Zeit werden",
             "dateDue": "2020-03-05T00:00:00", "deadline": "2020-06-01T00:00:00Z"}
    task2 = {"id": 2, "user": "root", "title": "!°^3+´#_.,<  ", "description": "öüä",
             "dateDue": "None", "deadline": "None"}
    task3 = {"id": 4, "user": "root", "title": "a", "description": "sjhfsefkwh",
             "dateDue": "None", "deadline": "2020-03-10T00:00:00"}

    inp = [task1, task2, task3]

    try:
        user = test_user

        t1 = get_tasks(user, inp, id_list=[1, 4], title="3")
        t2 = get_tasks(user, inp, general="a")
        t3 = get_tasks(user, inp, title="besuchen")
        t4 = get_tasks(user, inp, description="ö")
        t5 = get_tasks(user, inp,
                       description="öüä", precise=True)
        t6 = get_tasks(user, inp, deadline="2020-07-01T12:34:56")
        t7 = get_tasks(user, inp, deadline="2020", precise=True)
        t8 = get_tasks(user, inp, id_list=[3])
        t9 = get_tasks(user, inp,
                       title="!°^3+´#_.,<  ", precise=True)
        print(t6)

        t1 = t1 == [task2, task1, task3]
        t2 = t2 == [task1, task3]
        t3 = t3 == [task1]
        t4 = t4 == [task1, task2]
        t5 = t5 == [task2]
        t6 = t6 == [task1, task3]
        t7 = t7 == []
        t8 = t8 == []
        t9 = t9 == [task2]

        print(t1, t2, t3, t4, t5, t6, t7, t8, t9)

        assert t1 and t2 and t3 and t4 and t5 and t6 and t7 and t8 and t9
    except AuthenticationError:
        warnings.warn(
            "Authentication failed, function therefore cannot be tested", UserWarning)


def test_check_user_parameters():
    assert check_user_parameters(
        "mithem", "Wolfram", "Einstein", "Hello123", "helloexamplemail@mymailacccount.tech")


def test_check_user_parameters_2():
    assert check_user_parameters(password="_*'#@!\"§$%&/(){}=?ß´`°^\\\/")


def test_check_user_parameters_invalid_username():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(username="#########")


def test_check_user_parameters_username_too_short():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(username="hello")


def test_check_user_parameters_invalid_first_name():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(first_name="Wolfr'ms")


def test_check_user_parameters_invalid_last_name():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(last_name="Interstell*r")


def test_check_user_parameters_invalid_password():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(password="hello world")


def test_check_user_parameters_password_too_short():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(password="hello")


def test_check_user_parameters_invalid_email():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(email="test@test.t")


def test_check_user_parameters_invalid_email_2():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(email="@gmail.com")


def test_check_user_parameters_invalid_email_3():
    with pytest.raises(InvalidParameterError):
        check_user_parameters(email="notmymail.tech")


def test_user_authentication_object():
    with pytest.raises(AuthenticationError):
        UserAuthenticationObject(
            "notaname,definetelynotaname", "definetelynotapassword")


def test_user_authentication_object_2():
    myvar = test_user._authenticated
    assert myvar


def test_user_authentication_object_3():
    if test_user:
        assert True


def test_user_authentication_object_4():
    assert str(test_user) == "tester"


def test_user_authentication_object_5():
    with test_user as u:
        assert u._authenticated


def test_delete_task():
    with pytest.raises(TaskDoesNotExist):
        delete_task(11111111111111111112,
                    test_user)


def test_delete_user():
    with pytest.raises(InvalidParameterError):
        delete_user(2, test_user)


def test_authenticate():
    result = authenticate("tester", "test1234")
    assert result.username == test_user.username


def test_ranstr():
    result = ranstr()
    assert len(result) == 20 and result.lower() == result


def test_session_length():
    session = {"start": "2020-01-01T00:00:00", "end": "2020-01-01T00:01:00"}
    length = session_length(session)
    assert length == 60


def test_session_length_2():
    assert session_length("2020-01-01T00:00:00") == 10


def test_session_length_3():
    assert session_length("2020-01-01T00:00:00", "2020-01-01T00:00:30") == 30


def test_exec_sql():
    with pytest.raises(ProgrammingError):
        exec_sql("SELECT * FROM notatablename;")


def test_exec_sql_2():
    with pytest.raises(ProgrammingError):
        exec_sql("not a syntax!")


def test_statistics_register_user_activity_create_new():
    previous_length = len(exec_sql("SELECT * FROM statistics"))
    register_user_activity(test_user)
    new_length = len(exec_sql("SELECT * FROM statistics"))
    print("If assertion fails, verify that you have at least 1 minute inbetween your tests. This is because of the registering system which uses 1 minute as a treshhold whether to count activity to old one or create a new.")
    assert previous_length + 1 == new_length

    # cleanup
    exec_sql("DELETE FROM statistics ORDER BY id DESC LIMIT 1;")
    if len(exec_sql("SELECT * FROM statistics")) != previous_length:
        raise RuntimeError(
            "Something went wrong while deleting test row created in the 'statistics' table for user 'tester'. Please take care of the database.")
    assert True


def test_statistics_register_user_activity_update_existing():
    def get_activity():
        return exec_sql("SELECT * FROM statistics ORDER BY id DESC LIMIT 1")[0]
    register_user_activity(test_user)
    activity = get_activity()
    previous_date = activity.get("end")
    time.sleep(11)
    register_user_activity(test_user)
    activity = get_activity()
    new_date = activity.get("end")
    assert previous_date != new_date


def test_statistics_get_sessions():
    sessions = get_sessions(test_user)
    success = True
    for s in sessions:
        if type(s) != dict:
            success = False
        for k in s:
            if k != "username" and k != "start" and k != "end" and k != "id":
                success = False
    assert success


def test_newsletter():
    ns = Newsletter(
        False, "Hi ${username},\nthis is generated by a unit test (test_base.py > test_newsletter())", "Helix - test_base.py", get_all_users())
    assert ns.addressee_type == dict


def test_newsletter_2():
    ns = Newsletter(
        False, "Hi ${username},\nthis is generated by a unit test (test_base.py > test_newsletter())", "Helix - test_base.py", ["test@test.com"])
    assert ns.addressee_type == str


def test_newsletter_3():
    with pytest.raises(TypeError):
        ns = Newsletter(
            False, "Hi ${username},\nthis is generated by a unit test (test_base.py > test_newsletter())", "Helix - test_base.py", ["hello there", 0, {"username": "tester"}])


def test_newsletter_4():
    with pytest.raises(TypeError):
        ns = Newsletter(
            False, "Hi ${username},\nthis is generated by a unit test (test_base.py > test_newsletter())", "Helix - test_base.py", [10])
