from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)

def test_profile_valid_csv():
    csv_content = (
        "name,age,city\n"
        "Ali,30,Den Haag\n"
        "Ayse,,Rotterdam\n"
        "Ali,30,Den Haag\n"
    )

    response = client.post(
    "/data/profile",
    files={
        "file": (
            "test.csv",
            csv_content.encode("utf-8"),
            "text/csv",
        )
    },
    )
    body = response.json()

    assert response.status_code == 200

    assert body["row_count"] == 3
    assert body["column_count"] == 3
    assert body["null_counts"]["age"] == 1
    assert body["duplicate_count"] == 1
    assert body["numeric_columns"] == ["age"]
    assert body["numeric_summary"]["age"]["count"] == 2
    assert body["numeric_summary"]["age"]["mean"] == 30.0
    assert body["numeric_summary"]["age"]["min"] == 30.0
    assert body["numeric_summary"]["age"]["max"] == 30.0
    assert body["sample_rows"][1]["age"] is None

def test_profile_empty_csv():
    response = client.post(
        "/data/profile",
        files={
            "file": (
                "empty.csv",
                b"",    # icerik olmayan bos dosya
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "CSV dosyası boş."


def test_profile_broken_csv():
    csv_content = (
        "name,age,city\n"
        "Ali,30,Den Haag\n"
        'Ayse,"25,Rotterdam\n'
    )

    response = client.post(
        "/data/profile",
        files={
            "file": (
                "broken.csv",
                csv_content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "CSV dosyası geçersiz veya bozuk."


def test_profile_invalid_file_type():
    response = client.post(
        "/data/profile",
        files={
            "file": (
                "test.txt",
                b"Bu bir CSV dosyasi degil.",
                "text/plain",
            )
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Yalnızca CSV dosyası yükleyebilirsiniz."