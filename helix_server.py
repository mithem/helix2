import argparse
import json
from base.utils import file_paths

import webserver

p = argparse.ArgumentParser()
p.add_argument("--hostname", "-host", type=str, default="localhost")
p.add_argument("--port", "-p", type=int, default=8081)
p.add_argument("--superpath", "--path", "--super",
               nargs="?", type=str, default="notapath")
args = p.parse_args()

if args.superpath != "notapath":
    with open(file_paths["config.json"], "r") as f:
        config = json.loads(f.read())
    config["sitemap"]["path"] = args.superpath
    with open(file_paths["config.json"], "w") as f:
        f.write(json.dumps(config))

webserver.start(args.hostname, args.port)
