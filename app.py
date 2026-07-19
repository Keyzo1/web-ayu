import re
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'SUPER_SECRET_KEY'

login_manager = LoginManager()
login_manager.init_app(app)

orders = [
    {'id': 1, 'name': 'Иван Иванов', 'phone': '79991112233', 'details': 'Генеральная (2 комн.)', 'price': '6 900 ₽'}
]
reviews_list = []

class User(UserMixin):
    def __init__(self, id, phone, name, password, role='user'):
        self.id = id
        self.phone = phone
        self.name = name
        self.password = password
        self.role = role

users = {
    '1': User('1', 'эркен', 'Эркен Хулхачиев', 'erkenhulha2008', 'admin'),
    '2': User('2', '79991112233', 'Мария Колесникова', '1234567d', 'user')
}

def clean_phone(phone_string):
    if not phone_string:
        return ""
    s = phone_string.strip().lower()
    digits = re.sub(r'\D', '', s)
    if len(digits) == 11 and (digits.startswith('7') or digits.startswith('8')):
        return '7' + digits[1:]
    elif len(digits) == 10:
        return '7' + digits
    return s

def format_review_name(full_name):
    parts = full_name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0].capitalize()
        last_initial = parts[1][0].upper()
        return f"{first_name} {last_initial}."
    return full_name.capitalize()

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/reviews')
def reviews():
    return render_template('reviews.html', reviews=reviews_list)

@app.route('/add_review', methods=['POST'])
def add_review():
    if not current_user.is_authenticated:
        return redirect(url_for('reviews'))
    display_name = format_review_name(current_user.name)
    text = request.form.get('text', '').strip()
    rating = int(request.form.get('rating', 5))
    if text:
        reviews_list.append({'name': display_name, 'text': text, 'rating': rating})
    return redirect(url_for('reviews'))

@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('book'))

        name = current_user.name
        phone = current_user.phone
        service_type = request.form.get('service_type', 'Не указано')
        rooms = request.form.get('rooms', '1')
        price = request.form.get('price', '0 ₽')

        orders.append({
            'id': len(orders) + 1,
            'name': name,
            'phone': phone,
            'details': f"{service_type} ({rooms} комн.)",
            'price': price
        })
        return render_template('book.html', success_booking=True)

    return render_template('book.html')

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    global orders
    order_to_delete = next((o for o in orders if o['id'] == order_id), None)
    if order_to_delete and current_user.is_authenticated:
        user_phone_cleaned = clean_phone(current_user.phone)
        order_phone_cleaned = clean_phone(order_to_delete['phone'])
        if current_user.role == 'admin' or user_phone_cleaned == order_phone_cleaned:
            orders = [o for o in orders if o['id'] != order_id]
    return redirect(url_for('services'))

@app.route('/services')
def services():
    return render_template('services.html', orders=orders)

@app.route('/login', methods=['POST'])
def login():
    phone_input = request.form.get('phone', '').strip()
    password = request.form.get('password', '').strip()
    referrer = request.referrer
    template_to_render = 'index.html'
    if referrer:
        if '/book' in referrer: template_to_render = 'book.html'
        elif '/services' in referrer: template_to_render = 'services.html'
        elif '/reviews' in referrer: template_to_render = 'reviews.html'

    target_login = clean_phone(phone_input)
    user_found = False
    for user in users.values():
        if clean_phone(user.phone) == target_login:
            user_found = True
            if user.password == password:
                login_user(user)
                return redirect(referrer if referrer else url_for('services'))
            else:
                return render_template(template_to_render, orders=orders, reviews=reviews_list, login_error="Неверный пароль", open_modal="login")
    if not user_found:
        return render_template(template_to_render, orders=orders, reviews=reviews_list, login_error="Пользователь не найден", open_modal="login")

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '').strip()
    referrer = request.referrer
    template_to_render = 'index.html'
    if referrer:
        if '/book' in referrer: template_to_render = 'book.html'
        elif '/services' in referrer: template_to_render = 'services.html'
        elif '/reviews' in referrer: template_to_render = 'reviews.html'

    registered_phone = clean_phone(phone)
    if not name or not registered_phone or not password:
        return render_template(template_to_render, orders=orders, reviews=reviews_list, register_error="Заполните все поля", open_modal="register")
    for user in users.values():
        if clean_phone(user.phone) == registered_phone:
            return render_template(template_to_render, orders=orders, reviews=reviews_list, register_error="Пользователь уже зарегистрирован", open_modal="register")
    if len(password) < 8:
        return render_template(template_to_render, orders=orders, reviews=reviews_list, register_error="Пароль слишком короткий", open_modal="register")

    new_id = str(len(users) + 1)
    new_user = User(id=new_id, phone=registered_phone, name=name, password=password, role='user')
    users[new_id] = new_user
    login_user(new_user)
    return redirect(referrer if referrer else url_for('services'))

@app.route('/logout')
def logout():
    referrer = request.referrer
    logout_user()
    return redirect(referrer if referrer else url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)