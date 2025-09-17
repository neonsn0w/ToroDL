import sqlite3


def prepare_db():
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS videos
                   (
                       file_id     VARCHAR(255) PRIMARY KEY,
                       platform_id VARCHAR(255) NOT NULL
                   );""")

def check_if_video_is_present(platform_id: str) -> bool:
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()
    cursor.execute(f"""
                   SELECT COUNT(1)
                   FROM videos
                   WHERE platform_id = "{platform_id}";""")

    if cursor.fetchone()[0] > 0:
        return True
    else:
        return False

def add_video(file_id: str, platform_id: str):
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()
    cursor.execute(f"""
                   INSERT INTO videos VALUES ("{file_id}", "{platform_id}");""")

    connection.commit()

def get_video(platform_id: str):
    connection = sqlite3.connect('video_ids.db')
    cursor = connection.cursor()
    cursor.execute(f"""
                   SELECT v.file_id
                   FROM videos AS v
                   WHERE v.platform_id = "{platform_id}";""")

    return cursor.fetchone()[0]