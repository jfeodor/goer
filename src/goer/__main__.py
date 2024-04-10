import asyncio
import sys
from goer.goer import Gør


if __name__ == "__main__":
    gør = Gør.load_python("Goerfile.py")
    asyncio.run(gør.run(sys.argv[1:]))
