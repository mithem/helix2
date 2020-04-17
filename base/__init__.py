"""The base of helix, the wrapper to write to the central database"""
import datetime
import random
from hashlib import sha3_512

import pymysql.cursors
from fileloghelper import Logger
from pymysql.err import IntegrityError, OperationalError

from base import mailservice, utils
from base.utils import (EmailAlreadyLinked, InvalidParameterError,
                        TaskDoesNotExist, UserAlreadyExists,
                        UserAuthenticationObject, UserDoesNotExist,
                        authenticate, exec_sql, file_paths)

DESCRIPTION = "The base of helix, the wrapper to write to the central database"
logger = Logger(file_paths["repo"]+"logs/base.log", "base", autosave=True)
logger.header(True, True, DESCRIPTION, 0, False)


def delete_all_tasks(user: UserAuthenticationObject):
    """Delete all tasks. No undo!"""
    userobj = get_user(user)  # raises UserDoesNotExist if so
    exec_sql(f"DELETE FROM tasks WHERE user='{userobj.get('username')}'")
    logger.debug(f"Deleted all tasks from user '{userobj.get('username')}'")


def add_task(user: UserAuthenticationObject, title: str, description: str = "", due_date: str = "", deadline: str = ""):
    logger.debug(f"Adding task {title}")
    date_created = datetime.datetime.now().isoformat()[:-7]
    title = title.replace("'", "\\'").replace('"', '\\"')
    description = description.replace("'", "\\'").replace('"', '\\"')
    r = exec_sql(
        f"INSERT INTO tasks (user, title, description, dateCreated, dateDue, deadline) VALUES ('{user.username}', '{title}', '{description}', '{date_created}', '{due_date}', '{deadline}')", False)
    print(r)


def delete_task(id, user: UserAuthenticationObject):
    try:
        task = get_tasks(user, id_list=[id])[0]
    except IndexError:
        raise TaskDoesNotExist(f"Task with id {id} not found")
    if task.get("user") == user.username:
        exec_sql(f"DELETE FROM tasks WHERE id=" + str(id), False)
        logger.debug(f"Deleted task with id {str(id)}")
    else:
        raise InvalidParameterError(
            f"Task with id {id} doesn't belong to user '{user.username}'")


def get_all_tasks(user: UserAuthenticationObject):
    logger.debug("this is Houston, in get_all_tasks()")
    return exec_sql(f"SELECT * FROM tasks WHERE user='{user.username}'", verbose=False)


def change_task(user: UserAuthenticationObject, id: int, title: str = None, description: str = None, due_date: str = None, deadline: str = None, new_user: str = None):
    if len(exec_sql(f"SELECT * FROM tasks WHERE id={id}")) != 1:
        raise TaskDoesNotExist(f"Task with id {id} not found")
    if title != None and type(title) == str:
        title = title.replace("'", "\\'").replace('"', '\\"')
        exec_sql(f"UPDATE tasks SET title='{title}' WHERE id={id};")
    if description != None and type(description) == str:
        description = description.replace("'", "\\'").replace('"', '\\"')
        exec_sql(
            f"UPDATE tasks SET description='{description}' WHERE id={id};")
    if due_date != None and type(due_date) == str:
        exec_sql(f"UPDATE tasks SET dateDue='{due_date}' WHERE id={id};")
    if deadline != None and type(deadline) == str:
        exec_sql(f"UPDATE tasks SET deadline='{deadline}' WHERE id={id};")
    if new_user != None and type(new_user) == str:
        exec_sql(f"UPDATE tasks SET user='{new_user}' WHERE id={id};")
    logger.debug(f"changed task with id {id} (by user '{user.username}')")


class BreakKey(Exception):
    """internal helper for breaking the loop :)"""
    pass


def get_tasks(user: UserAuthenticationObject, task_set=None, id_list=[], general="", precise=False, **kwargs):
    """Returns a list of all tasks matching the parameters in one or more ways (logical or). If 'general' is specified, all properties of the task are searched for 'general'. If 'precise', the properties have to match the search exactly."""
    if task_set == None:
        task_set = get_all_tasks(user)
    try:
        result = []
        if general != "":
            try:
                for t in task_set:
                    for key in t:
                        if key != "id":
                            if precise:
                                if general == t[key]:
                                    result.append(t)
                                    raise BreakKey
                            else:
                                if general.lower() in t[key].lower():
                                    result.append(t)
                                    break
            except BreakKey:
                pass
        else:
            mapping = {
                "title": "title",
                "description": "description",
                "date_created": "dateCreated",
                "due_date": "dateDue",
                "deadline": "deadline",
            }
            for t in task_set:
                for key in kwargs:
                    if kwargs[key] == None or kwargs[key] == "":
                        continue
                    if precise:
                        if kwargs[key] == t[mapping[key]]:
                            result.append(t)
                            break
                    else:
                        if key == "due_date" or key == "deadline":
                            try:
                                if utils.has_passed(t[mapping[key]], kwargs[key]):
                                    result.append(t)
                                    break
                            except Exception as e:
                                raise e
                        else:
                            if kwargs[key] in t[mapping[key]]:
                                result.append(t)
                                break
        if len(id_list) != 0:
            for t in task_set:
                if t["id"] in id_list:
                    result.append(t)
    except Exception as e:
        logger.handle_exception(e)
        logger.debug("search query: ")
        logger.debug(kwargs)
        raise e
    logger.debug(
        f"search query ({kwargs}, IDs {id_list}{', general: ' +general if general != '' else ''}, precise {precise}) landed {len(result)} hits", True)
    return result


