import re
import json
import hanlp
import opencc
import string

from peewee import IntegrityError
from playhouse.postgres_ext import fn

from stilio.persistence.exceptions import StoringError
from stilio.persistence.torrents.models import Torrent


non_stops = (
    "\uFF02\uFF03\uFF04\uFF05\uFF06\uFF07\uFF08\uFF09\uFF0A\uFF0B\uFF0C\uFF0D"
    "\uFF0F\uFF1A\uFF1B\uFF1C\uFF1D\uFF1E\uFF20\uFF3B\uFF3C\uFF3D\uFF3E\uFF3F"
    "\uFF40\uFF5B\uFF5C\uFF5D\uFF5E\uFF5F\uFF60\uFF62\uFF63\uFF64\u3000\u3001"
    "\u3003\u3008\u3009\u300A\u300B\u300C\u300D\u300E\u300F\u3010\u3011\u3014"
    "\u3015\u3016\u3017\u3018\u3019\u301A\u301B\u301C\u301D\u301E\u301F\u3030"
    "\u303E\u303F\u2013\u2014\u2018\u2019\u201B\u201C\u201D\u201E\u201F\u2026"
    "\u2027\uFE4F\uFE51\uFE54\u00B7"
)
stops = "\uFF0E\uFF01\uFF1F\uFF61\u3002"
punctuation = non_stops + stops + string.punctuation + r"\\"

converter = opencc.OpenCC("t2s.json")
tokenizer = hanlp.load(hanlp.pretrained.tok.FINE_ELECTRA_SMALL_ZH)


class FileSystem:
    def __init__(self, file_path=None, root=False):
        self.children = []

        if file_path != None and not root:
            try:
                self.name, child = file_path.split("/", 1)
                self.children.append(FileSystem(child))
            except ValueError:
                self.name = file_path
        else:
            self.name = "/"

    def add_child(self, file_path):
        try:
            first_level, next_level = file_path.split("/", 1)
        except ValueError:
            # only one result, final file in path, add it
            self.children.append(FileSystem(file_path))
        else:
            # search for child and add the rest
            for child in self.children:
                if first_level == child.name:
                    child.add_child(next_level)
                    return
            else:
                # rest of the path not present in filesystem, add it
                self.children.append(FileSystem(file_path))

    def is_children(self, name: str) -> bool:
        return any(name == children.name for children in self.children)

    def make_dict(self):
        if len(self.children) > 0:
            dictionary = {self.name: []}
            for child in self.children:
                dictionary[self.name].append(child.make_dict())
            return dictionary
        else:
            return self.name


def store_metadata(info_hash: bytes, metadata: dict, logger=None) -> None:
    name = metadata[b"name"].decode("utf-8")
    files = get_file_structure(metadata, name)
    size = get_size(metadata)

    try:
        files = json.dumps(files, ensure_ascii=False)
        search_name = re.sub(r"[%s]+" % punctuation, " ", name + files)
        search_name = " ".join(search_name.split())
        search_name = converter.convert(search_name)
        search_name = list(set(tokenizer(search_name)))
        search_name = [token.replace(" ", "") for token in search_name]
        search_name = " ".join(search_name)
        Torrent.insert(
            info_hash=info_hash.hex(),
            name=name,
            search_name=fn.to_tsvector(search_name),
            files=files,
            size=size,
        ).execute()
    except IntegrityError as e:
        logger.exception(e)
        return

    if logger:
        logger.info(f"Added: {name}")


def get_file_structure(metadata: dict, name: str) -> dict:
    files = FileSystem(root=True)

    if b"files" in metadata:
        for file in metadata[b"files"]:
            if any(b"/" in item for item in file[b"path"]):
                raise StoringError(message="Path contains trailing slashes")
            path = "/".join(i.decode("utf-8") for i in file[b"path"])
            files.add_child(path)
    else:
        files.add_child(name)

    return files.make_dict()


def get_size(metadata: dict) -> int:
    if b"files" in metadata:
        return sum([element[b"length"] for element in metadata[b"files"]])
    else:
        return 0
