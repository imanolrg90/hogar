import os
import re
import json
import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
# En app.py, cambia la línea de importación por esta:
from models import db, User, Receta, MenuSemanal, MenuSelection, TareaLimpieza, Lavadora, ShoppingItem, Ingredient, RecipeIngredient
from forms import RecetaForm, LoginForm, RegistrationForm
from datetime import datetime, timedelta, date # Asegúrate de importar esto
from models import Exercise, WorkoutSession, WorkoutSet # Añadir a la lista existente
from forms import ExerciseForm # Añadir a la lista existente
from models import Routine, RoutineExercise # Añadir a la lista
from forms import RoutineForm # Añadir a la lista
from models import BodyMeasurement # Añadir
from forms import BodyMeasurementForm # Añadir
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

@app.route('/ingredients', methods=['GET', 'POST'])
@login_required
def ingredients_manager():
    if request.method == 'POST':
        name = request.form.get('name')
        try:
            kcal = float(request.form.get('kcal'))
            price_kg = float(request.form.get('price_kg')) # Input directo en KG
        except ValueError:
            flash('Introduce valores numéricos válidos.', 'error')
            return redirect(url_for('ingredients_manager'))
        
        exists = Ingredient.query.filter_by(name=name).first()
        if not exists:
            # Guardamos directamente price_kg
            new_ing = Ingredient(name=name, kcal_100g=kcal, price_kg=price_kg)
            db.session.add(new_ing)
            db.session.commit()
            flash('Ingrediente añadido.', 'success')
        else:
            flash('Ese ingrediente ya existe.', 'warning')
            
        return redirect(url_for('ingredients_manager'))
        
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()
    return render_template('ingredients.html', ingredients=all_ingredients)


@app.route('/create_recipe', methods=['GET', 'POST'])
@login_required
def create_recipe():
    """
    Crea una receta vinculando ingredientes existentes y sus cantidades.
    Recibe un JSON desde el frontend con la lista de ingredientes seleccionados.
    """
    # Cargamos ingredientes para el desplegable (select)
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        steps = request.form.get('steps')
        
        # 1. Crear la Receta Base
        new_recipe = Receta(
            title=title, 
            description=description, 
            steps=steps, 
            user_id=current_user.id
        )
        db.session.add(new_recipe)
        db.session.flush() # Importante: Genera el ID de la receta antes de seguir

        # 2. Procesar JSON de ingredientes (viene del JavaScript del Frontend)
        ing_data_json = request.form.get('ingredients_data')
        
        if ing_data_json:
            try:
                items = json.loads(ing_data_json)
                for item in items:
                    # Guardamos en la tabla intermedia (RecipeIngredient)
                    assoc = RecipeIngredient(
                        recipe_id=new_recipe.id,
                        ingredient_id=int(item['id']),
                        quantity_g=float(item['qty'])
                    )
                    db.session.add(assoc)
            except Exception as e:
                print(f"Error procesando ingredientes: {e}")
                flash('Hubo un error al guardar los ingredientes.', 'error')
        
        db.session.commit()
        flash(f'Receta "{title}" creada correctamente.', 'success')
        return redirect(url_for('create_recipe'))

    return render_template('create_recipe.html', ingredients=all_ingredients)



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

@app.route('/')
@login_required
def dashboard():
    # Importamos lo necesario para calcular fechas
    from datetime import date, timedelta
    
    # 1. Calcular el día de la semana y la fecha de inicio de ESTA semana
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    hoy = date.today()
    dia_actual_str = dias_semana[hoy.weekday()] # Ej: "Lunes"
    
    # Calculamos el lunes de esta semana exacta para filtrar en DB
    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())

    # 2. Buscar el menú filtrando por Usuario + Día + Semana Actual
    menu_hoy = MenuSemanal.query.filter_by(
        user_id=current_user.id, 
        dia=dia_actual_str,
        week_start=inicio_semana_actual # <--- ESTA ES LA CLAVE QUE FALTABA
    ).first()

    # Consultas auxiliares (se mantienen igual)
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

