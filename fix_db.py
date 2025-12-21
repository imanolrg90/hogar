import sqlite3

conn = sqlite3.connect('home_manager.db')
cursor = conn.cursor()

# PASO 1: Crear la tabla si no existe (incluyendo la columna week_start directamente)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS menu_semanal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start TEXT, 
        -- Añade aquí el resto de tus columnas (ej. lunes_comida, martes_cena, etc.)
        observaciones TEXT
    )
''')

# PASO 2: (Opcional) Migración defensiva
# Si ya tienes la tabla creada de antes pero SIN la columna, usa un try/except
try:
    cursor.execute("ALTER TABLE menu_semanal ADD COLUMN week_start TEXT")
    print("Columna 'week_start' añadida exitosamente.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("La columna 'week_start' ya existía.")
    else:
        # Aquí capturamos tu error actual si el paso 1 fallara o no se ejecutara
        print(f"ℹ️ Info: {e}")

conn.commit()
conn.close()