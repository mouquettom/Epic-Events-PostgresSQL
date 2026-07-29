from app.database.connection import get_connection


def test_database_connection():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute('SELECT current_database();')
    database_name = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    assert database_name == 'epic_events_database'