@app.route('/menu', methods=['GET', 'POST'])
@app.route('/menu/<week_str>', methods=['GET', 'POST'])
@login_required
def menu_semanal_page(week_str=None):
    # -----------------------------------------------------------
    # 1. Configuración de Fechas
    # -----------------------------------------------------------
    if week_str:
        try:
            current_week = datetime.strptime(week_str, '%Y-%m-%d').date()
        except ValueError:
            hoy = date.today()
            current_week = hoy - timedelta(days=hoy.weekday())
    else:
        hoy = date.today()
        current_week = hoy - timedelta(days=hoy.weekday())

    # Para el badge de "Semana Actual"
    hoy_real = date.today()
    real_current_week = hoy_real - timedelta(days=hoy_real.weekday())

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    tipos_comida = ['Desayuno', 'Comida', 'Merienda', 'Cena']

    # -----------------------------------------------------------
    # 2. Lógica de Guardado (POST)
    # -----------------------------------------------------------
    if request.method == 'POST':
        try:
            for dia in dias_semana:
                # A. Buscar o Crear el registro del Día (padre)
                menu_dia = MenuSemanal.query.filter_by(
                    user_id=current_user.id,
                    week_start=current_week,  # <--- CORREGIDO: Objeto date puro
                    dia=dia
                ).first()

                # 2. CREAR (Insert): Aquí es donde fallaba tu error INSERT
                if not menu_dia:
                    menu_dia = MenuSemanal(
                        user_id=current_user.id,
                        week_start=current_week, # <--- CORREGIDO: Objeto date puro
                        dia=dia
                    )
                    db.session.add(menu_dia)
                    db.session.commit()

                # B. Limpiar selecciones previas (CORREGIDO: usa menu_id)
                MenuSelection.query.filter_by(menu_id=menu_dia.id).delete()
                
                # C. Guardar las nuevas selecciones
                for tipo in tipos_comida:
                    # -- RECETAS --
                    recetas_ids = request.form.getlist(f"{dia}_{tipo}_receta")
                    for r_id in recetas_ids:
                        if r_id and r_id != "":
                            sel = MenuSelection(
                                menu_id=menu_dia.id,    # Corregido
                                tipo_comida=tipo,       # Corregido
                                receta_id=int(r_id)
                            )
                            db.session.add(sel)

                    # -- INGREDIENTES SUELTOS --
                    ing_ids = request.form.getlist(f"{dia}_{tipo}_ing_id")
                    ing_qtys = request.form.getlist(f"{dia}_{tipo}_ing_qty")
                    
                    for i_id, i_qty in zip(ing_ids, ing_qtys):
                        if i_id and i_id != "":
                            cantidad = float(i_qty) if i_qty else 0
                            sel = MenuSelection(
                                menu_id=menu_dia.id,    # Corregido
                                tipo_comida=tipo,       # Corregido
                                ingredient_id=int(i_id),
                                quantity=cantidad
                            )
                            db.session.add(sel)

            db.session.commit()
            flash('Menú guardado correctamente.', 'success')
            return redirect(url_for('menu_semanal_page', week_str=current_week))

        except Exception as e:
            db.session.rollback()
            print(f"Error guardando menú: {e}")
            flash(f'Error al guardar: {e}', 'error')

    # -----------------------------------------------------------
    # 3. Preparación de Datos (GET)
    # -----------------------------------------------------------
    menu = []
    
    # Usamos enumerate para calcular la fecha exacta de cada día
    for i, dia in enumerate(dias_semana):
        
        # 1. Obtener datos de la DB
        dia_db = MenuSemanal.query.filter_by(
            user_id=current_user.id, 
            week_start=current_week.strftime('%Y-%m-%d'),
            dia=dia
        ).first()

        # 2. Calcular la fecha visual (ej: 12/05)
        fecha_real = current_week + timedelta(days=i)
        fecha_formateada = fecha_real.strftime('%d/%m')

        if dia_db:
            dia_db.fecha_str = fecha_formateada # Inyectamos la fecha
            menu.append(dia_db)
        else:
            # Objeto dummy para días vacíos
            dummy = MenuSemanal(
                user_id=current_user.id,
                week_start=current_week.strftime('%Y-%m-%d'),
                dia=dia
            )
            dummy.fecha_str = fecha_formateada # Inyectamos la fecha
            menu.append(dummy)

    # Generar lista de compra y cargar catálogos
    lista_compra = generar_lista_compra_db(menu)
    recetas = Receta.query.filter_by(user_id=current_user.id).order_by(Receta.title).all()
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()

    # Navegación
    prev_week = (current_week - timedelta(weeks=1)).strftime('%Y-%m-%d')
    next_week = (current_week + timedelta(weeks=1)).strftime('%Y-%m-%d')

    return render_template('menu.html',
                           current_week=current_week,
                           real_current_week=real_current_week,
                           prev_week=prev_week,
                           next_week=next_week,
                           menu=menu,
                           recetas=recetas,
                           all_ingredients=all_ingredients,
                           lista_compra=lista_compra
                           )


