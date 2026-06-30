import psycopg
import backend.conexionBD.conexion as conexion


RUTA_ARCHIVO = "C:\\Users\\Usuario\\Documents\\Backup\\v1.docx"
DB_NAME = conexion.DB_NAME
DB_USER = conexion.DB_USER
import locale
print(locale.getpreferredencoding())

#CONEXION
conn = psycopg.connect(
    dbname=conexion.DB_NAME,
    user=conexion.DB_USER,
    password=conexion.DB_PASSWORD,
    host=conexion.DB_HOST,
    port=conexion.DB_PORT
)

cursor = conn.cursor()

#LEER ARCHIVO DOCX
with open(RUTA_ARCHIVO, 'rb') as f:
    contenido = f.read()

sql = """
    INSERT INTO documentos (nombre,archivo) 
    values (%s, %s)
    """

cursor.execute(sql, ("v1.docx", psycopg.Binary(contenido)))

conn.commit()

print("Docx guardado exitosamente")


cursor.close()
conn.close()
