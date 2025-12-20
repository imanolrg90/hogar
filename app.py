import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
# En app.py, cambia la línea de importación por esta:
from models import db, User, Receta, Ingrediente, MenuSemanal, MenuSelection, TareaLimpieza, Lavadora, ShoppingItem
from forms import RecetaForm, LoginForm, RegistrationForm

# --- Configuración Inicial ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_pro_home_os' # Cambia esto en producción
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///home_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)

# --- Configuración de Login ---
login = LoginManager(app)
login.login_view = 'login' # Redirige aquí si no estás logueado
login.login_message = "Por favor, inicia sesión para acceder a tu hogar."
login.login_message_category = "info"

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# Crear tablas al inicio si no existen
with app.app_context():
    db.create_all()


# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('dashboard'))
        
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        # Verificar si ya existe usuario o email
        if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
            flash('El usuario o email ya existe.', 'warning')
            return redirect(url_for('register'))

        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('¡Registro completado! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
        
    return render_template('auth/register.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))


# --- RUTAS PRINCIPALES DEL HOME OS ---
@app.route('/')
@login_required
def dashboard():
    import datetime
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_actual = dias[datetime.datetime.today().weekday()]
    
    menu_hoy = MenuSemanal.query.filter_by(user_id=current_user.id, dia=dia_actual).first() # Usar dia_actual en prod
    if not menu_hoy: # Fallback si no existe
         menu_hoy = MenuSemanal.query.filter_by(user_id=current_user.id, dia="Lunes").first()

    tareas = TareaLimpieza.query.filter_by(user_id=current_user.id).order_by(TareaLimpieza.proxima_fecha).limit(5).all()
    lavadoras = Lavadora.query.filter_by(user_id=current_user.id).all()
    total_recetas = Receta.query.filter_by(user_id=current_user.id).count()

    return render_template('dashboard.html', 
                           menu=menu_hoy, 
                           tareas=tareas, 
                           lavadoras=lavadoras,
                           stats={'recetas': total_recetas})


@app.route('/recetas')
@login_required
def recetas_page():
    # Mostrar recetas solo del usuario, ordenadas por la más reciente
    recetas = Receta.query.filter_by(user_id=current_user.id).order_by(Receta.id.desc()).all()
    return render_template('recetas.html', recetas=recetas)


@app.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    form = RecetaForm()
    
    if request.method == 'POST':
        # Validación manual de campos principales
        nombre = request.form.get('nombre')
        kcal = request.form.get('kcal')
        tipo = request.form.get('tipo')

        if nombre and kcal:
            try:
                # 1. Crear Receta vinculada al usuario
                nueva_receta = Receta(
                    nombre=nombre,
                    kcal=float(kcal),
                    tipo=tipo,
                    user_id=current_user.id # Importante: Asignar al usuario
                )
                db.session.add(nueva_receta)
                db.session.commit() # Commit para obtener ID

                # 2. Procesar Ingredientes (Lógica manual robusta)
                ingredientes_temp = {}
                
                for key, value in request.form.items():
                    # Buscar patrones 'ingredientes-X-campo'
                    match = re.match(r'ingredientes-(\d+)-(\w+)', key)
                    if match:
                        index = match.group(1)
                        field = match.group(2) # nombre, cantidad, unidad
                        
                        if index not in ingredientes_temp:
                            ingredientes_temp[index] = {}
                        
                        ingredientes_temp[index][field] = value

                # Guardar ingredientes
                for index, datos in ingredientes_temp.items():
                    if datos.get('nombre') and datos.get('cantidad'):
                        nuevo_ing = Ingrediente(
                            nombre=datos['nombre'],
                            cantidad=float(datos['cantidad']),
                            unidad=datos.get('unidad', 'ud'),
                            receta_id=nueva_receta.id
                        )
                        db.session.add(nuevo_ing)

                db.session.commit()
                flash(f'Receta "{nombre}" guardada con éxito.', 'success')
                return redirect(url_for('recetas_page'))

            except Exception as e:
                db.session.rollback()
                print(f"Error DB: {e}")
                flash(f'Error al guardar la receta: {e}', 'danger')
        else:
            flash('Nombre y Kcal son obligatorios.', 'warning')

    # Si es GET o fallo, mostrar form. Asegurar al menos una fila de ingrediente.
    if not form.ingredientes.entries:
        form.ingredientes.append_entry()
        
    return render_template('add_recipe.html', form=form)


@app.route('/delete_recipe/<int:recipe_id>')
@login_required
def delete_recipe(recipe_id):
    receta = Receta.query.get_or_404(recipe_id)
    
    # Seguridad: Comprobar que la receta pertenece al usuario actual
    if receta.user_id != current_user.id:
        flash('No tienes permiso para eliminar esta receta.', 'danger')
        return redirect(url_for('recetas_page'))
        
    try:
        db.session.delete(receta)
        db.session.commit()
        flash(f'Receta eliminada.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {e}', 'danger')
        
    return redirect(url_for('recetas_page'))


@app.route('/menu', methods=['GET', 'POST'])
@login_required
def menu_semanal_page():
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    tipos_comida = ['Desayuno', 'Comida', 'Merienda', 'Cena']
    
    # Inicializar días
    if MenuSemanal.query.filter_by(user_id=current_user.id).count() == 0:
        for dia in dias_semana:
            db.session.add(MenuSemanal(dia=dia, user_id=current_user.id))
        db.session.commit()

    if request.method == 'POST':
        # 1. Limpiar selecciones anteriores de este usuario (Estrategia simple: borrar todo y recrear)
        menus_usuario = MenuSemanal.query.filter_by(user_id=current_user.id).all()
        for m in menus_usuario:
            MenuSelection.query.filter_by(menu_id=m.id).delete()
        
        # 2. Guardar nuevas selecciones múltiples
        for dia in dias_semana:
            menu_dia = MenuSemanal.query.filter_by(dia=dia, user_id=current_user.id).first()
            
            for tipo in tipos_comida:
                # getlist obtiene TODOS los valores seleccionados para ese campo
                recetas_ids = request.form.getlist(f'{dia}_{tipo}')
                
                for r_id in recetas_ids:
                    if r_id and r_id != "":
                        seleccion = MenuSelection(
                            menu_id=menu_dia.id,
                            receta_id=int(r_id),
                            tipo_comida=tipo
                        )
                        db.session.add(seleccion)
                
        db.session.commit()

        # 3. Recalcular Lista de Compra
        ShoppingItem.query.filter_by(user_id=current_user.id, is_auto=True).delete()
        
        # Traer menús actualizados
        menu_items = MenuSemanal.query.filter_by(user_id=current_user.id).all()
        ingredientes_calculados = generar_lista_compra_db(menu_items)
        
        for item in ingredientes_calculados:
            nuevo_item = ShoppingItem(
                nombre=item['nombre'],
                cantidad=item['cantidad'],
                unidad=item['unidad'],
                is_auto=True,
                user_id=current_user.id
            )
            db.session.add(nuevo_item)
            
        db.session.commit()
        flash('Menú múltiple guardado y lista actualizada.', 'success')
        return redirect(url_for('menu_semanal_page'))

    menu = MenuSemanal.query.filter_by(user_id=current_user.id).all()
    mis_recetas = Receta.query.filter_by(user_id=current_user.id).order_by(Receta.nombre).all()
    lista_compra_preview = generar_lista_compra_db(menu)

    return render_template('menu.html', 
                           menu=menu, 
                           recetas=mis_recetas, 
                           lista_compra=lista_compra_preview)


# --- FUNCIONES AUXILIARES ---
def generar_lista_compra_db(menu_items):
    """Lógica actualizada para soportar MenuSelection"""
    compra = {}
    tipos = ['Desayuno', 'Comida', 'Merienda', 'Cena']

    for item in menu_items:
        # item es un objeto MenuSemanal
        for tipo in tipos:
            # Usamos el método helper que creamos en el modelo
            recetas = item.get_recetas(tipo) 
            for receta in recetas:
                for ing in receta.ingredientes:
                    key = (ing.nombre, ing.unidad)
                    compra[key] = compra.get(key, 0) + ing.cantidad
    
    resultado = []
    for (nombre, unidad), cantidad in sorted(compra.items()):
        resultado.append({'nombre': nombre, 'unidad': unidad, 'cantidad': cantidad})
    return resultado


@app.route('/shopping_list')
@login_required
def shopping_list():
    # Obtener items ordenados: primero los NO completados, luego los completados
    items = ShoppingItem.query.filter_by(user_id=current_user.id).order_by(ShoppingItem.completed, ShoppingItem.nombre).all()
    return render_template('shopping_list.html', items=items)

@app.route('/shopping_list/add', methods=['POST'])
@login_required
def add_shopping_item():
    nombre = request.form.get('nombre')
    if nombre:
        # Añadir item manual
        item = ShoppingItem(nombre=nombre, is_auto=False, user_id=current_user.id)
        db.session.add(item)
        db.session.commit()
    return redirect(url_for('shopping_list'))

@app.route('/shopping_list/toggle/<int:item_id>')
@login_required
def toggle_shopping_item(item_id):
    item = ShoppingItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        item.completed = not item.completed
        db.session.commit()
    return redirect(url_for('shopping_list'))

@app.route('/shopping_list/clear')
@login_required
def clear_completed_items():
    # Borrar solo los que están completados
    ShoppingItem.query.filter_by(user_id=current_user.id, completed=True).delete()
    db.session.commit()
    return redirect(url_for('shopping_list'))

@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    receta = Receta.query.get_or_404(recipe_id)
    
    # Seguridad: verificar dueño
    if receta.user_id != current_user.id:
        flash('No tienes permiso para editar esta receta.', 'danger')
        return redirect(url_for('recetas_page'))

    form = RecetaForm(obj=receta)

    if request.method == 'POST':
        # 1. Actualizar datos básicos
        receta.nombre = request.form.get('nombre')
        receta.kcal = float(request.form.get('kcal', 0))
        receta.tipo = request.form.get('tipo')
        
        try:
            # 2. BORRADO INTELIGENTE: Eliminamos ingredientes viejos para poner los nuevos
            # (Es más fácil que intentar sincronizar IDs uno por uno)
            Ingrediente.query.filter_by(receta_id=receta.id).delete()
            
            # 3. Guardar ingredientes nuevos (Misma lógica que en add_recipe)
            ingredientes_temp = {}
            for key, value in request.form.items():
                match = re.match(r'ingredientes-(\d+)-(\w+)', key)
                if match:
                    index = match.group(1)
                    field = match.group(2)
                    if index not in ingredientes_temp: ingredientes_temp[index] = {}
                    ingredientes_temp[index][field] = value

            for index, datos in ingredientes_temp.items():
                if datos.get('nombre') and datos.get('cantidad'):
                    nuevo_ing = Ingrediente(
                        nombre=datos['nombre'],
                        cantidad=float(datos['cantidad']),
                        unidad=datos.get('unidad', 'ud'),
                        receta_id=receta.id # Vinculamos a la receta existente
                    )
                    db.session.add(nuevo_ing)

            db.session.commit()
            flash('Receta actualizada correctamente.', 'success')
            return redirect(url_for('recetas_page'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al editar: {e}', 'danger')

    # --- LÓGICA GET (Cargar datos en el formulario) ---
    # Si es GET, rellenamos la lista de ingredientes manualmente para que aparezcan en el HTML
    if request.method == 'GET':
        # Limpiamos cualquier campo vacío por defecto
        while len(form.ingredientes) > 0:
            form.ingredientes.pop_entry()
            
        # Añadimos los ingredientes de la base de datos al formulario
        for ing in receta.ingredientes:
            form.ingredientes.append_entry(data={
                'nombre': ing.nombre,
                'cantidad': ing.cantidad,
                'unidad': ing.unidad
            })

    # Reutilizamos la plantilla add_recipe.html pero pasamos una variable extra
    return render_template('add_recipe.html', form=form, is_edit=True, receta_id=receta.id)

# --- EJECUCIÓN ---
if __name__ == '__main__':
    # Puerto 5003 como en tu configuración original
    print("Iniciando Home OS Multi-User en puerto 5003...")
    app.run(debug=True, port=5003)