import sqlite3


def prepare_db():
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS videos
                   (
                       file_id     VARCHAR(255) PRIMARY KEY,
                       platform_id VARCHAR(255) NOT NULL,
                       platform    VARCHAR(255),
                       media_type  VARCHAR(255)
                   );""")

def get_number_of_media_by_platform_id(platform_id: str) -> int:
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()
    cursor.execute(f"""
                   SELECT COUNT(*)
                   FROM videos
                   WHERE platform_id = "{platform_id}";""")

    return cursor.fetchone()[0]


def add_video(file_id: str, platform_id: str, platform: str):
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()
    cursor.execute(f"""
                   INSERT INTO videos VALUES ("{file_id}", "{platform_id}", "{platform}", "video");""")

    connection.commit()

def add_photo(file_id: str, platform_id: str, platform: str):
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()
    cursor.execute(f"""
                   INSERT INTO videos VALUES ("{file_id}", "{platform_id}", "{platform}", "photo");""")

    connection.commit()

def get_first_media(platform_id: str):
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()
    cursor.execute(f"""
                   SELECT *
                   FROM videos AS v
                   WHERE v.platform_id = "{platform_id}";""")

    return cursor.fetchone()

def get_all_media(platform_id: str):
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()
    cursor.execute(f"""
                   SELECT *
                   FROM videos AS v
                   WHERE v.platform_id = "{platform_id}";""")

    return cursor.fetchall()