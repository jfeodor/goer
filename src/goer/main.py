import asyncio
import sys

from goer.goer import Gør


def usage() -> None:
    print("goer [-h|--help] [JOB]...")
    print("Execute jobs defined in python files.")
    print()
    print("Options:")
    print("  -h, --help   print this message")
    print()
    print("Copyright 2024, Numerous ApS")


def main() -> None:
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        usage()
        sys.exit(0)

    try:
        gør = Gør.load_python("Goerfile.py")
    except FileNotFoundError:
        print("error: no Goerfile.py found")
        usage()
        sys.exit(1)

    job_ids = args
    if not job_ids:
        print("available jobs:", *gør.list_job_ids())
        sys.exit(0)

    if asyncio.run(gør.run(job_ids)):
        sys.exit(0)
    else:
        sys.exit(1)