def generar_lista_compra_db(menu_items):
    compra = {}
    tipos = ['Desayuno', 'Comida', 'Merienda', 'Cena']

    for item in menu_items:
        for tipo in tipos:
            # Usamos el nuevo método get_selections que devuelve todo
            selecciones = item.get_selections(tipo)
            
            for sel in selecciones:
                # CASO A: Es Receta
                if sel.receta:
                    for assoc in sel.receta.ingredients_assoc:
                        key = (assoc.ingredient.name, "g")
                        compra[key] = compra.get(key, 0) + assoc.quantity_g
                
                # CASO B: Es Ingrediente Suelto
                elif sel.ingredient:
                    key = (sel.ingredient.name, "g")
                    compra[key] = compra.get(key, 0) + sel.quantity

    resultado = []
    for (nombre, unidad), cantidad in sorted(compra.items()):
        resultado.append({'nombre': nombre, 'unidad': unidad, 'cantidad': round(cantidad, 1)})
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


@app.route('/ingredients/edit/<int:id>', methods=['POST'])
@login_required
def edit_ingredient(id):
    ing = Ingredient.query.get_or_404(id)
    
    try:
        ing.name = request.form.get('name')
        ing.kcal_100g = float(request.form.get('kcal'))
        ing.price_kg = float(request.form.get('price_kg'))
        
        db.session.commit()
        flash('Ingrediente actualizado correctamente.', 'success')
    except ValueError:
        flash('Error en los datos numéricos.', 'error')
    except Exception as e:
        flash(f'Error al actualizar: {e}', 'error')

    return redirect(url_for('ingredients_manager'))

@app.route('/ingredients/delete/<int:id>')
@login_required
def delete_ingredient(id):
    ing = Ingredient.query.get_or_404(id)
    
    # Verificamos si se usa en recetas para advertir (opcional, por ahora borramos)
    # Gracias al cascade de SQLAlchemy en models.py, se borrará de las recetas automáticamente
    try:
        db.session.delete(ing)
        db.session.commit()
        flash('Ingrediente eliminado del inventario.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {e}', 'error')
        
    return redirect(url_for('ingredients_manager'))

