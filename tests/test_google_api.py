import base64
from email import message_from_bytes
from email.policy import default

from notas_voz.google_api import DOC_MIME, FOLDER_MIME, GmailMailer, GoogleArchive


class Call:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeFiles:
    def __init__(self):
        self.items = []  # dicts with id, name, mimeType, parents
        self.created = []
        self.queries = []

    def list(self, q, fields, spaces):
        self.queries.append(q)
        found = []
        for item in self.items:
            if f"name = '{item['name']}'" in q.replace("\\'", "'") and item["parents"][0] in q:
                found.append({"id": item["id"]})
        if "root" in q:
            found = [{"id": i["id"]} for i in self.items if i["name"] == "Transcripciones"]
        return Call({"files": found})

    def create(self, body, fields, media_body=None):
        new_id = f"id{len(self.items) + 1}"
        self.items.append({"id": new_id, "parents": body.get("parents", ["root"]), **body})
        self.created.append((body, media_body))
        return Call({"id": new_id, "webViewLink": f"https://docs.google.com/{new_id}"})


class FakeDrive:
    def __init__(self):
        self._files = FakeFiles()

    def files(self):
        return self._files


def test_folders_are_found_or_created_under_root():
    drive = FakeDrive()
    archive = GoogleArchive(drive, root_name="Transcripciones")
    first = archive.ensure_folder("Ana (7)")
    second = archive.ensure_folder("Ana (7)")
    assert first == second
    folders = [b for b, _ in drive.files().created if b["mimeType"] == FOLDER_MIME]
    assert [f["name"] for f in folders] == ["Transcripciones", "Ana (7)"]
    assert folders[1]["parents"] == ["id1"]


def test_quotes_in_names_are_escaped():
    drive = FakeDrive()
    GoogleArchive(drive).ensure_folder("O'Neil (8)")
    assert any("O\\'Neil" in q for q in drive.files().queries)


def test_save_creates_google_doc_and_audio(tmp_path):
    audio = tmp_path / "a.ogg"
    audio.write_bytes(b"ogg")
    drive = FakeDrive()
    link = GoogleArchive(drive).save("F1", "2026-10-22 20.30 - Ana", "hola", audio, "audio/ogg")
    (doc_body, doc_media), (audio_body, audio_media) = drive.files().created
    assert doc_body == {"name": "2026-10-22 20.30 - Ana", "mimeType": DOC_MIME, "parents": ["F1"]}
    assert doc_media.getbytes(0, 100) == b"hola"
    assert audio_body == {"name": "2026-10-22 20.30 - Ana.ogg", "parents": ["F1"]}
    assert audio_media.mimetype() == "audio/ogg"
    assert link == "https://docs.google.com/id1"


def test_gmail_sends_utf8_message():
    sent = []

    class Messages:
        def send(self, userId, body):
            sent.append((userId, body))
            return Call({"id": "m1"})

    class Users:
        def messages(self):
            return Messages()

    class Gmail:
        def users(self):
            return Users()

    GmailMailer(Gmail()).send("dueno@example.com", "Transcripción — Ana", "Hola, ¿qué tal?")
    user_id, body = sent[0]
    assert user_id == "me"
    msg = message_from_bytes(base64.urlsafe_b64decode(body["raw"]), policy=default)
    assert msg["To"] == "dueno@example.com"
    assert msg["Subject"] == "Transcripción — Ana"
    assert msg.get_content().strip() == "Hola, ¿qué tal?"
