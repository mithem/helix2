import argparse
import json
import time
from json.decoder import JSONDecodeError

import serverly
import serverly.user
from serverly import Request, Response, error_response, logger

import base
import base.mailservice
import base.statistics
from base.utils import file_paths

p = argparse.ArgumentParser()
p.add_argument("--hostname", "-host", type=str, default="localhost")
p.add_argument("--port", "-p", type=int, default=8081)
p.add_argument("--superpath", "--path", "--super",
               nargs="?", type=str, default="notapath")
args = p.parse_args()

with open("config.json") as f:
    config = json.load(f)

serverly.stater.setup("mithem", "migpasswort123", "helix")
serverly.user.setup(user_columns={"email": str, "bearer_token": str, "verified": (
    bool, False), "role": (str, "normal"), "newsletter": (bool, True)}, require_email_verification=not config.get("skip-email-verification", False))


serverly.register_error_response(401, "Unauthorized.", "base")
serverly.register_error_response(404, "Task(s) not found.", "base")
serverly.register_error_response(406, "Invalid parameter(s). Expected ")


@serverly.serves("PUT", "/api/newsletter/unsubscribe")
def newsletter_unsubscribe(req: Request):
    try:
        username = req.obj["username"]
        base.mailservice.unsubscribe_newsletter(username)
        response = Response(body="Unsubscribed successfully")
    except KeyError:
        error_response(406)
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, body=str(e))
    return response


@serverly.serves("PUT", "/api/newsletter/subscribe")
def newsletter_subscribe(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        base.mailservice.subcribe_to_newsletter(uao)
        response = Response(body="Subscribe successfully")
    except KeyError:
        return error_response(406, "username", "password")
    except base.utils.AuthenticationError:
        return error_response(401)
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, body=str(e))
    return response


