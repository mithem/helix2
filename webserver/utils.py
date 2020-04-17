def get_filename(path):
    return path.split("/")[-1]


def remove_filename(path):
    return path[:-len(get_filename(path))]


def get_extension(fname_or_path):
    n = get_filename(fname_or_path)
    if n[-3:] == ".js":
        return "js"
    if n[-5:] == ".html":
        return "html"
    if n[-4:] == ".css":
        return "css"
    return ""


class ClientError(Exception):
    """Exception for unexpected client behavior or an error/mistake on the client's side"""
    pass
