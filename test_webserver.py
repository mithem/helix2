from webserver.utils import *

str1 = "https://hello.com/example.html"
str2 = "/newtask"


def test_get_filename():
    assert get_filename(str1) == "example.html" and get_filename(
        str2) == "newtask"


def test_remove_filename():
    result1 = remove_filename(
        str1) == "https://hello.com/"
    result2 = remove_filename(str2) == "/"
    assert result1 and result2


def test_get_extension():
    r1 = get_extension(str1) == "html"
    r2 = get_extension(str2) == ""
    r3 = get_extension("a'.js") == "js"
    r4 = get_extension("#´+<±.css") == "css"
    r5 = get_extension("wonderful.png") == ""
    assert r1 and r2 and r3 and r4 and r5
