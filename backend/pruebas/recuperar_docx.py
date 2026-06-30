import psycopg
import backend.conexionBD.conexion as conexion

#CONEXION
conn = psycopg.connect(
    dbname=conexion.DB_NAME,
    user=conexion.DB_USER,
    password=conexion.DB_PASSWORD,
    host=conexion.DB_HOST,
    port=conexion.DB_PORT
)


cursor = conn.cursor()

sql = """
    SELECT nombre, archivo 
    FROM documentos 
    WHERE id = 1
    """

cursor.execute(sql)

resultado = cursor.fetchone()

nombre = resultado[0]
contenido = resultado[1]

#GUARDAR EN DISCO
with open("descargado_"+nombre, 'wb') as f:
    f.write(contenido)

print("Docx recuperado exitosamente")

cursor.close()
conn.close()

