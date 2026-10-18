from ckpkg.utils import clamp, slugify
from ckpkg.helpers import build_url

if __name__ == "__main__":
    print(build_url("https://x.io/", "Hello, World!"), clamp(15, 0, 10))