@app.route('/delete_recipe/<int:id>')
@login_required
def delete_recipe(id):
    receta = Receta.query.get_or_404(id)
    if receta.user_id != current_user.id:
        flash('No tienes permiso para borrar esto.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(receta)
        db.session.commit()
        flash('Receta eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {e}', 'error')
        
    return redirect(url_for('recetas_page')) # Asegúrate que la función de la lista se llama recetas_page o index


@app.route('/edit_recipe/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(id):
    receta = Receta.query.get_or_404(id)
    if receta.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('dashboard'))
    
    # Cargamos ingredientes para el desplegable
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()

    if request.method == 'POST':
        # 1. Actualizar datos básicos
        receta.title = request.form.get('title')
        receta.description = request.form.get('description')
        receta.steps = request.form.get('steps')

        # 2. Actualizar Ingredientes
        # Primero borramos los antiguos (es más fácil que comparar uno a uno)
        # Nota: Al borrar la relación, NO borramos el ingrediente del inventario, solo el vínculo
        for assoc in receta.ingredients_assoc:
            db.session.delete(assoc)
        
        # Ahora creamos los nuevos vínculos desde el JSON
        ing_data_json = request.form.get('ingredients_data')
        if ing_data_json:
            try:
                items = json.loads(ing_data_json)
                for item in items:
                    assoc = RecipeIngredient(
                        recipe_id=receta.id,
                        ingredient_id=int(item['id']),
                        quantity_g=float(item['qty'])
                    )
                    db.session.add(assoc)
            except Exception as e:
                print(f"Error: {e}")

        db.session.commit()
        flash('Receta actualizada.', 'success')
        return redirect(url_for('recetas_page')) # O index/dashboard

    # --- MODO GET: PREPARAR DATOS PARA EL FRONTEND ---
    # Convertimos los ingredientes actuales a un formato que el JavaScript entienda
    preloaded_ingredients = []
    for assoc in receta.ingredients_assoc:
        # Replicamos el cálculo para que el JS no se vuelva loco
        real_kcal = (assoc.quantity_g / 100) * assoc.ingredient.kcal_100g
        real_price = (assoc.quantity_g / 1000) * assoc.ingredient.price_kg
        
        preloaded_ingredients.append({
            'id': str(assoc.ingredient_id), # ID como string para que coincida con el value del select
            'name': assoc.ingredient.name,
            'qty': assoc.quantity_g,
            'realKcal': real_kcal,
            'realPrice': real_price
        })

    # Convertimos a JSON string para inyectarlo en el HTML
    preloaded_json = json.dumps(preloaded_ingredients)

    # Reutilizamos la plantilla create_recipe.html pero pasándole datos extra
    return render_template('create_recipe.html', 
                           ingredients=all_ingredients, 
                           receta_editar=receta, # Objeto receta
                           preloaded_json=preloaded_json) # JSON para JS

@app.route('/gym')
@login_required
def gym_dashboard():
    # 1. Sesiones recientes
    recent_sessions = WorkoutSession.query.filter_by(user_id=current_user.id).order_by(WorkoutSession.date.desc()).limit(5).all()
    
    # 2. Ejercicios (para el contador del catálogo)
    exercises = Exercise.query.filter_by(user_id=current_user.id).all()

    # 3. RUTINAS (¡NUEVO! Añadimos esto)
    routines = Routine.query.filter_by(user_id=current_user.id).all()
    
    # Pasamos 'routines' a la plantilla
    return render_template('gym/dashboard.html', sessions=recent_sessions, exercises=exercises, routines=routines)
@app.route('/gym/exercises', methods=['GET', 'POST'])
@login_required
def gym_exercises():
    form = ExerciseForm()
    if form.validate_on_submit():
        new_ex = Exercise(
            name=form.name.data,
            muscle_group=form.muscle_group.data,
            user_id=current_user.id
        )
        db.session.add(new_ex)
        db.session.commit()
        flash('Ejercicio añadido al catálogo.', 'success')
        return redirect(url_for('gym_exercises'))
    
    exercises = Exercise.query.filter_by(user_id=current_user.id).order_by(Exercise.muscle_group, Exercise.name).all()
    return render_template('gym/exercises.html', form=form, exercises=exercises)
@app.route('/gym/log', methods=['GET', 'POST'])
@login_required
def gym_log():
    # 1. Obtener datos para los selectores (Ejercicios y Rutinas disponibles)
    exercises = Exercise.query.filter_by(user_id=current_user.id).order_by(Exercise.name).all()
    routines = Routine.query.filter_by(user_id=current_user.id).all()
    
    # 2. Lógica de PRECARGA (Si la URL trae ?routine_id=X)
    preloaded_sets = []
    routine_id = request.args.get('routine_id')
    
    if routine_id:
        routine = Routine.query.get(routine_id)
        # Seguridad: verificar que la rutina pertenece al usuario actual
        if routine and routine.user_id == current_user.id:
            for ex_assoc in routine.exercises:
                # Añadimos un "esqueleto" de serie para que el JS lo pinte
                preloaded_sets.append({
                    'id': str(ex_assoc.exercise_id),
                    'name': ex_assoc.exercise.name,
                    'weight': '', # Dejamos vacío para rellenar en el gym
                    'reps': ''
                })

    # 3. Lógica de GUARDADO (Cuando se envía el formulario POST)
    if request.method == 'POST':
        data_json = request.form.get('workout_data')
        note = request.form.get('note')
        
        if data_json:
            try:
                # A. Crear la Sesión (Cabecera)
                new_session = WorkoutSession(
                    user_id=current_user.id, 
                    note=note, 
                    date=datetime.now() # Usa la hora actual
                )
                db.session.add(new_session)
                db.session.flush() # Necesario para obtener el ID de la sesión antes de seguir
                
                # B. Procesar el JSON y guardar las Series (Detalle)
                sets_data = json.loads(data_json)
                
                for index, s in enumerate(sets_data):
                    # Solo guardamos si el usuario rellenó peso y reps
                    # (Esto filtra los ejercicios de la rutina que se hayan dejado en blanco)
                    if s.get('weight') and s.get('reps'):
                        new_set = WorkoutSet(
                            session_id=new_session.id,
                            exercise_id=int(s['id']),
                            weight=float(s['weight']),
                            reps=int(s['reps']),
                            order=index
                        )
                        db.session.add(new_set)
                
                db.session.commit()
                flash('Entrenamiento registrado. ¡Buen trabajo!', 'success')
                return redirect(url_for('gym_dashboard'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Error al guardar entreno: {e}")
                flash('Hubo un error al guardar el entrenamiento.', 'danger')
                
    # 4. Renderizar la plantilla (pasando el JSON precargado si existe)
    return render_template('gym/log_workout.html', 
                           exercises=exercises, 
                           routines=routines, 
                           preloaded_json=json.dumps(preloaded_sets))

# Asegúrate de importar esto arriba del todo en app.py, o ponlo dentro de la función así:
from itertools import groupby 

@app.route('/gym/progress/<int:exercise_id>')
@login_required
def gym_progress(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    
    # Seguridad: comprobar que el ejercicio es tuyo
    if exercise.user_id != current_user.id:
        flash('No tienes permiso para ver esto.', 'error')
        return redirect(url_for('gym_dashboard'))
    
    # 1. Obtener historial ordenado por fecha (ASCENDENTE para la gráfica)
    history = db.session.query(WorkoutSet, WorkoutSession.date)\
        .join(WorkoutSession)\
        .filter(WorkoutSet.exercise_id == exercise_id)\
        .order_by(WorkoutSession.date.asc())\
        .all()
    
    # 2. Preparar datos para Chart.js
    chart_labels = [] # Eje X: Fechas
    chart_data = []   # Eje Y: Pesos Máximos
    
    # Agrupamos por fecha para sacar el "mejor levantamiento" de cada día
    # (Nota: groupby requiere que los datos ya vengan ordenados, por eso el .order_by de arriba)
    for date_obj, group in groupby(history, key=lambda x: x[1].strftime('%Y-%m-%d')):
        sets_that_day = list(group)
        # Buscamos el peso máximo levantado ese día
        max_weight = max([s[0].weight for s in sets_that_day])
        
        # Formateamos la fecha para que quede bonita en la gráfica (ej: 25 May)
        date_label = datetime.strptime(date_obj, '%Y-%m-%d').strftime('%d %b')
        
        chart_labels.append(date_label)
        chart_data.append(max_weight)
        
    # 3. Renderizar
    # Pasamos 'labels' y 'data' que es lo que pide tu HTML y causaba el error
    return render_template('gym/progress.html', 
                           exercise=exercise, 
                           history=reversed(history), # Invertimos para la tabla (lo más nuevo arriba)
                           labels=chart_labels, 
                           data=chart_data)
    
@app.route('/gym/routines')
@login_required
def gym_routines():
    routines = Routine.query.filter_by(user_id=current_user.id).all()
    return render_template('gym/routines_list.html', routines=routines)

@app.route('/gym/routines/new', methods=['GET', 'POST'])
@login_required
def create_routine():
    form = RoutineForm()
    all_exercises = Exercise.query.filter_by(user_id=current_user.id).order_by(Exercise.name).all()
    
    if request.method == 'POST':
        # 1. Crear la Rutina
        new_routine = Routine(
            name=request.form.get('name'),
            description=request.form.get('description'),
            user_id=current_user.id
        )
        db.session.add(new_routine)
        db.session.flush() # Para tener ID
        
        # 2. Añadir Ejercicios desde JSON
        exercises_json = request.form.get('exercises_data')
        if exercises_json:
            try:
                items = json.loads(exercises_json)
                for i, item in enumerate(items):
                    assoc = RoutineExercise(
                        routine_id=new_routine.id,
                        exercise_id=int(item['id']),
                        order=i
                    )
                    db.session.add(assoc)
            except Exception as e:
                print(e)
        
        db.session.commit()
        flash('Rutina creada correctamente.', 'success')
        return redirect(url_for('gym_routines'))

    return render_template('gym/create_routine.html', form=form, exercises=all_exercises)

@app.route('/gym/measurements', methods=['GET', 'POST'])
@login_required
def gym_measurements():
    form = BodyMeasurementForm()
    
    # --- GUARDAR DATOS (POST) ---
    if form.validate_on_submit():
        # Verificamos que al menos haya un dato
        if any([form.weight.data, form.biceps.data, form.chest.data, 
                form.hips.data, form.thigh.data, form.calf.data]):
            
            new_entry = BodyMeasurement(
                user_id=current_user.id,
                date=datetime.now(),
                weight=form.weight.data,
                biceps=form.biceps.data,
                chest=form.chest.data,
                hips=form.hips.data,
                thigh=form.thigh.data,
                calf=form.calf.data
            )
            db.session.add(new_entry)
            db.session.commit()
            flash('Medidas registradas correctamente.', 'success')
            return redirect(url_for('gym_measurements'))
        else:
            flash('Introduce al menos un valor.', 'warning')

    # --- PREPARAR DATOS PARA LA GRÁFICA (GET) ---
    # Obtenemos historial ordenado por fecha
    history = BodyMeasurement.query.filter_by(user_id=current_user.id).order_by(BodyMeasurement.date.asc()).all()
    
    # Creamos un diccionario con listas para Chart.js
    # Chart.js ignora los 'null', así que si un día no te mediste algo, el gráfico saltará ese punto
    chart_data = {
        'labels': [m.date.strftime('%d/%m/%Y') for m in history],
        'weight': [m.weight for m in history],
        'biceps': [m.biceps for m in history],
        'chest':  [m.chest for m in history],
        'hips':   [m.hips for m in history],
        'thigh':  [m.thigh for m in history],
        'calf':   [m.calf for m in history]
    }

    # Invertimos historial para la tabla (lo más nuevo primero)
    return render_template('gym/measurements.html', 
                           form=form, 
                           history=reversed(history),
                           chart_data=json.dumps(chart_data)) # Pasamos JSON al template

# --- EJECUCIÓN ---
if __name__ == '__main__':
    # Puerto 5003 como en tu configuración original
    print("Iniciando Home OS Multi-User en puerto 5003...")
    app.run(debug=True, port=5003)