@serverly.serves("GET", "/api/requestdata")
def send_user_data(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        base.mailservice.send_user_req.obj(uao)
        response = Response(body="Sent data.")
    except KeyError:
        return error_response(406, "username", "password")
    except base.utils.AuthenticationError:
        return error_response(401)
    except Exception as e:
        serverly.logger.handle_exception(e)
        reponse = Response(500, body=str(e))
    return response


@serverly.serves("GET", "/api/statistics/getsessions")
def stats_get_sessions(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        sessions = base.statistics.get_sessions(uao)
        response = Response(body=sessions)
    except KeyError:
        response = error_response(406, "username", "password")
    except base.utils.AuthenticationError:
        response = error_response(401)
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, str(e))
    return response


@serverly.serves("POST", "/api/statistics/sayhello")
def stats_say_hello(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        base.statistics.register_user_activity(uao)
        response = Response()
    except KeyError:
        response = error_response(406, "username", "password")
    except base.utils.AuthenticationError:
        response = error_response(401)
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, body=str(e))
    return response


@serverly.serves("PUT", "/api/changetask")
def change_task(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        base.change_task(uao, req.obj["id"], req.obj.get("title", None), req.obj.get(
            "description", None), req.obj.get("dueDate", None), req.obj.get("deadline", None))
        response = Response()
    except KeyError:
        response = error_response(406, "username", "password", "id", "(optional) title",
                                  "(optional) description", "(optional) dueDate", "(optional) deadline")
    except base.utils.AuthenticationError:
        response = error_response(401)
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, body=str(e))
    return response


@serverly.serves("DELETE", "/api/resettasks")
def reset_tasks_for_user(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        base.delete_all_tasks(uao)
        response = Response()
    except base.utils.AuthenticationError:
        response = error_response(401)
    except base.utils.UserDoesNotExist:
        response = Response(404, body="User not found.")
    return response


@serverly.serves("GET", "/api/getuser")
def get_user(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        user = base.get_user(uao)
        response = Response(body=user)
    except base.utils.AuthenticationError:
        response = error_response(401)
    except base.utils.UserDoesNotExist:
        response = Response(404, body="User not found.")
    return response


@serverly.serves("DELETE", "/api/deleteuser")
def delete_user(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        user = base.get_user(uao)
        base.delete_user(user.get("id", 0), uao)
        response = Response()
    except base.utils.AuthenticationError as e:
        serverly.logger.handle_exception(e)
        response = error_response(401)
    except base.utils.UserDoesNotExist as e:
        serverly.logger.handle_exception(e)
        response = Response(404, body="User not found.")
    except base.utils.InvalidParameterError as e:
        serverly.logger.handle_exception(e)
        response = Response(406, body=str(e))
    return response


@serverly.serves("DELETE", "/api/deletetask")
def delete_task(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        base.delete_task(req.obj["id"], uao)
        response = Response(body="Deleted task with id " + str(req.obj["id"]))
    except base.utils.AuthenticationError:
        response = error_response(401)
    except base.utils.TaskDoesNotExist:
        response = error_response(404)
    except base.utils.InvalidParameterError as e:
        response = Response(406, body=str(e))
    except KeyError:
        response_code = 406
        response_msg = "Invalid parameters. Expected username, password and id."
    return {"code": response_code}, response_msg


@serverly.serves("POST", "/api/addtask")
def add_task(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        base.add_task(uao, title=req.obj.get("title", "New Task"), description=req.obj.get(
            "description", ""), due_date=req.obj.get("dueDate", ""), deadline=req.obj.get("deadline", ""))
        response = Response()
    except base.utils.AuthenticationError:
        reponse = error_response(401)
    except KeyError:
        response = error_response(406, "username", "password")
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, body=str(e))
    return response


@serverly.serves("POST", "/api/register")
def register_new_user(req: Request):
    try:
        base.create_user(req.obj["username"], req.obj["firstName"],
                         req.obj["lastName"], req.obj["password"], req.obj["email"])
        response = Response(201)
    except KeyError:
        response = error_response(
            406, "username", "firstName", "lastName", "password", "email")
    except (base.utils.UserAlreadyExists, base.utils.EmailAlreadyLinked) as e:
        response = Response(406, str(e))
    except Exception as e:
        response = Response(500, body=str(e))
    return response


@serverly.serves("POST", "/api/login")
def login_user(req: Request):
    try:
        base.authenticate(req.obj.get("username"), req.obj.get("password"))
        response = Response()
    except base.utils.AuthenticationError:
        response = error_response(401)
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, str(e))
    return response


@serverly.serves("GET", "/api/gettasks")
def get_tasks(req: Request):
    try:
        user = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        if bool(req.obj.get("getAll", False)):
            tasks = base.get_all_tasks(user)
        else:
            print("(webserver: get_tasks)", req.obj)
            tasks = base.get_tasks(user=user, task_set=None, id_list=req.obj.get("id", []), general=req.obj.get(
                "general", ""), precise=bool(req.obj.get("precise", False)), title=req.obj.get("title", ""), description=req.obj.get("description", ""), date_created=req.obj.get("dateCreated", ""), due_date=req.obj.get("dueDate", ""), deadline=req.obj.get("deadline", ""))
        response = Response(body=tasks)
    except base.utils.AuthenticationError:
        response = error_response(401)
    except Exception as e:
        respone = Response(500, str(e))
    finally:
        return response


@serverly.serves("PUT", "/api/changeuser")
def change_user(req: Request):
    try:
        uao = base.utils.UserAuthenticationObject(
            req.obj["username"], req.obj["password"])
        base.change_user(uao, username=req.obj.get("newUsername", None), first_name=req.obj.get("firstName", None),
                         last_name=req.obj.get("lastName", None), password=req.obj.get("newPassword", None), email=req.obj.get("email", None))
        response = Response()
    except base.utils.AuthenticationError:
        response = error_response(401)
    except KeyError:
        response = error_response(406, "username", "password")
    except (base.utils.UserAlreadyExists, base.utils.InvalidParameterError, base.utils.EmailAlreadyLinked) as e:
        response = Response(406, str(e))
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, str(e))
    return response


serverly.static_page(file_paths["repo"] +
                     "src/hello_world.html", "/helloworld")
serverly.static_page(
    file_paths["repo"] + "src/error_template.html", "/error")
serverly.static_page(file_paths["repo"] +
                     "src/welcome.html", "/")
serverly.static_page(file_paths["repo"] +
                     "src/register.html", "/register")
serverly.static_page(file_paths["repo"] + "src/login.html", "/login")
serverly.static_page(file_paths["repo"] +
                     "src/dashboard.html", "/dashboard")
serverly.static_page(file_paths["repo"] +
                     "src/account.html", "/account")
serverly.static_page(
    file_paths["repo"] + "src/user_successfully_verified.html", "/verified")

serverly.address = (args.hostname, args.port)
superpath = config.get("sitemap", {}).get("path", "/")
serverly.start(superpath)
