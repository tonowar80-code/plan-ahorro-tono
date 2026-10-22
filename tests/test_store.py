from datetime import datetime
from pathlib import Path

from notas_voz.store import Store


def make_store(tmp_path: Path) -> Store:
    return Store(tmp_path / "db.sqlite")


def test_people_authorize_revoke_and_list(tmp_path):
    store = make_store(tmp_path)
    assert not store.is_person(7)
    store.add_person(7, "Ana")
    assert store.is_person(7)
    assert store.list_people() == [(7, "Ana")]
    assert store.remove_person(7) is True
    assert store.remove_person(7) is False
    assert not store.is_person(7)


def test_requests_remember_last_name(tmp_path):
    store = make_store(tmp_path)
    assert store.requested_name(9) is None
    store.remember_request(9, "Luis")
    store.remember_request(9, "Luis G.")
    assert store.requested_name(9) == "Luis G."


def test_folders(tmp_path):
    store = make_store(tmp_path)
    assert store.folder_for(7) is None
    store.set_folder(7, "F1")
    assert store.folder_for(7) == "F1"


def test_jobs_lifecycle(tmp_path):
    store = make_store(tmp_path)
    when = datetime(2026, 10, 22, 20, 30)
    job_id = store.create_job(7, "Ana", 70, when, tmp_path / "a.ogg", "audio/ogg")
    job = store.get_job(job_id)
    assert job.user_id == 7 and job.name == "Ana" and job.chat_id == 70
    assert job.received_at == when and job.audio_path == tmp_path / "a.ogg"
    assert job.transcript is None and not job.drive_done and not job.mail_done
    assert store.unfinished_jobs() == [job_id]

    store.set_transcript(job_id, "hola")
    assert store.unfinished_jobs() == []
    assert store.pending_deliveries() == [job_id]

    store.mark_drive_done(job_id, "https://drive/x")
    job = store.get_job(job_id)
    assert job.drive_done and job.doc_link == "https://drive/x"
    assert store.pending_deliveries() == [job_id]

    store.mark_mail_done(job_id)
    assert store.pending_deliveries() == []

    store.delete_job(job_id)
    assert store.get_job(job_id) is None


def test_store_persists_across_instances(tmp_path):
    make_store(tmp_path).add_person(7, "Ana")
    assert make_store(tmp_path).is_person(7)


def test_store_is_safe_across_threads(tmp_path):
    import threading

    store = make_store(tmp_path)

    def add_many(start):
        for i in range(start, start + 50):
            store.add_person(i, f"P{i}")
            store.list_people()

    threads = [threading.Thread(target=add_many, args=(n * 100,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(store.list_people()) == 200