def get_user(user: UserAuthenticationObject):
    return exec_sql(f"SELECT * FROM users WHERE username='{user.username}'", False)[0]


def get_all_users(newsletter_only: bool = False):
    cmd = "SELECT id, username, firstName, lastName, email, newsletter FROM users"
    if newsletter_only:
        cmd += " WHERE newsletter=1"
    users: list = exec_sql(cmd, False)
    return users


def create_user(username: str, first_name: str, last_name: str, password: str, email: str, verbose=False):
    """Create user in database

    Note: This handles hashing the password
    """
    try:
        utils.check_user_parameters(
            username, first_name, last_name, password, email)
        salt = utils.get_salt()
        hash = sha3_512(bytes(password + salt, "utf-8")).hexdigest()
        dn = datetime.datetime.now().isoformat(timespec='seconds')
        uao = None
        if verbose:
            logger.debug("\nCreating user:")
            utils.tab({"username": username, "first name": first_name,
                       "last name": last_name, "email": email, "joined": dn, "verified": False}, logger=logger)
        else:
            logger.debug(f"Creating user: {username}")
        try:
            result = exec_sql(
                f"INSERT INTO users (username, firstName, lastName, hash, salt, email, joined, verified) VALUES ('{username}', '{first_name}', '{last_name}', '{hash}', '{salt}', '{email}', '{dn}', '0')", verbose=True)
            not_verify = mailservice.register(username, email, first_name,
                                              last_name, dn, logger)
            # Registration skipped (config.json: skip-email-verification)
            if not not_verify:
                exec_sql(
                    f"UPDATE users SET verified=1 WHERE username='{username}'", True)
        except IntegrityError as e:
            print(e)
            s = str(e)
            if "username" in s:
                raise UserAlreadyExists(f"{username} already exists")
            elif "email" in s:
                raise EmailAlreadyLinked(
                    f"Email '{email}' is already linked to another account")
    except Exception as e:
        logger.handle_exception(e)
        raise e


def delete_user(id: int, user: UserAuthenticationObject):
    try:
        user = get_user(user)
    except IndexError:
        raise UserDoesNotExist(f"User with id {id} not found")
    if user.get("id") == id:
        exec_sql(f"DELETE FROM users WHERE id={id}")
        logger.debug("Deleted user with id " + str(id))
    else:
        raise InvalidParameterError(
            f"Username '{user.get('username')}' doesn't match id {id}")


def get_user_by_email(email: str):
    result = exec_sql(f"SELECT * FROM users WHERE email='{email}'")[0]
    if len(result) == 0:
        raise UserDoesNotExist
    return result


def change_user(user: UserAuthenticationObject, username: str = None, first_name: str = None, last_name: str = None, password: str = None, email: str = None):
    userobj = get_user(user)
    utils.check_user_parameters(
        username, first_name, last_name, password, email)
    id = str(userobj.get("id"))
    if len(exec_sql(f"SELECT * FROM users WHERE id={id}")) != 1:
        raise UserDoesNotExist(f"User with id {id} not found")
    if username != None:
        try:
            exec_sql(
                f"UPDATE users SET username='{username}' WHERE id={id};")
            # transferring tasks mapped to old username to new one
            tasks = get_all_tasks(user)
            for task in tasks:
                change_task(user, task.get("id"), new_user=username)
        except IntegrityError:
            raise UserAlreadyExists(f"'{username}' already exists")
    if first_name != None:
        exec_sql(
            f"UPDATE users SET firstName='{first_name}' WHERE id={id};")
    if last_name != None:
        exec_sql(f"UPDATE users SET lastName='{last_name}' WHERE id={id};")
    if password != None:
        new_hash = sha3_512(
            bytes(password + utils.get_salt(), "utf-8")).hexdigest()
        exec_sql(
            f"UPDATE users SET hash='{new_hash}' WHERE id={id};")
    if email != None:
        exec_sql(f"UPDATE users SET email='{email}' WHERE id={id};")
        mailservice.register(username if username !=
                             None else userobj.get("username"), email, first_name if first_name != None else userobj.get("firstName"), last_name if last_name != None else userobj.get("lastName"), userobj.get("djoined"), verification=True)
        exec_sql(f"UPDATE users SET verified=0 WHERE email='{email}';")
    logger.debug(f"changed user with (previous) username {user.username}")
